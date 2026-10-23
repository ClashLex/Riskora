"""Point-in-time feature building, labels, baselines and chronological evaluation."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime

import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .db import connect, db_path, rows

FEATURE_VERSION = "1"
MODEL_VERSION = "logistic-v2"
BASE_FEATURES = [
    "fund_sector_share",
    "fund_industry_share",
    "fund_concentration",
    "past_fund_additions",
    "past_stock_additions",
    "return_5",
    "return_20",
    "volatility_20",
    "volume_ratio_5_20",
    "market_available",
]
FULL_FEATURES = BASE_FEATURES + ["event_direction", "event_available"]


def snapshots(db, scheme_id=None):
    sql = "SELECT * FROM snapshots"
    args = ()
    if scheme_id:
        sql += " WHERE scheme_id=?"
        args = (scheme_id,)
    return rows(db, sql + " ORDER BY scheme_id,report_date", args)


def horizon_snapshots(items, horizon):
    if horizon == "month":
        return items
    quarters = {}
    for item in items:
        d = date.fromisoformat(item["report_date"])
        quarters[(d.year, (d.month - 1) // 3)] = item
    return [quarters[key] for key in sorted(quarters)]


def holdings(db, snapshot_id):
    return {
        row["isin"]: row
        for row in rows(db, "SELECT * FROM holdings WHERE snapshot_id=?", (snapshot_id,))
    }


def known_universe(db, cutoff, source_kind):
    # A candidate must already have appeared in a published snapshot or in market data.
    return {
        row["isin"]
        for row in rows(
            db,
            """SELECT DISTINCT h.isin FROM holdings h
        JOIN snapshots s ON s.id=h.snapshot_id WHERE s.published_at<=? AND s.source_kind=?
        UNION SELECT DISTINCT isin FROM market_observations WHERE date<=? AND source_kind=?""",
            (cutoff, source_kind, cutoff, source_kind),
        )
    }


def label_change(previous, future, materiality):
    if previous and not future:
        return "exit"
    if previous and future:
        old_units, new_units = previous["units"], future["units"]
        if old_units is not None and new_units is not None and new_units > old_units * 1.01:
            return "accumulation"
        return "existing"
    if future and future["weight"] >= materiality:
        return "addition"
    return "negative"


def build_labels(db, horizon="month", materiality=0.1, persist=False):
    schemes = rows(db, "SELECT id,source_kind FROM schemes")
    cases = []
    for scheme in schemes:
        sequence = horizon_snapshots(snapshots(db, scheme["id"]), horizon)
        for previous, future in zip(sequence, sequence[1:], strict=False):
            gap = (
                date.fromisoformat(future["report_date"])
                - date.fromisoformat(previous["report_date"])
            ).days
            valid_gap = 20 <= gap <= 45 if horizon == "month" else 70 <= gap <= 105
            cutoff = previous["published_at"]
            if cutoff >= future["report_date"]:
                valid_gap = False
            prior = holdings(db, previous["id"])
            later = holdings(db, future["id"])
            known_securities = known_universe(db, cutoff, scheme["source_kind"])
            universe = known_securities | set(prior) | set(later)
            comparable = bool(previous["complete"] and future["complete"] and valid_gap)
            for isin in universe:
                # A security first observed only in the future cannot be a historical candidate.
                known = isin in known_securities
                label = (
                    label_change(prior.get(isin), later.get(isin), materiality)
                    if comparable and known
                    else "unknown"
                )
                case = {
                    "scheme_id": scheme["id"],
                    "isin": isin,
                    "cutoff": cutoff,
                    "target_report_date": future["report_date"],
                    "target_published_at": future["published_at"],
                    "horizon": horizon,
                    "label": label,
                    "previous_snapshot_id": previous["id"],
                    "next_snapshot_id": future["id"],
                    "materiality": materiality,
                    "source_kind": scheme["source_kind"],
                }
                cases.append(case)
                if persist:
                    db.execute(
                        """INSERT OR REPLACE INTO labels
                        (scheme_id,isin,cutoff,target_report_date,horizon,label,
                         previous_snapshot_id,next_snapshot_id,materiality)
                        VALUES(?,?,?,?,?,?,?,?,?)""",
                        tuple(
                            case[key]
                            for key in (
                                "scheme_id",
                                "isin",
                                "cutoff",
                                "target_report_date",
                                "horizon",
                                "label",
                                "previous_snapshot_id",
                                "next_snapshot_id",
                                "materiality",
                            )
                        ),
                    )
    return cases


def market_features(db, isin, cutoff, source_kind):
    history = rows(
        db,
        """SELECT date,close,adjusted_close,volume,source_url FROM market_observations
        WHERE isin=? AND date<=? AND source_kind=? ORDER BY date DESC LIMIT 21""",
        (isin, cutoff, source_kind),
    )
    if len(history) < 2:
        return {
            "return_5": None,
            "return_20": None,
            "volatility_20": None,
            "volume_ratio_5_20": None,
            "market_available": 0,
        }, []
    use_adjusted = all(item["adjusted_close"] is not None for item in history)
    prices = [
        item["adjusted_close"] if use_adjusted else item["close"] for item in reversed(history)
    ]
    volumes = [item["volume"] for item in reversed(history)]
    changes = np.diff(np.log(prices))
    values = {
        "return_5": prices[-1] / prices[-6] - 1 if len(prices) >= 6 else None,
        "return_20": prices[-1] / prices[-21] - 1 if len(prices) >= 21 else None,
        "volatility_20": float(np.std(changes[-20:])) if len(changes) >= 5 else None,
        "volume_ratio_5_20": (
            float(np.mean(volumes[-5:]) / np.mean(volumes[-20:]))
            if len(volumes) >= 20 and np.mean(volumes[-20:]) > 0
            else None
        ),
        "market_available": 1,
    }
    return values, [
        {
            "type": "market",
            "date": history[0]["date"],
            "source_url": history[0]["source_url"],
            "note": "Adjusted close used for the full window."
            if use_adjusted
            else "Unadjusted close used; corporate actions may distort returns.",
        }
    ]


def features(db, scheme_id, isin, cutoff, horizon="month"):
    scheme = db.execute("SELECT source_kind FROM schemes WHERE id=?", (scheme_id,)).fetchone()
    security = db.execute("SELECT * FROM securities WHERE isin=?", (isin,)).fetchone()
    previous = db.execute(
        """SELECT * FROM snapshots WHERE scheme_id=? AND published_at<=?
        ORDER BY report_date DESC LIMIT 1""",
        (scheme_id, cutoff),
    ).fetchone()
    if not security or not previous:
        raise ValueError("Security or disclosed fund snapshot unavailable at cutoff.")
    past = rows(
        db,
        """SELECT l.*,s.published_at FROM labels l JOIN snapshots s ON s.id=l.next_snapshot_id
        WHERE l.scheme_id=? AND l.horizon=? AND s.published_at<=?""",
        (scheme_id, horizon, cutoff),
    )
    prior = holdings(db, previous["id"])
    in_sector = [
        h["weight"]
        for key, h in prior.items()
        if security["sector"] is not None
        and db.execute("SELECT sector FROM securities WHERE isin=?", (key,)).fetchone()[0]
        == security["sector"]
    ]
    in_industry = [
        h["weight"]
        for key, h in prior.items()
        if security["industry"] is not None
        and db.execute("SELECT industry FROM securities WHERE isin=?", (key,)).fetchone()[0]
        == security["industry"]
    ]
    values = {
        "fund_sector_share": sum(in_sector) / 100,
        "fund_industry_share": sum(in_industry) / 100,
        "fund_concentration": sum((h["weight"] / 100) ** 2 for h in prior.values()),
        "past_fund_additions": sum(item["label"] == "addition" for item in past),
        "past_stock_additions": sum(
            item["label"] == "addition" and item["isin"] == isin for item in past
        ),
    }
    market, market_sources = market_features(db, isin, cutoff, scheme["source_kind"])
    values.update(market)
    events = rows(
        db,
        """SELECT e.*,x.extracted_json,x.processed_at FROM company_events e
        JOIN extracted_events x ON x.event_id=e.id WHERE e.isin=? AND e.source_kind=? AND e.published_at<=?
        AND x.status='ok' AND x.processed_at<=? ORDER BY e.published_at DESC LIMIT 5""",
        (isin, scheme["source_kind"], cutoff + "T23:59:59", cutoff + "T23:59:59"),
    )
    directions = []
    evidence = [
        {
            "type": "holdings",
            "date": previous["report_date"],
            "published_at": previous["published_at"],
            "source_url": previous["source_url"],
        }
    ] + market_sources
    for event in events:
        extracted = json.loads(event["extracted_json"])
        directions.append({"positive": 1, "neutral": 0, "negative": -1}[extracted["direction"]])
        evidence.append(
            {
                "type": "event",
                "date": event["published_at"],
                "source_url": event["source_url"],
                "excerpt": event["excerpt"][:300],
            }
        )
    values["event_direction"] = float(np.mean(directions)) if directions else None
    values["event_available"] = int(bool(directions))
    return values, evidence


def dataset(db, horizon="month", materiality=0.1, source_kind="user_import"):
    cases = build_labels(db, horizon, materiality, persist=True)
    output = []
    for case in cases:
        if case["source_kind"] != source_kind or case["label"] not in {"addition", "negative"}:
            continue
        values, evidence = features(db, case["scheme_id"], case["isin"], case["cutoff"], horizon)
        record = {
            **case,
            **values,
            "target": int(case["label"] == "addition"),
            "evidence": evidence,
        }
        output.append(record)
        db.execute(
            """INSERT OR REPLACE INTO feature_records VALUES(?,?,?,?,?,?)""",
            (
                case["scheme_id"],
                case["isin"],
                case["cutoff"],
                horizon,
                FEATURE_VERSION,
                json.dumps(values),
            ),
        )
    return pd.DataFrame(output)


def model_fit(frame, columns):
    if frame.empty or frame["target"].nunique() < 2:
        raise ValueError(
            "Training requires both additions and verified negatives in earlier periods."
        )
    model = make_pipeline(
        SimpleImputer(strategy="constant", fill_value=0),
        StandardScaler(),
        LogisticRegression(max_iter=1000, class_weight="balanced"),
    )
    model.fit(frame[columns], frame["target"])
    return model


def training_readiness(cases):
    """Use the same availability and class requirements as the final training split."""
    eligible = [case for case in cases if case["label"] in {"addition", "negative"}]
    dates = sorted({case["cutoff"] for case in eligible})
    known_labels = {
        case["label"]
        for case in eligible
        if dates and case["cutoff"] < dates[-1] and case["target_published_at"] <= dates[-1]
    }
    blockers = []
    if len(dates) < 4:
        blockers.append(
            "At least four distinct comparable cutoff periods are required for a holdout."
        )
    if known_labels != {"addition", "negative"}:
        blockers.append(
            "Earlier periods need both additions and verified negatives published by the holdout cutoff."
        )
    return {
        "usable_periods": len(dates),
        "ready": not blockers,
        "blockers": blockers,
        "requirements": "Four comparable cutoff periods, with both training labels known by the final holdout cutoff. Complete statements and a known candidate universe are required.",
    }


def available_training(frame, cutoff):
    return frame[(frame["cutoff"] < cutoff) & (frame["target_published_at"] <= cutoff)].copy()


def ranking_metrics(frame, scores, k=5):
    data = frame[["scheme_id", "cutoff", "target"]].copy()
    data["score"] = scores
    precision, recall = [], []
    for _, group in data.groupby(["scheme_id", "cutoff"]):
        ordered = group.sort_values("score", ascending=False).head(k)
        precision.append(float(ordered["target"].sum() / len(ordered)))
        positives = int(group["target"].sum())
        if positives:
            recall.append(float(ordered["target"].sum() / positives))
    result = {
        "cases": len(data),
        "positives": int(data["target"].sum()),
        "precision_at_5": float(np.mean(precision)),
        "recall_at_5": float(np.mean(recall)) if recall else None,
        "average_precision": float(average_precision_score(data["target"], scores))
        if data["target"].sum()
        else None,
    }
    return result


def evaluate_models(earlier, test):
    """Fit only on earlier cutoffs and evaluate a later single cutoff."""
    baseline_frequency = earlier.groupby("isin")["target"].mean().to_dict()
    fallback = float(earlier["target"].mean())
    results = {
        "addition_frequency": ranking_metrics(
            test, [baseline_frequency.get(v, fallback) for v in test["isin"]]
        ),
        "fund_preference": ranking_metrics(
            test, test["fund_sector_share"].to_numpy() + test["fund_industry_share"].to_numpy()
        ),
    }
    base_model = model_fit(earlier, BASE_FEATURES)
    results["holdings_market_model"] = ranking_metrics(
        test, base_model.predict_proba(test[BASE_FEATURES])[:, 1]
    )
    full_model = None
    if earlier["event_available"].sum() > 0 and test["event_available"].sum() > 0:
        full_model = model_fit(earlier, FULL_FEATURES)
        results["full_event_model"] = ranking_metrics(
            test, full_model.predict_proba(test[FULL_FEATURES])[:, 1]
        )
    else:
        results["full_event_model"] = {
            "status": "unavailable",
            "reason": "No point-in-time extracted event features in train and holdout periods.",
        }
    return results, base_model, full_model


def train(horizon="month", materiality=0.1, source_kind="user_import"):
    with connect() as db:
        frame = dataset(db, horizon, materiality, source_kind)
        readiness = training_readiness(frame.to_dict("records"))
        if not readiness["ready"]:
            raise ValueError(" ".join(readiness["blockers"]))
        dates = sorted(frame["cutoff"].unique()) if not frame.empty else []
        test_date = dates[-1]
        earlier = available_training(frame, test_date)
        test = frame[frame["cutoff"] == test_date].copy()
        if earlier["target"].nunique() < 2 or test.empty:
            raise ValueError(
                "Earlier periods need both labels and the holdout needs eligible cases."
            )
        # Earlier dates provide walk-forward validation; the final date stays untouched.
        validation = []
        for fold_date in dates[2:-1]:
            fold_train = available_training(frame, fold_date)
            fold_test = frame[frame["cutoff"] == fold_date]
            if fold_train["target"].nunique() < 2 or fold_test.empty:
                continue
            fold_metrics, _, _ = evaluate_models(fold_train, fold_test)
            validation.append((fold_date, fold_metrics))
        results, base_model, full_model = evaluate_models(earlier, test)
        finished = datetime.now(UTC).isoformat()
        cursor = db.execute(
            """INSERT INTO training_runs
            (started_at,finished_at,status,source_kind,horizon,model_version,feature_version,
             train_end,test_start,test_end,metrics_json) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (
                finished,
                finished,
                "complete",
                source_kind,
                horizon,
                MODEL_VERSION,
                FEATURE_VERSION,
                earlier["cutoff"].max(),
                test_date,
                test_date,
                json.dumps(results),
            ),
        )
        for phase, period, metrics in [
            ("validation", day, outcome) for day, outcome in validation
        ] + [("holdout", test_date, results)]:
            for name, values in metrics.items():
                db.execute(
                    "INSERT INTO evaluation_results VALUES(?,?,?,?,?)",
                    (cursor.lastrowid, phase, period, name, json.dumps(values)),
                )
        artifact = db_path().parent / "models" / f"run-{cursor.lastrowid}.joblib"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "base": base_model,
                "full": full_model,
                "horizon": horizon,
                "source_kind": source_kind,
                "materiality": materiality,
                "trained_through": earlier["cutoff"].max(),
                "labels_available_through": earlier["target_published_at"].max(),
                "feature_version": FEATURE_VERSION,
            },
            artifact,
        )
        db.execute(
            "UPDATE training_runs SET artifact_path=? WHERE id=?", (str(artifact), cursor.lastrowid)
        )
        return {
            "run_id": cursor.lastrowid,
            "train_end": earlier["cutoff"].max(),
            "test_period": test_date,
            "metrics": results,
            "walk_forward_periods": len(validation),
            "source_kind": source_kind,
            "horizon": horizon,
            "score_type": "uncalibrated ranking score",
        }


def predict(scheme_id, horizon="month", cutoff=None):
    with connect() as db:
        scheme = db.execute("SELECT * FROM schemes WHERE id=?", (scheme_id,)).fetchone()
        if not scheme:
            raise ValueError("Scheme not found.")
        query = "SELECT * FROM snapshots WHERE scheme_id=?"
        params = [scheme_id]
        if cutoff:
            query += " AND published_at<=?"
            params.append(cutoff)
        latest = db.execute(query + " ORDER BY report_date DESC LIMIT 1", params).fetchone()
        if not latest:
            raise ValueError("No complete disclosed snapshot is available at the selected cutoff.")
        if not latest["complete"]:
            raise ValueError(
                "The latest statement at this cutoff is incomplete. Import a complete statement before ranking."
            )
        cutoff = cutoff or latest["published_at"]
        run = db.execute(
            """SELECT * FROM training_runs WHERE status='complete' AND source_kind=? AND horizon=?
            AND model_version=? AND artifact_path IS NOT NULL ORDER BY id DESC LIMIT 1""",
            (scheme["source_kind"], horizon, MODEL_VERSION),
        ).fetchone()
        if not run:
            raise ValueError(
                "No current model is available for this dataset and period. Train or retrain using publication-aware evaluation."
            )
        artifact = joblib.load(run["artifact_path"])
        if artifact["horizon"] != horizon:
            raise ValueError("Train a model for the selected horizon first.")
        if cutoff <= artifact["trained_through"]:
            raise ValueError("Prediction cutoff must follow the model's training period.")
        if cutoff < artifact["labels_available_through"]:
            raise ValueError(
                "Prediction cutoff precedes the publication of labels used to train this model."
            )
        held = set(holdings(db, latest["id"]))
        candidates = sorted(known_universe(db, cutoff, scheme["source_kind"]) - held)
        if not candidates:
            raise ValueError("No known, currently absent securities are available to rank.")
        if len(candidates) > 5000:
            raise ValueError("Candidate universe exceeds the 5,000-security local limit.")
        records = []
        for isin in candidates:
            values, evidence = features(db, scheme_id, isin, cutoff, horizon)
            records.append((isin, values, evidence))
        model = artifact["full"] or artifact["base"]
        columns = FULL_FEATURES if artifact["full"] else BASE_FEATURES
        frame = pd.DataFrame([r[1] for r in records])
        scores = model.predict_proba(frame[columns])[:, 1]
        transformed = model["simpleimputer"].transform(frame[columns])
        transformed = model["standardscaler"].transform(transformed)
        contributions = transformed * model["logisticregression"].coef_[0]
        output = []
        generated_at = datetime.now(UTC).isoformat()
        for index, ((isin, values, evidence), score) in enumerate(
            zip(records, scores, strict=True)
        ):
            security = db.execute("SELECT * FROM securities WHERE isin=?", (isin,)).fetchone()
            item = {
                "isin": isin,
                "company": security["company"],
                "ticker": security["ticker"],
                "sector": security["sector"],
                "score": round(float(score), 6),
                "score_type": "uncalibrated ranking score",
                "features": values,
                "contributions": {
                    name: round(float(contributions[index, column]), 5)
                    for column, name in enumerate(columns)
                },
                "evidence": evidence,
            }
            output.append(item)
            db.execute(
                """INSERT OR REPLACE INTO predictions
                (run_id,scheme_id,isin,horizon,cutoff,score,created_at,features_json,evidence_json)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    run["id"],
                    scheme_id,
                    isin,
                    horizon,
                    cutoff,
                    float(score),
                    generated_at,
                    json.dumps(values),
                    json.dumps(evidence),
                ),
            )
        output.sort(key=lambda item: item["score"], reverse=True)
        return {
            "scheme_id": scheme_id,
            "horizon": horizon,
            "cutoff": cutoff,
            "observation_date": latest["report_date"],
            "published_at": latest["published_at"],
            "generated_at": generated_at,
            "run_id": run["id"],
            "model_version": run["model_version"],
            "feature_version": FEATURE_VERSION,
            "materiality": artifact["materiality"],
            "source_kind": scheme["source_kind"],
            "score_type": "uncalibrated ranking score",
            "warning": "Rankings concern newly observed holdings in a later disclosure, not orders or exact trade timing. Scores are not calibrated probabilities or investment advice.",
            "candidates": output,
        }
