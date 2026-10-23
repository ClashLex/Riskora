from datetime import date

from app.domain.models import FxRate, Portfolio
from app.engine.provenance import stale_data_warnings
from app.engine.valuation import value_portfolio


def portfolio_response(portfolio: Portfolio, rates: list[FxRate]) -> dict:
    valuation = value_portfolio(portfolio, portfolio.base_currency.value, rates)
    warnings = [
        f"FX_RATE_MISSING: holding {holding_id} cannot be converted "
        f"to {portfolio.base_currency.value}."
        for holding_id in valuation.unconverted_holding_ids
    ]
    used_source_ids = {source_id for item in valuation.holdings for source_id in item.source_ids}
    warnings.extend(
        stale_data_warnings(
            [holding.as_of_date for holding in portfolio.holdings]
            + [rate.as_of_date for rate in rates if rate.source_id in used_source_ids]
        )
    )
    return {
        **portfolio.model_dump(mode="json"),
        "total_value": float(valuation.total_value),
        "value_complete": valuation.value_complete,
        "as_of_dates": sorted({holding.as_of_date.isoformat() for holding in portfolio.holdings}),
        "holding_valuations": [
            {
                "holding_id": item.holding_id,
                "original_value": float(item.original_value),
                "original_currency": item.original_currency,
                "base_value": float(item.base_value) if item.base_value is not None else None,
                "fx_rate": float(item.fx_rate) if item.fx_rate is not None else None,
                "fx_path": list(item.fx_path),
                "source_ids": list(item.source_ids),
            }
            for item in valuation.holdings
        ],
        "warnings": warnings,
    }


def portfolio_summary(portfolio: Portfolio, rates: list[FxRate]) -> dict:
    valuation = value_portfolio(portfolio, portfolio.base_currency.value, rates)
    return {
        "id": portfolio.id,
        "name": portfolio.name,
        "base_currency": portfolio.base_currency.value,
        "total_value": float(valuation.total_value),
        "value_complete": valuation.value_complete,
        "holding_count": len(portfolio.holdings),
        "data_status": portfolio.data_status.value,
        "is_demo": portfolio.is_demo,
    }


def valuation_as_of_dates(portfolio: Portfolio) -> list[date]:
    return sorted({holding.as_of_date for holding in portfolio.holdings})
