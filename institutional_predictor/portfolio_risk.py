from __future__ import annotations

from collections import defaultdict
from typing import Literal
from urllib.parse import urlsplit

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

AssetType = Literal["equity", "mf", "us_stock", "etf", "debt"]
Currency = Literal["INR", "USD"]
AssetClass = Literal["Equity", "Debt", "Other"]


def validate_source_url(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Source URLs must use http or https.")
    return value


class FundConstituent(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, populate_by_name=True)

    symbol: str = Field(min_length=1, max_length=80)
    weight: float = Field(gt=0, le=1)
    sector: str = Field(default="Others", min_length=1, max_length=80)
    currency: Currency = "INR"
    asset_class: AssetClass = Field(
        default="Equity",
        validation_alias=AliasChoices("asset_class", "assetClass"),
    )
    source_url: str | None = Field(
        default=None,
        max_length=2048,
        validation_alias=AliasChoices("source_url", "sourceUrl"),
    )

    @field_validator("symbol", "sector")
    @classmethod
    def clean_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value

    _validate_source_url = field_validator("source_url")(validate_source_url)


class PortfolioHolding(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, populate_by_name=True)

    type: AssetType
    symbol: str = Field(min_length=1, max_length=120)
    quantity: float = Field(gt=0, validation_alias=AliasChoices("quantity", "units"))
    price: float = Field(gt=0, validation_alias=AliasChoices("price", "nav"))
    currency: Currency | None = None
    sector: str = Field(default="Others", min_length=1, max_length=80)
    asset_class: AssetClass | None = Field(
        default=None,
        validation_alias=AliasChoices("asset_class", "assetClass"),
    )
    amc: str | None = Field(default=None, max_length=120)
    scheme_code: str | None = Field(
        default=None,
        max_length=40,
        validation_alias=AliasChoices("scheme_code", "schemeCode"),
    )
    constituents: list[FundConstituent] = Field(default_factory=list, max_length=100)
    source_url: str | None = Field(
        default=None,
        max_length=2048,
        validation_alias=AliasChoices("source_url", "sourceUrl"),
    )

    @model_validator(mode="before")
    @classmethod
    def derive_fund_symbol(cls, value: object) -> object:
        if isinstance(value, dict) and value.get("type") == "mf" and not value.get(
            "symbol"
        ):
            value = value.copy()
            value["symbol"] = value.get("schemeCode") or value.get("scheme_code") or value.get(
                "amc"
            )
        return value

    @field_validator("symbol", "sector")
    @classmethod
    def clean_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value

    _validate_source_url = field_validator("source_url")(validate_source_url)

    @model_validator(mode="after")
    def validate_fund_data(self) -> PortfolioHolding:
        if self.type == "mf":
            total_weight = sum(item.weight for item in self.constituents)
            if total_weight > 1.000001:
                raise ValueError("Mutual-fund constituent weights cannot exceed 100%.")
        elif self.constituents:
            raise ValueError("Constituents can only be supplied for mutual funds.")
        return self


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, populate_by_name=True)

    portfolio: list[PortfolioHolding] = Field(min_length=1, max_length=100)
    scenario: dict[str, float] = Field(
        default_factory=lambda: {
            "equityShockPercent": -10.0,
            "usdInrChange": 5.0,
        }
    )
    usd_inr_rate: float = Field(
        default=83.5,
        gt=0,
        le=10000,
        validation_alias=AliasChoices("usd_inr_rate", "usdInrRate"),
    )

    @field_validator("scenario")
    @classmethod
    def validate_scenario(cls, value: dict[str, float]) -> dict[str, float]:
        allowed = {"equityShockPercent", "usdInrChange"}
        if set(value) - allowed:
            raise ValueError("Scenario supports equityShockPercent and usdInrChange only.")
        if "equityShockPercent" in value and not -100 <= value["equityShockPercent"] <= 500:
            raise ValueError("equityShockPercent must be between -100 and 500.")
        if "usdInrChange" in value and not -99.99 <= value["usdInrChange"] <= 500:
            raise ValueError("usdInrChange must be between -99.99 and 500.")
        return value

    @model_validator(mode="after")
    def require_scenario_fields(self) -> AnalyzeRequest:
        required = {"equityShockPercent", "usdInrChange"}
        if not required.issubset(self.scenario):
            raise ValueError("Provide both equityShockPercent and usdInrChange.")
        return self


def analyze_portfolio(request: AnalyzeRequest) -> dict:
    fx_rate = request.usd_inr_rate
    total_value = 0.0
    sector_values: defaultdict[str, float] = defaultdict(float)
    currency_values: defaultdict[str, float] = defaultdict(float)
    asset_class_values: defaultdict[str, float] = defaultdict(float)
    issuer_values: defaultdict[str, float] = defaultdict(float)
    issuer_labels: dict[str, str] = {}
    equity_value = 0.0
    usd_equity_value = 0.0
    usd_total_value = 0.0
    fund_positions: defaultdict[str, list[dict]] = defaultdict(list)
    sources: dict[str, str] = {}

    def add_exposure(
        *,
        value_inr: float,
        symbol: str,
        sector: str,
        currency: Currency,
        asset_class: AssetClass,
    ) -> None:
        nonlocal total_value, equity_value, usd_equity_value, usd_total_value
        total_value += value_inr
        sector_values[sector] += value_inr
        currency_values[currency] += value_inr
        asset_class_values[asset_class] += value_inr
        normalized_symbol = symbol.casefold()
        issuer_values[normalized_symbol] += value_inr
        issuer_labels.setdefault(normalized_symbol, symbol)
        if asset_class == "Equity":
            equity_value += value_inr
            if currency == "USD":
                usd_equity_value += value_inr
        if currency == "USD":
            usd_total_value += value_inr

    for holding in request.portfolio:
        currency: Currency = holding.currency or (
            "USD" if holding.type == "us_stock" else "INR"
        )
        asset_class: AssetClass = holding.asset_class or (
            "Debt" if holding.type == "debt" else "Equity"
        )
        base_value = holding.quantity * holding.price
        if holding.type == "mf":
            fund_name = holding.symbol
            invested_weight = sum(item.weight for item in holding.constituents)
            for constituent in holding.constituents:
                constituent_value = base_value * constituent.weight
                constituent_currency = constituent.currency
                converted_value = constituent_value
                add_exposure(
                    value_inr=converted_value,
                    symbol=constituent.symbol,
                    sector=constituent.sector,
                    currency=constituent_currency,
                    asset_class=constituent.asset_class,
                )
                fund_positions[constituent.symbol.casefold()].append(
                    {
                        "symbol": constituent.symbol,
                        "scheme": fund_name,
                        "weight": converted_value,
                        "sourceUrl": constituent.source_url or holding.source_url,
                    }
                )
                if constituent.source_url:
                    sources[constituent.source_url] = f"{fund_name} constituent data"
            unclassified_value = base_value * (1 - invested_weight)
            if unclassified_value > 0:
                add_exposure(
                    value_inr=unclassified_value,
                    symbol=f"{fund_name} (unclassified)",
                    sector="Others",
                    currency="INR",
                    asset_class="Other",
                )
        else:
            converted_value = base_value * (fx_rate if currency == "USD" else 1)
            add_exposure(
                value_inr=converted_value,
                symbol=holding.symbol,
                sector=holding.sector,
                currency=currency,
                asset_class=asset_class,
            )
        if holding.source_url:
            sources[holding.source_url] = f"{holding.symbol} holding data"

    if total_value <= 0:
        raise ValueError("Portfolio total value must be greater than zero.")

    def shares(values: dict[str, float]) -> dict[str, float]:
        return {
            key: value / total_value
            for key, value in sorted(values.items(), key=lambda item: item[0].casefold())
            if value > 0
        }

    overlaps = []
    for _, positions in sorted(fund_positions.items()):
        distinct_schemes = {position["scheme"] for position in positions}
        if len(distinct_schemes) < 2:
            continue
        fund_weights: dict[str, float] = defaultdict(float)
        source_urls: set[str] = set()
        for position in positions:
            fund_weights[position["scheme"]] += position["weight"]
            if position["sourceUrl"]:
                source_urls.add(position["sourceUrl"])
        overlaps.append(
            {
                "symbol": positions[0]["symbol"],
                "funds": [
                    {
                        "scheme": scheme,
                        "weight": amount / total_value,
                    }
                    for scheme, amount in sorted(fund_weights.items())
                ],
                "totalOverlapPercent": sum(fund_weights.values()) / total_value * 100,
                "sources": sorted(source_urls),
            }
        )

    equity_shock = request.scenario["equityShockPercent"] / 100
    fx_shock = request.scenario["usdInrChange"] / 100
    market_pnl = equity_value * equity_shock
    # USD debt is not exposed to the equity shock, so exclude its value from the cross-term.
    usd_debt_value = max(0.0, usd_total_value - usd_equity_value)
    fx_pnl = (usd_equity_value * (1 + equity_shock) + usd_debt_value) * fx_shock
    new_value = total_value + market_pnl + fx_pnl

    hhi = sum((value / total_value) ** 2 for value in issuer_values.values())
    top_exposures = sorted(
        (
            {
                "symbol": issuer_labels[symbol_key],
                "valueInr": value,
                "weight": value / total_value,
            }
            for symbol_key, value in issuer_values.items()
        ),
        key=lambda item: item["weight"],
        reverse=True,
    )[:5]
    explanation_parts = [
        f"Your portfolio is valued at ₹{total_value:,.2f} using the quantities and prices you provided."
    ]
    biggest_sector = max(sector_values.items(), key=lambda item: item[1])
    explanation_parts.append(
        f"{biggest_sector[0]} is the largest sector bucket at "
        f"{biggest_sector[1] / total_value:.1%} of the portfolio."
    )
    if overlaps:
        largest_overlap = max(overlaps, key=lambda item: item["totalOverlapPercent"])
        explanation_parts.append(
            f"{largest_overlap['symbol']} appears in multiple supplied mutual-fund "
            f"constituent lists, representing {largest_overlap['totalOverlapPercent']:.2f}% "
            "of portfolio value across those funds."
        )
    explanation_parts.append(
        f"Under the selected scenario, the estimated equity-shock impact is "
        f"₹{market_pnl:,.2f} and the currency impact is ₹{fx_pnl:,.2f}; "
        f"the resulting illustrative value is ₹{new_value:,.2f}."
    )
    explanation_parts.append(
        "This is deterministic arithmetic on user-entered inputs, not a forecast or investment advice."
    )
    return {
        "totalValueInr": total_value,
        "allocations": {
            "sectors": shares(sector_values),
            "currencies": shares(currency_values),
            "assetClasses": shares(asset_class_values),
        },
        "overlaps": overlaps,
        "stressResults": {
            "marketShockPnl": market_pnl,
            "fxShockPnl": fx_pnl,
            "totalPnl": market_pnl + fx_pnl,
            "newPortfolioValue": new_value,
            "equityShockPercent": request.scenario["equityShockPercent"],
            "usdInrChange": request.scenario["usdInrChange"],
            "usdInrRate": fx_rate,
        },
        "riskMetrics": {
            "issuerConcentrationHhi": hhi,
            "topExposures": top_exposures,
            "equityValueInr": equity_value,
            "usdExposureInr": usd_total_value,
        },
        "explanation": " ".join(explanation_parts),
        "sources": [
            {"name": name, "url": url} for url, name in sorted(sources.items())
        ],
        "dataNotes": [
            "Prices, quantities, sectors, currencies, and fund constituents are user-supplied.",
            f"USD exposure is converted using the user-supplied rate of ₹{fx_rate:,.4f} per USD.",
            "Fund overlap is only calculated from constituent lists provided with this request.",
            "Uploaded or submitted portfolio data is processed for this request and is not persisted by this endpoint.",
        ],
        "disclaimer": "For educational analysis only. Not investment advice. Scenario results are illustrative, assume linear shocks, and are not predictions of actual returns.",
    }
