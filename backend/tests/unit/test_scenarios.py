import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.errors import ApiError
from app.domain.models import Currency, FxRate, Portfolio, ScenarioRequest
from app.engine.scenarios import run_scenario
from tests.helpers import holding


def scenario_catalog() -> list[dict]:
    path = Path(__file__).resolve().parents[2] / "app" / "data" / "demo_scenarios.json"
    return json.loads(path.read_text(encoding="utf-8"))


def portfolio_with(*holdings, base_currency: str = "USD") -> Portfolio:
    return Portfolio(
        id="scenario-test",
        name="Scenario test",
        base_currency=Currency(base_currency),
        holdings=list(holdings),
        created_at=datetime(2026, 6, 30, tzinfo=UTC),
    )


def test_ten_percent_shock_on_twenty_thousand_reconciles() -> None:
    portfolio = portfolio_with(holding("stock", "20000"))
    result = run_scenario(
        portfolio,
        ScenarioRequest(
            scenario_id="broad_market_down", asset_shock_percent=-10, fx_shock_percent=0
        ),
        [],
        [],
        scenario_catalog(),
    )
    assert result["estimated_change"] == -2000.0
    assert result["portfolio_value_after"] == 18000.0
    assert (
        sum(row["estimated_change_base_value"] for row in result["rows"])
        == result["estimated_change"]
    )


def test_total_loss_and_below_minus_one_hundred_validation() -> None:
    portfolio = portfolio_with(holding("stock", "1000"))
    result = run_scenario(
        portfolio,
        ScenarioRequest(
            scenario_id="broad_market_down", asset_shock_percent=-100, fx_shock_percent=0
        ),
        [],
        [],
        scenario_catalog(),
    )
    assert result["portfolio_value_after"] == 0
    with pytest.raises(ValidationError):
        ScenarioRequest(scenario_id="broad_market_down", asset_shock_percent=-100.01)


def test_combined_asset_and_fx_returns_compound() -> None:
    portfolio = portfolio_with(holding("euro-stock", "1000", currency="EUR"))
    fx = FxRate(
        base_currency=Currency.USD,
        foreign_currency=Currency.EUR,
        rate=Decimal("1.08"),
        as_of_date=date(2026, 6, 30),
        source_label="Test FX",
        source_id="src-test-fx",
    )
    result = run_scenario(
        portfolio,
        ScenarioRequest(
            scenario_id="combined_market_fx_shock",
            asset_shock_percent=-10,
            fx_shock_percent=5,
        ),
        [fx],
        [],
        scenario_catalog(),
    )
    row = result["rows"][0]
    assert row["asset_return"] == -0.1
    assert row["fx_return"] == 0.05
    assert row["estimated_change_base_value"] == pytest.approx(-59.4)


@pytest.mark.parametrize(
    ("scenario_id", "expected_fx_return"),
    [("usd_strengthens", -0.10), ("usd_weakens", 0.10)],
)
def test_usd_presets_apply_consistent_fx_direction(
    scenario_id: str,
    expected_fx_return: float,
) -> None:
    portfolio = portfolio_with(holding("euro-stock", "1000", currency="EUR"))
    fx = FxRate(
        base_currency=Currency.USD,
        foreign_currency=Currency.EUR,
        rate=Decimal("1.08"),
        as_of_date=date(2026, 6, 30),
        source_label="Test FX",
        source_id="src-test-fx",
    )
    result = run_scenario(
        portfolio,
        ScenarioRequest(scenario_id=scenario_id),
        [fx],
        [],
        scenario_catalog(),
    )
    assert result["rows"][0]["fx_return"] == expected_fx_return


def test_unknown_sector_and_hedge_mapping_are_not_silently_assumed() -> None:
    unknown = holding("unknown", "500", sector=None)
    portfolio = portfolio_with(unknown)
    result = run_scenario(
        portfolio,
        ScenarioRequest(scenario_id="technology_sector_down"),
        [],
        [],
        scenario_catalog(),
    )
    assert result["is_complete"] is False
    assert result["estimated_change"] is None
    assert result["rows"][0]["data_status"] == "not_modelled"
    assert result["rows"][0]["estimated_change_base_value"] is None


def test_custom_scenario_rejects_unknown_asset_ids() -> None:
    with pytest.raises(ApiError) as error:
        run_scenario(
            portfolio_with(holding("known", "1000")),
            ScenarioRequest(
                scenario_id="custom",
                asset_shock_percent=-5,
                affected_asset_ids=["not-in-portfolio"],
            ),
            [],
            [],
            scenario_catalog(),
        )
    assert error.value.code == "UNKNOWN_SCENARIO_ASSET"
