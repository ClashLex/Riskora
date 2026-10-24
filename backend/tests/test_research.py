import json
import sqlite3

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.db import connect
from app.ingestion import ImportProblem, import_holdings, import_market
from app.main import create_app
from app.ml import available_training, build_labels, features, training_readiness


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("RISKORA_DB", str(tmp_path / "test.sqlite3"))
    monkeypatch.setenv("RISKORA_UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("RISKORA_ADMIN_TOKEN", "test-secret")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    return TestClient(create_app())


def holding_csv(*rows):
    return ("isin,company,weight,units,sector,industry,ticker\n" + "\n".join(rows) + "\n").encode()


def import_snapshot(data, report, publication, complete=True):
    return import_holdings(
        data,
        scheme_id="fund_1",
        scheme_name="Test Fund",
        amc="Test AMC",
        report_date=report,
        published_at=publication,
        source_url="https://example.org/disclosure.csv",
        complete=complete,
    )


def test_import_validation_and_duplicate_snapshot(client):
    with pytest.raises(ImportProblem, match="Duplicate holding"):
        import_snapshot(
            holding_csv(
                "IN0000000001,Company A,50,10,Banks,Banks,AAA",
                "IN0000000001,Company A,50,10,Banks,Banks,AAA",
            ),
            "2024-01-31",
            "2024-02-08",
        )
    with pytest.raises(ImportProblem, match="well-formed Indian ISIN"):
        import_snapshot(
            holding_csv("BAD,Company A,100,10,Banks,Banks,AAA"), "2024-01-31", "2024-02-08"
        )
    imported = import_snapshot(
        holding_csv("IN0000000001,Company A,100,10,Banks,Banks,AAA"), "2024-01-31", "2024-02-08"
    )
    assert imported["complete"]
    with pytest.raises(sqlite3.IntegrityError):
        import_snapshot(
            holding_csv("IN0000000001,Company A,100,10,Banks,Banks,AAA"), "2024-01-31", "2024-02-08"
        )
    assert client.get("/api/v1/overview").json()["observations"] == 1


def test_observed_disclosure_remains_ineligible_for_labels(client):
    data = holding_csv("IN0000000001,Company A,100,10,Banks,Banks,AAA")
    import_snapshot(data, "2024-01-31", "2024-02-08")
    result = import_holdings(
        data,
        scheme_id="fund_1",
        scheme_name="Test Fund",
        amc="Test AMC",
        report_date="2024-02-29",
        published_at="2024-04-15",
        source_url="https://example.org/disclosures",
        complete=True,
        availability_basis="observed",
    )
    assert result["complete"] is False
    fund = client.get("/api/v1/funds/fund_1").json()
    assert fund["snapshots"][0]["availability_basis"] == "observed"
    assert "publication date is unverified" in fund["snapshots"][0]["warnings"][0].lower()
    with connect() as db:
        assert {case["label"] for case in build_labels(db)} == {"unknown"}


def test_market_import_retains_per_observation_source_url(client):
    data = (
        b"date,isin,company,close,volume,source_url\n"
        b"2024-01-30,IN0000000001,Company A,100,0,https://example.org/2024-01-30.zip\n"
    )
    import_market(data, source_url="https://example.org/reports")
    with connect() as db:
        row = db.execute("SELECT volume,source_url FROM market_observations").fetchone()
    assert row["volume"] == 0
    assert row["source_url"] == "https://example.org/2024-01-30.zip"


def test_ambiguous_identifier_and_incomplete_unknown(client):
    first = holding_csv("IN0000000001,Company A,100,10,Banks,Banks,AAA")
    import_snapshot(first, "2024-01-31", "2024-02-08")
    with pytest.raises(ImportProblem, match="Ambiguous"):
        import_snapshot(
            holding_csv("IN0000000001,Other Company,100,10,Banks,Banks,AAA"),
            "2024-02-29",
            "2024-03-08",
        )
    import_snapshot(
        holding_csv("IN0000000002,Company B,50,10,Tech,Software,BBB"),
        "2024-02-29",
        "2024-03-08",
        complete=False,
    )
    with connect() as db:
        cases = build_labels(db)
    assert cases and all(case["label"] == "unknown" for case in cases)


def test_addition_accumulation_exit_and_cutoff(client):
    market = (
        b"date,isin,company,close,volume,sector,industry,ticker\n"
        b"2024-01-30,IN0000000002,Company B,100,1000,Tech,Software,BBB\n"
        b"2024-02-01,IN0000000002,Company B,101,1100,Tech,Software,BBB\n"
    )
    import_market(market, source_url="https://example.org/market.csv")
    import_snapshot(
        holding_csv("IN0000000001,Company A,100,10,Banks,Banks,AAA"), "2024-01-31", "2024-02-08"
    )
    import_snapshot(
        holding_csv(
            "IN0000000001,Company A,50,12,Banks,Banks,AAA",
            "IN0000000002,Company B,50,10,Tech,Software,BBB",
        ),
        "2024-02-29",
        "2024-03-08",
    )
    import_snapshot(
        holding_csv("IN0000000002,Company B,100,10,Tech,Software,BBB"), "2024-03-31", "2024-04-08"
    )
    with connect() as db:
        cases = build_labels(db)
        labels = {(c["cutoff"], c["isin"]): c["label"] for c in cases}
        values, evidence = features(db, "fund_1", "IN0000000002", "2024-02-08")
    assert labels[("2024-02-08", "IN0000000002")] == "addition"
    assert labels[("2024-02-08", "IN0000000001")] == "accumulation"
    assert labels[("2024-03-08", "IN0000000001")] == "exit"
    changes = client.get("/api/v1/funds/fund_1").json()
    assert changes["changes_total"] == len(changes["changes"])
    assert [case["cutoff"] for case in changes["changes"]] == sorted(
        (case["cutoff"] for case in changes["changes"]), reverse=True
    )
    assert values["market_available"] == 1
    assert all(item["date"] <= "2024-02-08" for item in evidence)
    assert (
        client.get("/api/v1/evidence/fund_1/IN0000000002?cutoff=2024-02-08").json()["holdings"]
        == []
    )


def test_admin_absent_llm_and_stale_event(client):
    assert client.post("/api/v1/demo/load").status_code == 401
    import_snapshot(
        holding_csv("IN0000000001,Company A,100,10,Banks,Banks,AAA"), "2024-01-31", "2024-02-08"
    )
    event = {
        "isin": "IN0000000001",
        "title": "Quarterly result",
        "category": "earnings",
        "published_at": "2024-04-01T09:00:00+00:00",
        "source_url": "https://example.org/result",
        "excerpt": "Company A reported sales of 100 crore for the quarter.",
    }
    response = client.post("/api/v1/events", headers={"X-Admin-Token": "test-secret"}, json=event)
    assert response.status_code == 200
    event_id = response.json()["event_id"]
    assert (
        client.post(
            f"/api/v1/events/{event_id}/extract", headers={"X-Admin-Token": "test-secret"}
        ).status_code
        == 422
    )
    assert client.get("/api/v1/events?cutoff=2024-03-01").json() == []
    with connect() as db:
        db.execute(
            "INSERT INTO extracted_events(event_id,status,model,extracted_json,processed_at) VALUES(?,?,?,?,?)",
            (
                event_id,
                "ok",
                "test",
                json.dumps({"direction": "positive"}),
                "2024-04-02T00:00:00+00:00",
            ),
        )
    with connect() as db:
        early, _ = features(db, "fund_1", "IN0000000001", "2024-02-08")
        later, _ = features(db, "fund_1", "IN0000000001", "2024-04-03")
    assert early["event_available"] == 0
    assert later["event_available"] == 1


def test_api_upload_and_identifier_review(client):
    headers = {"X-Admin-Token": "test-secret"}
    file_data = holding_csv("IN0000000001,Company A,100,10,Banks,Banks,AAA")
    response = client.post(
        "/api/v1/imports/holdings",
        headers=headers,
        data={
            "scheme_id": "fund_1",
            "scheme_name": "Test Fund",
            "amc": "Test AMC",
            "report_date": "2024-01-31",
            "published_at": "2024-02-08",
            "source_url": "https://example.org/disclosure.csv",
            "complete": "true",
        },
        files={"file": ("holdings.csv", file_data, "text/csv")},
    )
    assert response.status_code == 200, response.text
    assert client.get("/api/v1/identifiers").json()[0]["ticker"] == "AAA"
    updated = client.put(
        "/api/v1/identifiers/IN0000000001",
        headers=headers,
        json={"ticker": "NEWAAA", "source_url": "https://example.org/mapping"},
    )
    assert updated.status_code == 200
    assert client.get("/api/v1/identifiers").json()[0]["reviewed_at"]
    assert (
        client.post(
            "/api/v1/imports/market",
            headers=headers,
            data={"source_url": "https://example.org/prices"},
            files={"file": ("bad.txt", b"x", "text/plain")},
        ).status_code
        == 422
    )
    duplicate = (
        b"date,isin,company,close,volume\n"
        b"2024-01-31,IN0000000001,Company A,100,1000\n"
        b"2024-01-31,IN0000000001,Company A,101,1000\n"
    )
    with pytest.raises(ImportProblem, match="Duplicate market observation"):
        import_market(duplicate, source_url="https://example.org/market.csv")


def test_synthetic_end_to_end_is_isolated(client):
    headers = {"X-Admin-Token": "test-secret"}
    demo = client.post("/api/v1/demo/load", headers=headers)
    assert demo.status_code == 200, demo.text
    assert demo.json()["source_kind"] == "synthetic"
    assert client.get("/api/v1/readiness?source_kind=user_import").json()["ready"] is False
    assert client.get("/api/v1/readiness?source_kind=synthetic").json()["ready"] is True
    result = client.post(
        "/api/v1/training-runs",
        headers=headers,
        json={"horizon": "month", "source_kind": "synthetic"},
    )
    assert result.status_code == 200, result.text
    assert result.json()["metrics"]["full_event_model"]["status"] == "unavailable"
    backtests = client.get("/api/v1/backtests").json()
    assert any(row["phase"] == "validation" for row in backtests)
    assert any(row["phase"] == "holdout" for row in backtests)
    output = client.get("/api/v1/predictions/synthetic_fund_1")
    assert output.status_code == 200, output.text
    assert output.json()["candidates"]
    assert output.json()["score_type"] == "uncalibrated ranking score"
    assert output.json()["candidates"][0]["contributions"]
    assert output.json()["model_version"] == "logistic-v2"
    assert output.json()["published_at"] == output.json()["cutoff"]
    assert output.json()["generated_at"]
    run_id = result.json()["run_id"]
    assert all(row["run_id"] == run_id for row in backtests)
    assert client.get("/api/v1/training-runs").json()[0]["current_method"]
    # A newer incomplete statement must not silently fall back to older holdings.
    with connect() as db:
        db.execute(
            "UPDATE snapshots SET complete=0 WHERE scheme_id='synthetic_fund_1' AND report_date=(SELECT MAX(report_date) FROM snapshots WHERE scheme_id='synthetic_fund_1')"
        )
    incomplete = client.get("/api/v1/predictions/synthetic_fund_1")
    assert incomplete.status_code == 422
    assert "incomplete" in incomplete.json()["detail"]
    with connect() as db:
        db.execute("UPDATE training_runs SET model_version='logistic-v1'")
    assert client.get("/api/v1/predictions/synthetic_fund_2").status_code == 422
    assert client.get("/api/v1/training-runs").json()[0]["current_method"] is False


def test_training_excludes_labels_published_after_evaluation_cutoff(client, monkeypatch):
    cases = [
        {
            "cutoff": day,
            "target_published_at": published,
            "label": label,
            "source_kind": "user_import",
        }
        for day, published, label in [
            ("2024-01-08", "2024-02-08", "negative"),
            ("2024-02-08", "2024-05-08", "addition"),
            ("2024-03-08", "2024-05-08", "addition"),
            ("2024-04-08", "2024-05-08", "negative"),
        ]
    ]
    # Four cutoff periods and both classes globally are insufficient if the positive
    # outcomes were still undisclosed at the final holdout cutoff.
    readiness = training_readiness(cases)
    assert readiness["usable_periods"] == 4
    assert readiness["ready"] is False
    frame = pd.DataFrame(cases)
    eligible = available_training(frame, "2024-04-08")
    assert eligible["cutoff"].tolist() == ["2024-01-08"]
    monkeypatch.setattr("app.main.build_labels", lambda *args: cases)
    response = client.get("/api/v1/readiness").json()
    assert response["ready"] is False
    assert response["blockers"] == readiness["blockers"]
    cases[1]["target_published_at"] = "2024-04-08"
    assert training_readiness(cases)["ready"] is True


def test_market_source_filter_and_event_timezone(client):
    market = b"date,isin,company,close,volume\n2024-01-01,IN0000000001,Company A,100,10\n"
    import_market(market, source_url="https://example.org/prices")
    import_market(market, source_url="sample://prices", source_kind="synthetic")
    real = client.get("/api/v1/market?isin=IN0000000001").json()
    sample = client.get("/api/v1/market?isin=IN0000000001&source_kind=synthetic").json()
    assert len(real) == len(sample) == 1
    assert real[0]["source_kind"] == "user_import"
    assert sample[0]["source_kind"] == "synthetic"
    response = client.post(
        "/api/v1/events",
        headers={"X-Admin-Token": "test-secret"},
        json={
            "isin": "IN0000000001",
            "title": "Dated result",
            "category": "earnings",
            "published_at": "2024-01-02T01:00:00+05:30",
            "source_url": "https://example.org/result",
            "excerpt": "Company A reported revenue in its statement.",
        },
    )
    assert response.status_code == 200
    events = client.get("/api/v1/events?cutoff=2024-01-01").json()
    assert len(events) == 1
    assert events[0]["published_at"] == "2024-01-01T19:30:00+00:00"
