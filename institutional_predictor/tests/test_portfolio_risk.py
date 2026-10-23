import pytest
from fastapi.testclient import TestClient

from institutional_predictor import app as predictor
from institutional_predictor.portfolio_risk import AnalyzeRequest, analyze_portfolio


def test_analyze_calculates_allocations_and_combined_stress():
    request = AnalyzeRequest(
        portfolio=[
            {
                "type": "equity",
                "symbol": "TCS",
                "quantity": 10,
                "price": 3000,
                "currency": "INR",
                "sector": "IT",
            },
            {
                "type": "mf",
                "symbol": "Fund A",
                "quantity": 200,
                "price": 50,
                "constituents": [
                    {"symbol": "TCS", "weight": 0.1, "sector": "IT"},
                    {"symbol": "HDFC Bank", "weight": 0.2, "sector": "Banking"},
                ],
            },
            {
                "type": "us_stock",
                "symbol": "AAPL",
                "quantity": 5,
                "price": 150,
                "currency": "USD",
                "sector": "Technology",
            },
        ],
        scenario={"equityShockPercent": -10, "usdInrChange": 5},
        usd_inr_rate=80,
    )

    result = analyze_portfolio(request)

    assert result["totalValueInr"] == pytest.approx(100_000)
    assert sum(result["allocations"]["sectors"].values()) == pytest.approx(1)
    assert sum(result["allocations"]["currencies"].values()) == pytest.approx(1)
    assert sum(result["allocations"]["assetClasses"].values()) == pytest.approx(1)
    assert result["stressResults"]["marketShockPnl"] == pytest.approx(-9_300)
    assert result["stressResults"]["fxShockPnl"] == pytest.approx(2_700)
    assert result["stressResults"]["newPortfolioValue"] == pytest.approx(93_400)
    assert result["overlaps"] == []


def test_analyze_finds_cross_fund_overlap_and_citations():
    request = AnalyzeRequest(
        portfolio=[
            {
                "type": "mf",
                "symbol": "Fund A",
                "quantity": 100,
                "price": 100,
                "source_url": "https://example.org/fund-a",
                "constituents": [
                    {
                        "symbol": "RELIANCE",
                        "weight": 0.2,
                        "sector": "Energy",
                        "source_url": "https://example.org/a-holdings",
                    }
                ],
            },
            {
                "type": "mf",
                "symbol": "Fund B",
                "quantity": 100,
                "price": 100,
                "constituents": [
                    {
                        "symbol": "reliance",
                        "weight": 0.1,
                        "sector": "Energy",
                    }
                ],
            },
        ],
        usd_inr_rate=83.5,
    )

    result = analyze_portfolio(request)

    assert result["overlaps"][0]["symbol"] == "RELIANCE"
    assert result["overlaps"][0]["totalOverlapPercent"] == pytest.approx(15)
    assert result["overlaps"][0]["funds"][0]["weight"] == pytest.approx(0.1)
    assert result["sources"] == [
        {"name": "Fund A constituent data", "url": "https://example.org/a-holdings"},
        {"name": "Fund A holding data", "url": "https://example.org/fund-a"},
    ]


def test_analyze_marks_unprovided_mutual_fund_weight_as_other():
    result = analyze_portfolio(
        AnalyzeRequest(
            portfolio=[
                {
                    "type": "mf",
                    "symbol": "Fund A",
                    "quantity": 10,
                    "price": 100,
                    "constituents": [
                        {"symbol": "TCS", "weight": 0.4, "sector": "IT"}
                    ],
                }
            ]
        )
    )

    assert result["allocations"]["assetClasses"] == {"Equity": 0.4, "Other": 0.6}
    assert result["allocations"]["sectors"] == {"IT": 0.4, "Others": 0.6}


def test_usd_mutual_fund_constituent_uses_inr_nav_weight_without_double_conversion():
    result = analyze_portfolio(
        AnalyzeRequest(
            portfolio=[
                {
                    "type": "mf",
                    "symbol": "Global Fund",
                    "quantity": 10,
                    "price": 100,
                    "constituents": [
                        {
                            "symbol": "US Equity",
                            "weight": 0.2,
                            "currency": "USD",
                            "sector": "Technology",
                        },
                        {
                            "symbol": "Indian Equity",
                            "weight": 0.3,
                            "currency": "INR",
                            "sector": "Banking",
                        },
                    ],
                }
            ],
            scenario={"equityShockPercent": -10, "usdInrChange": 10},
            usd_inr_rate=80,
        )
    )

    assert result["totalValueInr"] == pytest.approx(1000)
    assert result["riskMetrics"]["usdExposureInr"] == pytest.approx(200)
    assert result["stressResults"]["marketShockPnl"] == pytest.approx(-50)
    assert result["stressResults"]["fxShockPnl"] == pytest.approx(18)
    assert result["stressResults"]["newPortfolioValue"] == pytest.approx(968)


def test_request_rejects_invalid_fund_weights_and_source_url():
    with pytest.raises(ValueError):
        AnalyzeRequest(
            portfolio=[
                {
                    "type": "mf",
                    "symbol": "Fund A",
                    "quantity": 1,
                    "price": 10,
                    "constituents": [
                        {"symbol": "A", "weight": 0.7},
                        {"symbol": "B", "weight": 0.4},
                    ],
                }
            ]
        )

    with pytest.raises(ValueError):
        AnalyzeRequest(
            portfolio=[
                {
                    "type": "equity",
                    "symbol": "A",
                    "quantity": 1,
                    "price": 10,
                    "source_url": "javascript:alert(1)",
                }
            ]
        )


def test_analyze_endpoint_processes_request_without_persisting_it(tmp_path, monkeypatch):
    monkeypatch.setattr(predictor, "DATABASE_PATH", tmp_path / "unused.sqlite3")
    client = TestClient(predictor.app)
    response = client.post(
        "/api/analyze",
        json={
            "portfolio": [
                {
                    "type": "equity",
                    "symbol": "TCS",
                    "quantity": 2,
                    "price": 100,
                    "sector": "IT",
                }
            ],
            "scenario": {"equityShockPercent": -10, "usdInrChange": 5},
        },
    )

    assert response.status_code == 200
    assert response.json()["stressResults"]["newPortfolioValue"] == pytest.approx(180)
    assert not (tmp_path / "unused.sqlite3").exists()


def test_analyze_endpoint_rejects_incomplete_scenario():
    response = TestClient(predictor.app).post(
        "/api/analyze",
        json={
            "portfolio": [
                {"type": "equity", "symbol": "TCS", "quantity": 2, "price": 100}
            ],
            "scenario": {"equityShockPercent": -10},
        },
    )

    assert response.status_code == 422


def test_analyze_accepts_the_report_api_field_names():
    request = AnalyzeRequest.model_validate(
        {
            "portfolio": [
                {
                    "type": "equity",
                    "symbol": "TCS",
                    "quantity": 10,
                    "price": 3000,
                    "currency": "INR",
                },
                {
                    "type": "mf",
                    "amc": "ICICI",
                    "schemeCode": "123456",
                    "units": 200,
                    "nav": 50,
                },
                {
                    "type": "us_stock",
                    "symbol": "AAPL",
                    "quantity": 5,
                    "price": 150,
                    "currency": "USD",
                },
            ],
            "scenario": {"equityShockPercent": -10, "usdInrChange": 5},
            "usdInrRate": 80,
        }
    )

    result = analyze_portfolio(request)

    assert result["totalValueInr"] == pytest.approx(100_000)
    assert result["stressResults"]["newPortfolioValue"] == pytest.approx(93_700)
