from datetime import date
from decimal import Decimal

from app.domain.models import AssetClass, Currency, DataStatus, FundConstituent, Holding


def holding(
    holding_id: str,
    market_value: str,
    *,
    currency: str = "USD",
    asset_class: str = "stock",
    sector: str | None = "Technology",
    underlying_asset_id: str | None = None,
    fx_hedged: bool | None = False,
) -> Holding:
    return Holding(
        id=holding_id,
        name=holding_id.replace("-", " ").title(),
        underlying_asset_id=underlying_asset_id,
        asset_class=AssetClass(asset_class),
        market_value=Decimal(market_value),
        currency=Currency(currency),
        sector=sector,
        country="United States",
        source_label="Test fixture",
        source_id="src-test",
        as_of_date=date(2026, 6, 30),
        data_status=DataStatus.USER_ENTERED,
        fx_hedged=fx_hedged,
    )


def constituent(
    fund_id: str,
    asset_id: str,
    weight: str,
    *,
    name: str = "Company X",
    sector: str = "Technology",
    currency: str = "USD",
) -> FundConstituent:
    return FundConstituent(
        fund_id=fund_id,
        underlying_asset_id=asset_id,
        underlying_name=name,
        weight=Decimal(weight),
        sector=sector,
        country="United States",
        currency=Currency(currency),
        as_of_date=date(2026, 6, 30),
    )
