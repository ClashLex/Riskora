from datetime import UTC, datetime
from decimal import Decimal

from app.domain.models import Currency, Portfolio
from app.engine.exposure import analyze_exposure, build_exposure_positions
from tests.helpers import constituent, holding


def test_fund_lookthrough_aggregates_direct_and_fund_exposure_without_double_counting() -> None:
    direct = holding("direct-x", "1000", underlying_asset_id="asset-x")
    fund_a = holding("fund-a", "10000", asset_class="etf", sector=None)
    fund_b = holding("fund-b", "5000", asset_class="mutual_fund", sector=None)
    portfolio = Portfolio(
        id="test-portfolio",
        name="Test",
        base_currency=Currency.USD,
        holdings=[direct, fund_a, fund_b],
        created_at=datetime(2026, 6, 30, tzinfo=UTC),
    )
    constituents = [
        constituent("fund-a", "asset-x", "0.20"),
        constituent("fund-a", "asset-y", "0.80", name="Company Y", sector="Healthcare"),
        constituent("fund-b", "asset-x", "0.10"),
        constituent("fund-b", "asset-z", "0.90", name="Company Z", sector="Industrials"),
    ]

    exposure = analyze_exposure(portfolio, "USD", [], constituents)
    positions, _, _ = build_exposure_positions(portfolio, "USD", [], constituents)
    company_x = [item for item in positions if item.underlying_asset_id == "asset-x"]

    assert sum((item.value for item in company_x), Decimal("0")) == Decimal("3500.00")
    assert exposure["total_portfolio_value"] == 16000.0
    assert exposure["overlaps"][0]["total_exposure"] == 3500.0
    assert (
        exposure["fund_coverage"][0]["covered_value"]
        + exposure["fund_coverage"][1]["covered_value"]
        == 15000.0
    )


def test_partial_fund_coverage_is_reported_without_scaling() -> None:
    fund = holding("fund", "10000", asset_class="etf", sector=None)
    portfolio = Portfolio(
        id="portfolio",
        name="Partial",
        base_currency=Currency.USD,
        holdings=[fund],
        created_at=datetime(2026, 6, 30, tzinfo=UTC),
    )
    positions, warnings, coverage = build_exposure_positions(
        portfolio, "USD", [], [constituent("fund", "asset-x", "0.20")]
    )
    assert coverage["fund"] == Decimal("0.20")
    assert sum((item.value for item in positions), Decimal("0")) == Decimal("10000.00")
    assert any("PARTIAL_LOOKTHROUGH" in warning for warning in warnings)


def test_invalid_total_constituent_weight_is_not_counted_twice() -> None:
    fund = holding("fund", "10000", asset_class="etf", sector=None)
    portfolio = Portfolio(
        id="portfolio",
        name="Invalid",
        base_currency=Currency.USD,
        holdings=[fund],
        created_at=datetime(2026, 6, 30, tzinfo=UTC),
    )
    positions, warnings, _ = build_exposure_positions(
        portfolio,
        "USD",
        [],
        [constituent("fund", "asset-a", "0.60"), constituent("fund", "asset-b", "0.50")],
    )
    assert sum((item.value for item in positions), Decimal("0")) == Decimal("10000")
    assert any("INVALID_CONSTITUENT_WEIGHTS" in warning for warning in warnings)
