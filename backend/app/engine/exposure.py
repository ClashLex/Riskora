from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.domain.models import DataStatus, FundConstituent, FxRate, Holding, Portfolio
from app.engine.provenance import stale_data_warnings
from app.engine.valuation import ZERO, value_holding, value_portfolio

WEIGHT_TOLERANCE = Decimal("0.01")


@dataclass(frozen=True)
class ExposurePosition:
    id: str
    name: str
    value: Decimal
    asset_class: str
    sector: str | None
    country: str | None
    currency: str | None
    underlying_asset_id: str | None
    holding_ids: tuple[str, ...]
    source_ids: tuple[str, ...]
    as_of_date: str
    data_status: str
    fx_hedged: bool | None
    is_fund_derived: bool
    is_residual: bool = False


def build_exposure_positions(
    portfolio: Portfolio,
    base_currency: str,
    rates: list[FxRate],
    constituents: list[FundConstituent],
) -> tuple[list[ExposurePosition], list[str], dict[str, Decimal]]:
    positions: list[ExposurePosition] = []
    warnings: list[str] = []
    fund_coverage: dict[str, Decimal] = {}
    constituents_by_fund: dict[str, list[FundConstituent]] = defaultdict(list)
    for item in constituents:
        constituents_by_fund[item.fund_id].append(item)

    for holding in portfolio.holdings:
        valuation = value_holding(holding, base_currency, rates)
        if valuation.base_value is None:
            warnings.append(
                f"FX_RATE_MISSING: holding {holding.id} cannot be converted to {base_currency}."
            )
            continue

        fund_items = constituents_by_fund.get(holding.id, [])
        if holding.asset_class in ("etf", "mutual_fund"):
            total_weight = sum((item.weight for item in fund_items), ZERO)
            if total_weight > Decimal("1"):
                warnings.append(
                    f"INVALID_CONSTITUENT_WEIGHTS: fund {holding.id} weights exceed 100%; "
                    "look-through for this fund is not modelled."
                )
                fund_coverage[holding.id] = ZERO
                positions.append(
                    _position(
                        holding,
                        holding.id,
                        holding.name,
                        valuation.base_value,
                        holding.sector,
                        holding.country,
                        None,
                        holding.underlying_asset_id,
                        valuation.source_ids,
                        holding.as_of_date.isoformat(),
                        DataStatus.NOT_MODELLED.value,
                        holding.fx_hedged,
                        False,
                        True,
                    )
                )
                continue

            fund_coverage[holding.id] = total_weight
            if not fund_items:
                warnings.append(
                    f"FUND_CONSTITUENTS_MISSING: fund {holding.id} has no constituent data."
                )
                positions.append(
                    _position(
                        holding,
                        holding.id,
                        holding.name,
                        valuation.base_value,
                        holding.sector,
                        holding.country,
                        None,
                        holding.underlying_asset_id,
                        valuation.source_ids,
                        holding.as_of_date.isoformat(),
                        DataStatus.NOT_MODELLED.value,
                        holding.fx_hedged,
                        False,
                        True,
                    )
                )
                continue

            for constituent in fund_items:
                positions.append(
                    ExposurePosition(
                        id=f"{holding.id}:{constituent.underlying_asset_id}",
                        name=constituent.underlying_name,
                        value=valuation.base_value * constituent.weight,
                        asset_class="stock",
                        sector=constituent.sector,
                        country=constituent.country,
                        currency=constituent.currency.value,
                        underlying_asset_id=constituent.underlying_asset_id,
                        holding_ids=(holding.id,),
                        source_ids=tuple(
                            dict.fromkeys((*valuation.source_ids, constituent.source_id))
                        ),
                        as_of_date=min(holding.as_of_date, constituent.as_of_date).isoformat(),
                        data_status=constituent.data_status.value,
                        fx_hedged=holding.fx_hedged,
                        is_fund_derived=True,
                    )
                )
            residual_weight = Decimal("1") - total_weight
            if residual_weight > WEIGHT_TOLERANCE:
                residual_value = valuation.base_value * residual_weight
                positions.append(
                    _position(
                        holding,
                        f"{holding.id}:uncovered",
                        f"{holding.name} (uncovered)",
                        residual_value,
                        None,
                        holding.country,
                        None,
                        None,
                        valuation.source_ids,
                        holding.as_of_date.isoformat(),
                        DataStatus.NOT_MODELLED.value,
                        holding.fx_hedged,
                        False,
                        True,
                    )
                )
                warnings.append(
                    f"PARTIAL_LOOKTHROUGH: fund {holding.id} has "
                    f"{float(total_weight * 100):.2f}% constituent coverage; "
                    f"{float(residual_weight * 100):.2f}% remains uncovered."
                )
            elif total_weight < Decimal("1"):
                warnings.append(
                    f"PARTIAL_LOOKTHROUGH_TOLERANCE: fund {holding.id} weights are within "
                    "the 1% tolerance but do not sum exactly to 100%."
                )
            continue

        positions.append(
            ExposurePosition(
                id=holding.id,
                name=holding.name,
                value=valuation.base_value,
                asset_class=holding.asset_class.value,
                sector=holding.sector,
                country=holding.country,
                currency=holding.currency.value,
                underlying_asset_id=holding.underlying_asset_id or holding.id,
                holding_ids=(holding.id,),
                source_ids=valuation.source_ids,
                as_of_date=holding.as_of_date.isoformat(),
                data_status=holding.data_status.value,
                fx_hedged=holding.fx_hedged,
                is_fund_derived=False,
            )
        )

    return positions, warnings, fund_coverage


def _position(
    holding: Holding,
    position_id: str,
    name: str,
    value: Decimal,
    sector: str | None,
    country: str | None,
    currency: str | None,
    underlying_asset_id: str | None,
    source_ids: tuple[str, ...],
    as_of_date: str,
    data_status: str,
    fx_hedged: bool | None,
    is_fund_derived: bool,
    is_residual: bool,
) -> ExposurePosition:
    return ExposurePosition(
        id=position_id,
        name=name,
        value=value,
        asset_class=holding.asset_class.value,
        sector=sector,
        country=country,
        currency=currency,
        underlying_asset_id=underlying_asset_id,
        holding_ids=(holding.id,),
        source_ids=source_ids,
        as_of_date=as_of_date,
        data_status=data_status,
        fx_hedged=fx_hedged,
        is_fund_derived=is_fund_derived,
        is_residual=is_residual,
    )


def _group_by(
    positions: list[ExposurePosition],
    field_name: str,
    total: Decimal,
) -> list[dict[str, Any]]:
    values: dict[str, list[ExposurePosition]] = defaultdict(list)
    for position in positions:
        value = getattr(position, field_name)
        values[value if value else "Unknown"].append(position)
    groups = []
    for key in sorted(values, key=str.casefold):
        members = values[key]
        amount = sum((item.value for item in members), ZERO)
        groups.append(
            {
                "key": key,
                "value": float(amount),
                "percent": float(amount / total) if total else 0.0,
                "contributions": [
                    {
                        "id": item.id,
                        "name": item.name,
                        "value": float(item.value),
                        "holding_ids": list(item.holding_ids),
                        "is_fund_derived": item.is_fund_derived,
                        "data_status": item.data_status,
                        "source_ids": list(item.source_ids),
                        "as_of_date": item.as_of_date,
                    }
                    for item in members
                ],
                "source_ids": sorted({source for item in members for source in item.source_ids}),
                "as_of_dates": sorted({item.as_of_date for item in members}),
                "data_statuses": sorted({item.data_status for item in members}),
            }
        )
    return groups


def _overlaps(positions: list[ExposurePosition]) -> list[dict[str, Any]]:
    contributions: dict[str, list[ExposurePosition]] = defaultdict(list)
    names: dict[str, str] = {}
    for item in positions:
        if item.underlying_asset_id and not item.is_residual:
            contributions[item.underlying_asset_id].append(item)
            names[item.underlying_asset_id] = item.name
    overlaps = []
    for asset_id, items in sorted(contributions.items()):
        direct = [item for item in items if not item.is_fund_derived]
        funds = [item for item in items if item.is_fund_derived]
        distinct_funds = {holding_id for item in funds for holding_id in item.holding_ids}
        distinct_direct = {holding_id for item in direct for holding_id in item.holding_ids}
        if len(distinct_funds) + len(distinct_direct) < 2:
            continue
        overlaps.append(
            {
                "underlying_asset_id": asset_id,
                "name": names[asset_id],
                "total_exposure": float(sum((item.value for item in items), ZERO)),
                "direct_exposure": float(sum((item.value for item in direct), ZERO)),
                "fund_derived_exposure": float(sum((item.value for item in funds), ZERO)),
                "fund_count": len(distinct_funds),
                "direct_holding_count": len(distinct_direct),
                "holding_ids": sorted(
                    {holding_id for item in items for holding_id in item.holding_ids}
                ),
                "source_ids": sorted({source for item in items for source in item.source_ids}),
            }
        )
    return overlaps


def analyze_exposure(
    portfolio: Portfolio,
    base_currency: str,
    rates: list[FxRate],
    constituents: list[FundConstituent],
) -> dict[str, Any]:
    positions, warnings, fund_coverage = build_exposure_positions(
        portfolio, base_currency, rates, constituents
    )
    valuation = value_portfolio(portfolio, base_currency, rates)
    missing = set(valuation.unconverted_holding_ids)
    warnings.extend(
        stale_data_warnings(
            [holding.as_of_date for holding in portfolio.holdings]
            + [item.as_of_date for item in constituents]
            + [
                rate.as_of_date
                for rate in rates
                if any(rate.source_id in item.source_ids for item in positions)
            ]
        )
    )
    groups = {
        "asset_class": _group_by(positions, "asset_class", valuation.total_value),
        "sector": _group_by(positions, "sector", valuation.total_value),
        "company": _group_by(positions, "name", valuation.total_value),
        "geography": _group_by(positions, "country", valuation.total_value),
        "currency": _group_by(positions, "currency", valuation.total_value),
    }
    covered_value = sum(
        (item.value for item in positions if item.data_status != DataStatus.NOT_MODELLED.value),
        ZERO,
    )
    return {
        "portfolio_id": portfolio.id,
        "base_currency": base_currency,
        "total_portfolio_value": float(valuation.total_value),
        "value_complete": valuation.value_complete,
        "coverage_percent": float(covered_value / valuation.total_value)
        if valuation.total_value
        else 0.0,
        "groups": groups,
        "positions": [
            {
                "id": item.id,
                "name": item.name,
                "value": float(item.value),
                "asset_class": item.asset_class,
                "sector": item.sector,
                "country": item.country,
                "currency": item.currency,
                "underlying_asset_id": item.underlying_asset_id,
                "holding_ids": list(item.holding_ids),
                "source_ids": list(item.source_ids),
                "as_of_date": item.as_of_date,
                "data_status": item.data_status,
                "is_fund_derived": item.is_fund_derived,
            }
            for item in positions
        ],
        "fund_coverage": [
            {
                "holding_id": fund_id,
                "coverage_percent": float(weight),
                "covered_value": float(
                    sum(
                        (
                            item.value
                            for item in positions
                            if item.is_fund_derived and fund_id in item.holding_ids
                        ),
                        ZERO,
                    )
                ),
                "uncovered_percent": float(max(ZERO, Decimal("1") - weight)),
            }
            for fund_id, weight in sorted(fund_coverage.items())
        ],
        "overlaps": _overlaps(positions),
        "unmapped_holding_ids": sorted(
            {
                holding_id
                for position in positions
                if position.data_status == DataStatus.NOT_MODELLED.value or position.sector is None
                for holding_id in position.holding_ids
            }
            | missing
        ),
        "unconverted_holding_ids": sorted(missing),
        "source_ids": sorted({source for item in positions for source in item.source_ids}),
        "as_of_dates": sorted({item.as_of_date for item in positions}),
        "data_statuses": sorted({item.data_status for item in positions}),
        "warnings": warnings,
    }
