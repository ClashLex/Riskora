"""Check that an ephemeral demo starts with usable public research screens."""

from app.main import create_app
from fastapi.testclient import TestClient


def test_synthetic_demo_bootstrap_is_usable_and_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("RISKORA_DB", str(tmp_path / "riskora.sqlite3"))
    monkeypatch.setenv("RISKORA_UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("RISKORA_AUTO_LOAD_SYNTHETIC", "true")
    monkeypatch.setenv("RISKORA_AUTO_TRAIN_SYNTHETIC", "true")

    client = TestClient(create_app())
    overview = client.get("/api/v1/overview").json()
    assert overview["synthetic_observations"] == 30
    assert overview["training_status"] == "trained"
    assert client.get("/api/v1/backtests").json()
    ranking = client.get("/api/v1/predictions/synthetic_fund_1")
    assert ranking.status_code == 200
    assert ranking.json()["source_kind"] == "synthetic"

    restarted = TestClient(create_app())
    assert len(restarted.get("/api/v1/training-runs").json()) == 1
