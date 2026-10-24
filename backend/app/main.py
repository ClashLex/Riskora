"""Canonical FastAPI entrypoint for Riskora."""

from __future__ import annotations

import json
import logging
import os
import secrets
import sqlite3
from datetime import UTC, date, datetime
from typing import Literal

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, HttpUrl, field_validator

from .db import connect, init_db, rows
from .demo import load_synthetic_demo
from .ingestion import ImportProblem, import_holdings, import_market, utcnow
from .ml import MODEL_VERSION, build_labels, predict, train, training_readiness
from .signals import extract

logger = logging.getLogger(__name__)


def admin(x_admin_token: str | None = Header(default=None)):
    expected = os.getenv("RISKORA_ADMIN_TOKEN", "")
    if not expected:
        raise HTTPException(
            503, "Set RISKORA_ADMIN_TOKEN on the server to enable management actions."
        )
    if not x_admin_token or not secrets.compare_digest(expected, x_admin_token):
        raise HTTPException(401, "A valid X-Admin-Token is required.")


class EventInput(BaseModel):
    isin: str = Field(pattern=r"^IN[A-Z0-9]{10}$")
    title: str = Field(min_length=3, max_length=200)
    category: str = Field(min_length=2, max_length=80)
    published_at: datetime
    source_url: HttpUrl
    excerpt: str = Field(min_length=10, max_length=10000)

    @field_validator("published_at")
    @classmethod
    def check_published(cls, value):
        if not value.tzinfo or value > datetime.now(UTC):
            raise ValueError("published_at needs a timezone and cannot be in the future")
        return value.astimezone(UTC)


class TrainingInput(BaseModel):
    horizon: Literal["month", "quarter"] = "month"
    materiality: float = Field(default=0.1, ge=0.01, le=10)
    source_kind: Literal["user_import", "synthetic"] = "user_import"


class IdentifierReview(BaseModel):
    ticker: str = Field(pattern=r"^[A-Z0-9._-]{1,30}$")
    source_url: HttpUrl


def create_app():
    init_db()
    app = FastAPI(
        title="Riskora — Indian Mutual Fund Purchase Intelligence",
        version="0.2.0",
        description="Research on newly observed holdings in subsequent disclosed snapshots.",
    )
    origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Content-Type", "X-Admin-Token"],
    )

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "riskora", "database": "SQLite"}

    @app.get("/api/v1/overview")
    def overview():
        with connect() as db:
            values = db.execute("""SELECT (SELECT COUNT(*) FROM schemes) funds,
                (SELECT COUNT(*) FROM snapshots) observations,
                (SELECT COUNT(*) FROM securities) securities,
                (SELECT COUNT(DISTINCT scheme_id) FROM snapshots WHERE complete=1) eligible_funds,
                (SELECT COUNT(*) FROM snapshots WHERE source_kind='synthetic') synthetic_observations,
                (SELECT COUNT(*) FROM snapshots WHERE source_kind='user_import') imported_observations,
                (SELECT MAX(report_date) FROM snapshots WHERE source_kind='user_import') latest_real_report,
                (SELECT MAX(retrieved_at) FROM snapshots WHERE source_kind='user_import') latest_update""").fetchone()
            latest = db.execute(
                "SELECT * FROM training_runs WHERE status='complete' AND model_version=? ORDER BY id DESC LIMIT 1",
                (MODEL_VERSION,),
            ).fetchone()
            incomplete = db.execute("SELECT COUNT(*) FROM snapshots WHERE complete=0").fetchone()[0]
            warnings = []
            if not values["observations"]:
                warnings.append("No historical holdings imported. Predictions are unavailable.")
            if incomplete:
                warnings.append(
                    f"{incomplete} snapshot(s) are incomplete and cannot verify negative labels."
                )
            if values["synthetic_observations"]:
                warnings.append(
                    f"{values['synthetic_observations']} synthetic snapshot(s) are included in overview totals; they are not real disclosures."
                )
            if (
                values["latest_real_report"]
                and (
                    datetime.now(UTC).date() - date.fromisoformat(values["latest_real_report"])
                ).days
                > 90
            ):
                warnings.append("The latest imported real portfolio report is over 90 days old.")
            if not latest:
                warnings.append("No trained model or out-of-sample evaluation is available.")
            return {
                **dict(values),
                "training_status": "trained" if latest else "not_trained",
                "latest_evaluation": json.loads(latest["metrics_json"]) if latest else None,
                "latest_run_id": latest["id"] if latest else None,
                "latest_run_source_kind": latest["source_kind"] if latest else None,
                "warnings": warnings,
            }

    @app.get("/api/v1/funds")
    def funds():
        with connect() as db:
            return rows(
                db,
                """SELECT s.*,COUNT(p.id) observations,MAX(p.report_date) latest_report_date,
                MAX(p.published_at) latest_published_at FROM schemes s LEFT JOIN snapshots p ON p.scheme_id=s.id
                GROUP BY s.id ORDER BY s.name""",
            )

    @app.get("/api/v1/identifiers")
    def identifiers():
        with connect() as db:
            return rows(
                db,
                """SELECT s.isin,s.company,s.ticker,s.sector,
                (SELECT MAX(reviewed_at) FROM identifier_mappings m WHERE m.isin=s.isin) reviewed_at
                FROM securities s ORDER BY s.company LIMIT 5000""",
            )

    @app.put("/api/v1/identifiers/{isin}", dependencies=[Depends(admin)])
    def review_identifier(isin: str, body: IdentifierReview):
        with connect() as db:
            if not db.execute("SELECT 1 FROM securities WHERE isin=?", (isin,)).fetchone():
                raise HTTPException(404, "Security not found.")
            collision = db.execute(
                "SELECT isin FROM securities WHERE ticker=? AND isin<>?", (body.ticker, isin)
            ).fetchone()
            if collision:
                raise HTTPException(409, "Ticker already maps to another ISIN.")
            db.execute("UPDATE securities SET ticker=? WHERE isin=?", (body.ticker, isin))
            db.execute(
                """INSERT OR REPLACE INTO identifier_mappings(isin,ticker,source_url,reviewed_at)
                VALUES(?,?,?,?)""",
                (isin, body.ticker, str(body.source_url), utcnow()),
            )
            return {"isin": isin, "ticker": body.ticker, "reviewed_at": utcnow()}

    @app.get("/api/v1/funds/{scheme_id}")
    def fund(scheme_id: str):
        with connect() as db:
            scheme = db.execute("SELECT * FROM schemes WHERE id=?", (scheme_id,)).fetchone()
            if not scheme:
                raise HTTPException(404, "Fund not found.")
            snapshots = rows(
                db,
                "SELECT * FROM snapshots WHERE scheme_id=? ORDER BY report_date DESC",
                (scheme_id,),
            )
            for item in snapshots:
                item["warnings"] = json.loads(item["warnings"])
                item["holdings"] = rows(
                    db,
                    """SELECT h.*,s.company,s.ticker,s.sector,s.industry FROM holdings h
                    JOIN securities s ON s.isin=h.isin WHERE snapshot_id=? ORDER BY weight DESC""",
                    (item["id"],),
                )
            labels = [
                case
                for horizon in ("month", "quarter")
                for case in build_labels(db, horizon)
                if case["scheme_id"] == scheme_id and case["label"] not in {"negative", "existing"}
            ]
            labels.sort(key=lambda case: (case["cutoff"], case["target_report_date"]), reverse=True)
            return {
                "scheme": dict(scheme),
                "snapshots": snapshots,
                "changes": labels[:200],
                "changes_total": len(labels),
            }

    @app.post("/api/v1/imports/holdings", dependencies=[Depends(admin)])
    async def holdings_import(
        file: UploadFile = File(...),
        scheme_id: str = Form(...),
        scheme_name: str = Form(...),
        amc: str = Form(...),
        report_date: str = Form(...),
        published_at: str = Form(...),
        source_url: str = Form(...),
        complete: bool = Form(...),
        category: str = Form(""),
    ):
        if not file.filename or not file.filename.lower().endswith(".csv"):
            raise HTTPException(422, "Upload a UTF-8 CSV file.")
        data = await file.read(5 * 1024 * 1024 + 1)
        try:
            return import_holdings(
                data,
                scheme_id=scheme_id,
                scheme_name=scheme_name,
                amc=amc,
                report_date=report_date,
                published_at=published_at,
                source_url=source_url,
                complete=complete,
                category=category,
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(
                422,
                "A statement for this fund and report date already exists. Review the existing disclosure or choose a different report date.",
            ) from exc
        except ImportProblem as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/v1/imports/market", dependencies=[Depends(admin)])
    async def market_import(file: UploadFile = File(...), source_url: str = Form(...)):
        if not file.filename or not file.filename.lower().endswith(".csv"):
            raise HTTPException(422, "Upload a UTF-8 CSV file.")
        try:
            return import_market(await file.read(5 * 1024 * 1024 + 1), source_url=source_url)
        except sqlite3.IntegrityError as exc:
            raise HTTPException(
                422,
                "Some market observations already exist for this security and date. Remove duplicates from the CSV and retry.",
            ) from exc
        except ImportProblem as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/v1/demo/load", dependencies=[Depends(admin)])
    def demo_load():
        return load_synthetic_demo()

    @app.get("/api/v1/market")
    def market(
        isin: str = Query(pattern=r"^IN[A-Z0-9]{10}$"),
        cutoff: date | None = None,
        source_kind: Literal["user_import", "synthetic"] = "user_import",
    ):
        with connect() as db:
            return rows(
                db,
                """SELECT * FROM market_observations WHERE isin=? AND date<=? AND source_kind=?
                ORDER BY date DESC LIMIT 100""",
                (isin, (cutoff or date.today()).isoformat(), source_kind),
            )

    @app.post("/api/v1/events", dependencies=[Depends(admin)])
    def event_import(body: EventInput):
        with connect() as db:
            if not db.execute("SELECT 1 FROM securities WHERE isin=?", (body.isin,)).fetchone():
                raise HTTPException(422, "Import a security through holdings or market CSV first.")
            try:
                cursor = db.execute(
                    """INSERT INTO company_events
                    (isin,title,category,published_at,source_url,excerpt,imported_at,source_kind)
                    VALUES(?,?,?,?,?,?,?,?)""",
                    (
                        body.isin,
                        body.title,
                        body.category,
                        body.published_at.isoformat(),
                        str(body.source_url),
                        body.excerpt,
                        utcnow(),
                        "user_import",
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise HTTPException(409, "Duplicate event.") from exc
            return {"event_id": cursor.lastrowid, "extraction_status": "not_requested"}

    @app.get("/api/v1/events")
    def events(isin: str | None = None, cutoff: date | None = None):
        with connect() as db:
            query = """SELECT e.*,x.status extraction_status,x.extracted_json,x.processed_at FROM company_events e
                LEFT JOIN extracted_events x ON x.event_id=e.id WHERE 1=1"""
            args = []
            if isin:
                query += " AND e.isin=?"
                args.append(isin)
            if cutoff:
                query += " AND e.published_at<=?"
                args.append(cutoff.isoformat() + "T23:59:59")
            return rows(db, query + " ORDER BY e.published_at DESC LIMIT 200", args)

    @app.post("/api/v1/events/{event_id}/extract", dependencies=[Depends(admin)])
    def event_extract(event_id: int):
        with connect() as db:
            event = db.execute("SELECT * FROM company_events WHERE id=?", (event_id,)).fetchone()
            if not event:
                raise HTTPException(404, "Event not found.")
            try:
                result, model = extract(dict(event))
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
            except Exception as exc:
                logger.warning(
                    "Event extraction failed for event %s: %s", event_id, type(exc).__name__
                )
                raise HTTPException(
                    502, "LLM extraction failed; original event remains available."
                ) from exc
            db.execute(
                """INSERT OR REPLACE INTO extracted_events
                (event_id,status,model,extracted_json,processed_at,error) VALUES(?,?,?,?,?,NULL)""",
                (event_id, "ok", model, json.dumps(result), utcnow()),
            )
            return result

    @app.get("/api/v1/readiness")
    def readiness(
        horizon: Literal["month", "quarter"] = "month",
        materiality: float = Query(0.1, ge=0.01, le=10),
        source_kind: Literal["user_import", "synthetic"] = "user_import",
    ):
        with connect() as db:
            labels = [
                case
                for case in build_labels(db, horizon, materiality)
                if case["source_kind"] == source_kind
            ]
            counts = {
                name: sum(case["label"] == name for case in labels)
                for name in ("addition", "negative", "accumulation", "exit", "unknown")
            }
            return {
                "horizon": horizon,
                "source_kind": source_kind,
                "label_counts": counts,
                **training_readiness(labels),
            }

    @app.post("/api/v1/training-runs", dependencies=[Depends(admin)])
    def training(body: TrainingInput):
        try:
            return train(body.horizon, body.materiality, body.source_kind)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/v1/training-runs")
    def runs():
        with connect() as db:
            results = rows(db, "SELECT * FROM training_runs ORDER BY id DESC LIMIT 50")
            for item in results:
                item["metrics"] = (
                    json.loads(item.pop("metrics_json")) if item["metrics_json"] else None
                )
                item.pop("artifact_path", None)
                item["current_method"] = item["model_version"] == MODEL_VERSION
            return results

    @app.get("/api/v1/backtests")
    def backtests(run_id: int | None = None):
        with connect() as db:
            if run_id is None:
                latest = db.execute(
                    "SELECT MAX(id) FROM training_runs WHERE status='complete'"
                ).fetchone()[0]
                run_id = latest
            if run_id is None:
                return []
            results = rows(
                db,
                """SELECT run_id,phase,period,model,metrics_json FROM evaluation_results
                WHERE run_id=? ORDER BY period,model""",
                (run_id,),
            )
            for item in results:
                item["metrics"] = json.loads(item.pop("metrics_json"))
            return results

    @app.get("/api/v1/predictions/{scheme_id}")
    def predictions(
        scheme_id: str, horizon: Literal["month", "quarter"] = "month", cutoff: date | None = None
    ):
        try:
            return predict(scheme_id, horizon, cutoff.isoformat() if cutoff else None)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/v1/evidence/{scheme_id}/{isin}")
    def evidence(scheme_id: str, isin: str, cutoff: date | None = None):
        with connect() as db:
            scheme = db.execute(
                "SELECT source_kind FROM schemes WHERE id=?", (scheme_id,)
            ).fetchone()
            if not scheme:
                raise HTTPException(404, "Fund not found.")
            limit = (cutoff or date.today()).isoformat()
            return {
                "holdings": rows(
                    db,
                    """SELECT p.report_date,p.published_at,p.availability_basis,p.source_url,h.weight,h.units
                FROM snapshots p JOIN holdings h ON h.snapshot_id=p.id WHERE p.scheme_id=? AND h.isin=?
                AND p.published_at<=? ORDER BY p.report_date DESC""",
                    (scheme_id, isin, limit),
                ),
                "market": rows(
                    db,
                    """SELECT date,close,adjusted_close,volume,source_url FROM market_observations
                WHERE isin=? AND date<=? AND source_kind=? ORDER BY date DESC LIMIT 30""",
                    (isin, limit, scheme["source_kind"]),
                ),
                "events": rows(
                    db,
                    """SELECT title,published_at,source_url,excerpt FROM company_events
                WHERE isin=? AND published_at<=? AND source_kind=? ORDER BY published_at DESC LIMIT 20""",
                    (isin, limit + "T23:59:59", scheme["source_kind"]),
                ),
            }

    return app


app = create_app()
