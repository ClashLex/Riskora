from datetime import date
from typing import Any

from app.domain.models import FundConstituent, FxRate, Portfolio
from app.engine.exposure import analyze_exposure
from app.engine.valuation import value_portfolio


def generate_insights(
    portfolio: Portfolio,
    base_currency: str,
    rates: list[FxRate],
    constituents: list[FundConstituent],
) -> list[dict[str, Any]]:
    exposure = analyze_exposure(portfolio, base_currency, rates, constituents)
    valuation = value_portfolio(portfolio, base_currency, rates)
    as_of_date = max(exposure["as_of_dates"], default=date.fromisoformat("2026-06-30").isoformat())
    source_ids = exposure["source_ids"]
    insights: list[dict[str, Any]] = []

    for sector in exposure["groups"]["sector"]:
        if sector["key"] == "Unknown" or sector["percent"] < 0.30:
            continue
        severity = "high" if sector["percent"] >= 0.50 else "medium"
        insights.append(
            {
                "id": f"{portfolio.id}:insight-sector-{_slug(sector['key'])}",
                "type": "concentration",
                "title": f"{sector['key']} concentration",
                "severity": severity,
                "explanation": (
                    f"{sector['key']} represents {sector['percent']:.1%} of converted "
                    "portfolio value. "
                    "Prototype heuristic: medium at 30%; high at 50%."
                ),
                "calculation_details": {
                    "sector": sector["key"],
                    "exposure_base_value": sector["value"],
                    "portfolio_value": float(valuation.total_value),
                    "exposure_percent": sector["percent"],
                    "thresholds": {"medium": 0.30, "high": 0.50},
                    "threshold_note": "Prototype heuristic, not a universal financial standard.",
                },
                "related_holding_ids": sorted(
                    {
                        holding_id
                        for contribution in sector["contributions"]
                        for holding_id in contribution["holding_ids"]
                    }
                ),
                "source_ids": sector["source_ids"],
                "data_status": _combined_status(sector["data_statuses"]),
                "as_of_date": as_of_date,
                "limitations": [
                    "Constituent coverage and missing conversions can reduce analysis completeness."
                ],
            }
        )

    for overlap in exposure["overlaps"]:
        insights.append(
            {
                "id": f"{portfolio.id}:insight-overlap-{_slug(overlap['underlying_asset_id'])}",
                "type": "overlap",
                "title": f"Repeated exposure to {overlap['name']}",
                "severity": "medium",
                "explanation": (
                    f"{overlap['name']} appears through {overlap['fund_count']} fund(s) and "
                    f"{overlap['direct_holding_count']} direct holding(s), totaling "
                    f"{overlap['total_exposure']:.2f} {base_currency} of look-through exposure."
                ),
                "calculation_details": {
                    **overlap,
                    "threshold_note": (
                        "Overlap is a structural observation; medium is a prototype review flag."
                    ),
                },
                "related_holding_ids": overlap["holding_ids"],
                "source_ids": overlap["source_ids"],
                "data_status": "illustrative" if portfolio.is_demo else "user_entered",
                "as_of_date": as_of_date,
                "limitations": ["Fund constituent data may be incomplete or illustrative."],
            }
        )

    foreign = [
        group
        for group in exposure["groups"]["currency"]
        if group["key"] not in ("Unknown", base_currency)
    ]
    foreign_value = sum(group["value"] for group in foreign)
    foreign_percent = foreign_value / float(valuation.total_value) if valuation.total_value else 0.0
    if foreign_percent >= 0.40:
        insights.append(
            {
                "id": f"{portfolio.id}:insight-currency-{base_currency.lower()}",
                "type": "currency_exposure",
                "title": "Material foreign-currency exposure",
                "severity": "high" if foreign_percent >= 0.60 else "medium",
                "explanation": (
                    f"Known non-{base_currency} exposure is {foreign_percent:.1%} "
                    "of converted portfolio value. "
                    "Prototype heuristic: medium at 40%; high at 60%."
                ),
                "calculation_details": {
                    "foreign_exposure_base_value": foreign_value,
                    "portfolio_value": float(valuation.total_value),
                    "exposure_percent": foreign_percent,
                    "thresholds": {"medium": 0.40, "high": 0.60},
                    "threshold_note": "Prototype heuristic, not a universal financial standard.",
                },
                "related_holding_ids": sorted(
                    {
                        holding_id
                        for group in foreign
                        for contribution in group["contributions"]
                        for holding_id in contribution["holding_ids"]
                    }
                ),
                "source_ids": sorted(
                    {source for group in foreign for source in group["source_ids"]}
                ),
                "data_status": "illustrative" if portfolio.is_demo else "user_entered",
                "as_of_date": as_of_date,
                "limitations": ["Known currency groups omit holdings with missing FX conversion."],
            }
        )

    data_quality_ids = sorted(
        {
            holding_id
            for position in exposure["positions"]
            if position["data_status"] in ("illustrative", "not_modelled")
            for holding_id in position["holding_ids"]
        }
        | set(exposure["unconverted_holding_ids"])
    )
    if data_quality_ids:
        insights.append(
            {
                "id": f"{portfolio.id}:insight-data-quality",
                "type": "data_quality",
                "title": "Illustrative or incomplete data",
                "severity": "medium",
                "explanation": (
                    f"{len(data_quality_ids)} holding(s) use illustrative, unmapped, "
                    "or unconverted data. "
                    "Fixture data is not live or verified."
                ),
                "calculation_details": {
                    "affected_holding_count": len(data_quality_ids),
                    "holding_ids": data_quality_ids,
                    "threshold_note": (
                        "Any incomplete or illustrative input triggers this "
                        "transparent quality flag."
                    ),
                },
                "related_holding_ids": data_quality_ids,
                "source_ids": source_ids,
                "data_status": "illustrative" if portfolio.is_demo else "user_entered",
                "as_of_date": as_of_date,
                "limitations": [
                    "This rule reports provenance status, not accuracy or data-provider quality."
                ],
            }
        )
    return insights


def _combined_status(statuses: list[str]) -> str:
    return (
        "illustrative"
        if "illustrative" in statuses
        else (statuses[0] if statuses else "not_modelled")
    )


def _slug(value: str) -> str:
    result = "".join(character.lower() if character.isalnum() else "-" for character in value)
    return "-".join(part for part in result.split("-") if part)
