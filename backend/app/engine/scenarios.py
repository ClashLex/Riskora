import json
from datetime import date
from decimal import Decimal
from hashlib import sha256
from typing import Any

from app.domain.errors import ApiError
from app.domain.models import FundConstituent, FxRate, Portfolio, ScenarioRequest
from app.engine.exposure import ExposurePosition, build_exposure_positions
from app.engine.provenance import stale_data_warnings
from app.engine.valuation import ZERO, value_portfolio

EQUITY_CLASSES = {"stock", "etf", "mutual_fund"}


def run_scenario(
    portfolio: Portfolio,
    request: ScenarioRequest,
    rates: list[FxRate],
    constituents: list[FundConstituent],
    scenario_catalog: list[dict[str, Any]],
) -> dict[str, Any]:
    definition = next(
        (item for item in scenario_catalog if item["id"] == request.scenario_id), None
    )
    if definition is None:
        raise ApiError(404, "SCENARIO_NOT_FOUND", "The requested scenario was not found.")

    base_currency = (request.base_currency or portfolio.base_currency).value
    if request.scenario_id == "custom" and request.affected_asset_ids:
        known_ids = {
            identifier
            for position in build_exposure_positions(portfolio, base_currency, rates, constituents)[
                0
            ]
            for identifier in (
                position.id,
                position.underlying_asset_id,
                *position.holding_ids,
            )
            if identifier is not None
        }
        unknown_ids = sorted(set(request.affected_asset_ids) - known_ids)
        if unknown_ids:
            raise ApiError(
                400,
                "UNKNOWN_SCENARIO_ASSET",
                "One or more selected assets are not present in the portfolio exposure.",
                {"asset_ids": unknown_ids},
            )
    asset_shock = Decimal(
        str(
            request.asset_shock_percent
            if request.asset_shock_percent is not None
            else definition["default_asset_shock_percent"]
        )
    ) / Decimal("100")
    fx_shock = Decimal(
        str(
            request.fx_shock_percent
            if request.fx_shock_percent is not None
            else definition["default_fx_shock_percent"]
        )
    ) / Decimal("100")
    positions, warnings, _ = build_exposure_positions(portfolio, base_currency, rates, constituents)
    valuation = value_portfolio(portfolio, base_currency, rates)
    warning_details = list(warnings)
    if valuation.unconverted_holding_ids:
        warning_details.append(
            "FX_RATE_MISSING: portfolio value and scenario impact are incomplete for "
            + ", ".join(valuation.unconverted_holding_ids)
            + "."
        )
    warning_details.extend(
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

    rows: list[dict[str, Any]] = []
    modeled_change = ZERO
    has_unmodeled_impact = bool(valuation.unconverted_holding_ids)
    for position in positions:
        market_return, market_known, market_reason = _market_return(position, request, asset_shock)
        fx_return, fx_known, fx_reason = _fx_return(
            position, base_currency, fx_shock, request.scenario_id
        )
        reason = market_reason or fx_reason
        is_modeled = market_known and fx_known
        if not is_modeled:
            has_unmodeled_impact = True
            warning_details.append(
                f"NOT_MODELLED: {position.name}: {reason or 'incomplete exposure mapping.'}"
            )
            rows.append(
                {
                    "id": position.id,
                    "name": position.name,
                    "exposure_base_value": float(position.value),
                    "asset_return": float(market_return) if market_known else None,
                    "fx_return": float(fx_return) if fx_known else None,
                    "estimated_change_base_value": None,
                    "post_shock_base_value": None,
                    "data_status": "not_modelled",
                    "is_modelled": False,
                    "holding_ids": list(position.holding_ids),
                    "source_ids": list(position.source_ids),
                    "as_of_date": position.as_of_date,
                    "explanation": reason
                    or "The scenario impact could not be modelled from available mapping data.",
                }
            )
            continue

        combined_return = (Decimal("1") + market_return) * (Decimal("1") + fx_return) - Decimal("1")
        change = position.value * combined_return
        modeled_change += change
        rows.append(
            {
                "id": position.id,
                "name": position.name,
                "exposure_base_value": float(position.value),
                "asset_return": float(market_return),
                "fx_return": float(fx_return),
                "estimated_change_base_value": float(change),
                "post_shock_base_value": float(position.value + change),
                "data_status": (
                    "illustrative" if position.is_residual and is_modeled else position.data_status
                ),
                "is_modelled": True,
                "holding_ids": list(position.holding_ids),
                "source_ids": list(position.source_ids),
                "as_of_date": position.as_of_date,
                "explanation": _row_explanation(position, market_return, fx_return, definition),
            }
        )

    dates = [item.as_of_date for item in positions]
    as_of_date = max(dates) if dates else date.fromisoformat("2026-06-30").isoformat()
    is_complete = not has_unmodeled_impact
    stable_result = {
        "portfolio_id": portfolio.id,
        "scenario_id": request.scenario_id,
        "base_currency": base_currency,
        "asset_shock_percent": float(asset_shock * 100),
        "fx_shock_percent": float(fx_shock * 100),
        "rows": rows,
        "as_of_date": as_of_date,
    }
    result_id = (
        "result-"
        + sha256(
            json.dumps(stable_result, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:20]
    )
    if not is_complete:
        warning_details.append(
            "AGGREGATE_INCOMPLETE: the modeled row subtotal is available, but the total portfolio "
            "change is withheld because some exposure could not be modelled."
        )
    return {
        "result_id": result_id,
        "portfolio_id": portfolio.id,
        "scenario_id": request.scenario_id,
        "base_currency": base_currency,
        "portfolio_value_before": float(valuation.total_value),
        "portfolio_value_after": float(valuation.total_value + modeled_change)
        if is_complete
        else None,
        "estimated_change": float(modeled_change) if is_complete else None,
        "modeled_estimated_change": float(modeled_change),
        "estimated_change_percent": (
            float(modeled_change / valuation.total_value)
            if is_complete and valuation.total_value
            else None
        ),
        "is_complete": is_complete,
        "is_simulation": True,
        "data_status": "illustrative" if portfolio.is_demo else "user_entered",
        "as_of_date": as_of_date,
        "assumptions": _assumptions(definition, request, asset_shock, fx_shock),
        "limitations": list(definition["limitations"]),
        "rows": rows,
        "source_ids": sorted({source for row in rows for source in row["source_ids"]}),
        "warnings": list(dict.fromkeys(warning_details)),
    }


def _market_return(
    position: ExposurePosition,
    request: ScenarioRequest,
    asset_shock: Decimal,
) -> tuple[Decimal, bool, str]:
    scenario_id = request.scenario_id
    if asset_shock == ZERO:
        return ZERO, True, ""
    if scenario_id in ("broad_market_down", "combined_market_fx_shock"):
        if position.asset_class in EQUITY_CLASSES:
            return asset_shock, True, ""
        return ZERO, True, ""
    if scenario_id == "technology_sector_down":
        if position.sector is None:
            return (
                ZERO,
                False,
                "Sector mapping is missing; this exposure was not assigned a technology shock.",
            )
        return (
            (asset_shock, True, "")
            if position.sector.casefold() == "technology"
            else (ZERO, True, "")
        )
    if scenario_id == "custom":
        selected_ids = set(request.affected_asset_ids)
        selected_sector = request.affected_sector
        if (
            selected_ids
            and position.underlying_asset_id not in selected_ids
            and not selected_ids.intersection(position.holding_ids)
        ):
            return ZERO, True, ""
        if selected_sector and (position.sector or "").casefold() != selected_sector.casefold():
            return ZERO, True, ""
        if not selected_ids and not selected_sector:
            if position.sector is None:
                return (
                    ZERO,
                    False,
                    "Custom scenario has no target selector and sector mapping is missing.",
                )
            return asset_shock, True, ""
        return asset_shock, True, ""
    return ZERO, True, ""


def _fx_return(
    position: ExposurePosition,
    base_currency: str,
    fx_shock: Decimal,
    scenario_id: str,
) -> tuple[Decimal, bool, str]:
    if fx_shock == ZERO:
        return ZERO, True, ""
    if position.currency is None:
        return ZERO, False, "Currency mapping is missing; FX exposure was not assumed."
    if position.currency == base_currency or position.fx_hedged is True:
        return ZERO, True, ""
    if position.fx_hedged is None:
        return ZERO, False, "Hedge status is unknown; the position was not assumed unhedged."

    if scenario_id in ("usd_strengthens", "usd_weakens"):
        magnitude = abs(fx_shock)
        if base_currency == "USD":
            currency_return = -magnitude if scenario_id == "usd_strengthens" else magnitude
            return currency_return, True, ""
        if position.currency == "USD":
            currency_return = magnitude if scenario_id == "usd_strengthens" else -magnitude
            return currency_return, True, ""
        return (
            ZERO,
            False,
            "This USD-specific preset does not define a shock for the holding currency.",
        )
    return fx_shock, True, ""


def _row_explanation(
    position: ExposurePosition,
    asset_return: Decimal,
    fx_return: Decimal,
    definition: dict[str, Any],
) -> str:
    if position.is_residual:
        return (
            "Uncovered fund value receives the documented broad-market proxy only."
            if asset_return
            else "Uncovered exposure is unchanged under this scenario."
        )
    if asset_return and fx_return:
        return (
            "Market and currency returns are compounded using "
            "(1 + asset_return) * (1 + fx_return) - 1."
        )
    if asset_return:
        return f"Mapped exposure receives the {definition['name']} market shock."
    if fx_return:
        return f"Known unhedged {position.currency} exposure receives the FX shock."
    return "No shock applies to this mapped exposure under the selected scenario."


def _assumptions(
    definition: dict[str, Any],
    request: ScenarioRequest,
    asset_shock: Decimal,
    fx_shock: Decimal,
) -> list[str]:
    assumptions = [
        f"Hypothetical asset return: {asset_shock * 100}% and FX return: {fx_shock * 100}%.",
        "Asset and FX returns compound as (1 + asset_return) * (1 + fx_return) - 1.",
        "FX rate convention: units of base currency for one unit of foreign currency.",
        "Unknown hedge status is not assumed unhedged; fund constituents are decomposed, "
        "not added to portfolio value.",
        "USD-specific presets use the preset direction and the absolute FX shock as its magnitude.",
        "Results use illustrative or user-entered data and are not a forecast or "
        "investment advice.",
        *definition["limitations"],
    ]
    if request.affected_sector:
        assumptions.append(
            f"Only exposure mapped to sector '{request.affected_sector}' is targeted."
        )
    if request.affected_asset_ids:
        assumptions.append(
            "Asset filters match holding IDs or underlying asset IDs supplied by the caller."
        )
    return assumptions
