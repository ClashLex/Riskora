from fastapi.testclient import TestClient

from app.main import create_app


def test_health_openapi_and_required_endpoints() -> None:
    client = TestClient(create_app())
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {
        "status": "ok",
        "service": "risvanta-backend",
        "version": "0.1.0",
        "data_mode": "illustrative",
    }
    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    assert {
        "/health",
        "/api/v1/portfolios",
        "/api/v1/portfolios/{portfolio_id}",
        "/api/v1/portfolios/{portfolio_id}/holdings",
        "/api/v1/portfolios/{portfolio_id}/holdings/{holding_id}",
        "/api/v1/portfolios/{portfolio_id}/load-demo",
        "/api/v1/portfolios/{portfolio_id}/exposure",
        "/api/v1/portfolios/{portfolio_id}/insights",
        "/api/v1/portfolios/{portfolio_id}/scenarios/run",
        "/api/v1/scenarios",
        "/api/v1/portfolios/{portfolio_id}/explanations",
    } <= set(openapi.json()["paths"])
    assert client.get("/api/v1/portfolios").status_code == 200
    assert client.get("/api/v1/scenarios").status_code == 200
    assert client.get("/api/v1/portfolios/demo-global").status_code == 200


def test_unknown_resources_and_invalid_requests_use_consistent_errors() -> None:
    client = TestClient(create_app())
    missing = client.get("/api/v1/portfolios/not-here")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "PORTFOLIO_NOT_FOUND"
    invalid = client.post(
        "/api/v1/portfolios/demo-global/scenarios/run",
        json={"scenario_id": "broad_market_down", "asset_shock_percent": -101},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"


def test_portfolio_crud_and_demo_reset() -> None:
    client = TestClient(create_app())
    created = client.post(
        "/api/v1/portfolios",
        json={"name": "My test portfolio", "base_currency": "USD"},
    )
    assert created.status_code == 201
    portfolio_id = created.json()["id"]
    holding = client.post(
        f"/api/v1/portfolios/{portfolio_id}/holdings",
        json={
            "name": "New holding",
            "asset_class": "stock",
            "market_value": 2500,
            "currency": "USD",
            "sector": "Technology",
            "as_of_date": "2026-06-30",
        },
    )
    assert holding.status_code == 201
    holding_id = holding.json()["holdings"][0]["id"]
    user_sources = client.get(f"/api/v1/portfolios/{portfolio_id}/exposure").json()["sources"]
    assert user_sources[0]["id"] == "src-user-entry"
    assert user_sources[0]["data_status"] == "user_entered"
    updated = client.patch(
        f"/api/v1/portfolios/{portfolio_id}/holdings/{holding_id}",
        json={"market_value": 3000},
    )
    assert updated.status_code == 200
    assert updated.json()["total_value"] == 3000
    deleted = client.delete(f"/api/v1/portfolios/{portfolio_id}/holdings/{holding_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/portfolios/{portfolio_id}").json()["total_value"] == 0

    before = client.get("/api/v1/portfolios/demo-global").json()["total_value"]
    client.post(
        "/api/v1/portfolios/demo-global/holdings",
        json={
            "name": "Temporary",
            "asset_class": "stock",
            "market_value": 10,
            "currency": "USD",
            "as_of_date": "2026-06-30",
        },
    )
    reset = client.post("/api/v1/portfolios/demo-global/load-demo")
    assert reset.status_code == 200
    assert reset.json()["total_value"] == before
    assert len(reset.json()["holdings"]) == 7


def test_exposure_scenario_and_grounded_explanation() -> None:
    client = TestClient(create_app())
    exposure = client.get("/api/v1/portfolios/demo-global/exposure")
    assert exposure.status_code == 200
    payload = exposure.json()
    assert payload["groups"]["sector"]
    assert payload["overlaps"]
    assert payload["fund_coverage"]
    assert all(source["data_status"] == "illustrative" for source in payload["sources"])

    result = client.post(
        "/api/v1/portfolios/demo-global/scenarios/run",
        json={"scenario_id": "broad_market_down"},
    )
    assert result.status_code == 200
    body = result.json()
    assert body["is_simulation"] is True
    assert body["is_complete"] is True
    assert (
        sum(row["estimated_change_base_value"] for row in body["rows"]) == body["estimated_change"]
    )
    explained = client.post(
        "/api/v1/portfolios/demo-global/explanations",
        json={"result_id": body["result_id"], "question": "What does this result show?"},
    )
    assert explained.status_code == 200
    assert explained.json()["mode"] == "template"
    assert explained.json()["source_ids"]
    assert (
        client.post(
            "/api/v1/portfolios/demo-global/explanations",
            json={"result_id": "client-invented-result", "question": "Explain"},
        ).status_code
        == 404
    )


def test_cors_is_limited_to_configured_origin() -> None:
    client = TestClient(create_app())
    allowed = client.options(
        "/api/v1/portfolios",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    denied = client.options(
        "/api/v1/portfolios",
        headers={
            "Origin": "https://unexpected.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in denied.headers
