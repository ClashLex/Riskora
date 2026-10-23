import re
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)


class Currency(StrEnum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    INR = "INR"
    JPY = "JPY"
    CAD = "CAD"
    AUD = "AUD"
    CHF = "CHF"


class AssetClass(StrEnum):
    STOCK = "stock"
    ETF = "etf"
    MUTUAL_FUND = "mutual_fund"
    BOND = "bond"
    CASH = "cash"
    OTHER = "other"


class DataStatus(StrEnum):
    ILLUSTRATIVE = "illustrative"
    USER_ENTERED = "user_entered"
    VERIFIED_SOURCE = "verified_source"
    DELAYED = "delayed"
    NOT_MODELLED = "not_modelled"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Holding(StrictModel):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
    name: str = Field(min_length=1, max_length=160)
    ticker: str | None = Field(default=None, max_length=20)
    underlying_asset_id: str | None = Field(default=None, max_length=80)
    asset_class: AssetClass
    quantity: Decimal | None = Field(default=None, gt=0)
    market_value: Decimal = Field(gt=0, max_digits=20, decimal_places=6)
    currency: Currency
    country: str | None = Field(default=None, min_length=2, max_length=80)
    sector: str | None = Field(default=None, min_length=1, max_length=80)
    source_label: str = Field(default="User supplied", min_length=1, max_length=160)
    source_id: str = "src-user-entry"
    source_url: str | None = Field(default=None, max_length=500)
    as_of_date: date
    data_status: DataStatus = DataStatus.USER_ENTERED
    is_demo: bool = False
    fx_hedged: bool | None = None

    @field_validator("market_value", "quantity")
    @classmethod
    def validate_finite_decimal(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and not value.is_finite():
            raise ValueError("Value must be finite.")
        return value

    @field_validator("name", "source_label")
    @classmethod
    def trim_nonempty_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be blank.")
        return value

    @field_serializer("market_value", "quantity", when_used="json")
    def serialize_decimal(self, value: Decimal | None) -> float | None:
        return float(value) if value is not None else None


class Portfolio(StrictModel):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
    name: str = Field(min_length=1, max_length=160)
    base_currency: Currency
    holdings: list[Holding] = Field(default_factory=list, max_length=500)
    data_status: DataStatus = DataStatus.ILLUSTRATIVE
    created_at: datetime
    is_demo: bool = False

    @field_validator("name")
    @classmethod
    def trim_portfolio_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Portfolio name cannot be blank.")
        return value

    @model_validator(mode="after")
    def unique_holding_ids(self) -> "Portfolio":
        ids = [holding.id for holding in self.holdings]
        if len(ids) != len(set(ids)):
            raise ValueError("Holding IDs must be unique within a portfolio.")
        return self


class PortfolioCreate(StrictModel):
    name: str = Field(min_length=1, max_length=160)
    base_currency: Currency

    @field_validator("name")
    @classmethod
    def trim_portfolio_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Portfolio name cannot be blank.")
        return value


class HoldingCreate(StrictModel):
    name: str = Field(min_length=1, max_length=160)
    asset_class: AssetClass
    market_value: Decimal = Field(gt=0, max_digits=20, decimal_places=6)
    currency: Currency
    as_of_date: date
    ticker: str | None = Field(default=None, max_length=20)
    underlying_asset_id: str | None = Field(default=None, max_length=80)
    quantity: Decimal | None = Field(default=None, gt=0)
    country: str | None = Field(default=None, min_length=2, max_length=80)
    sector: str | None = Field(default=None, min_length=1, max_length=80)
    source_label: str = "User supplied"
    source_url: str | None = Field(default=None, max_length=500)
    fx_hedged: bool | None = None

    @field_validator("market_value", "quantity")
    @classmethod
    def validate_finite_decimal(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and not value.is_finite():
            raise ValueError("Value must be finite.")
        return value

    @field_validator("name", "source_label")
    @classmethod
    def trim_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be blank.")
        return value


class HoldingPatch(StrictModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    ticker: str | None = Field(default=None, max_length=20)
    underlying_asset_id: str | None = Field(default=None, max_length=80)
    asset_class: AssetClass | None = None
    quantity: Decimal | None = Field(default=None, gt=0)
    market_value: Decimal | None = Field(default=None, gt=0, max_digits=20, decimal_places=6)
    currency: Currency | None = None
    country: str | None = Field(default=None, min_length=2, max_length=80)
    sector: str | None = Field(default=None, min_length=1, max_length=80)
    source_label: str | None = Field(default=None, min_length=1, max_length=160)
    source_url: str | None = Field(default=None, max_length=500)
    as_of_date: date | None = None
    fx_hedged: bool | None = None

    @field_validator("market_value", "quantity")
    @classmethod
    def validate_finite_decimal(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and not value.is_finite():
            raise ValueError("Value must be finite.")
        return value

    @field_validator("name", "source_label")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be blank.")
        return value


class ScenarioRequest(StrictModel):
    scenario_id: str = Field(min_length=1, max_length=80)
    base_currency: Currency | None = None
    asset_shock_percent: float | None = Field(default=None, ge=-100, le=100)
    fx_shock_percent: float | None = Field(default=None, ge=-100, le=100)
    affected_sector: str | None = Field(default=None, min_length=1, max_length=80)
    affected_asset_ids: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("asset_shock_percent", "fx_shock_percent")
    @classmethod
    def validate_finite_shocks(cls, value: float | None) -> float | None:
        if value is not None and (value != value or value in (float("inf"), float("-inf"))):
            raise ValueError("Scenario shocks must be finite.")
        return value


class ExplanationRequest(StrictModel):
    result_id: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=1, max_length=500)

    @field_validator("question")
    @classmethod
    def trim_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question cannot be blank.")
        return value


class FundConstituent(StrictModel):
    fund_id: str
    underlying_asset_id: str
    underlying_name: str
    weight: Decimal = Field(ge=0, le=1, max_digits=8, decimal_places=6)
    sector: str | None = None
    country: str | None = None
    currency: Currency
    as_of_date: date
    data_status: DataStatus = DataStatus.ILLUSTRATIVE
    source_id: str = "src-demo-constituents"

    @field_validator("weight")
    @classmethod
    def validate_weight(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("Weight must be finite.")
        return value


class FxRate(StrictModel):
    base_currency: Currency
    foreign_currency: Currency
    rate: Decimal = Field(gt=0, max_digits=20, decimal_places=10)
    as_of_date: date
    source_label: str
    source_id: str
    source_url: str | None = None
    data_status: DataStatus = DataStatus.ILLUSTRATIVE

    @field_validator("rate")
    @classmethod
    def validate_finite_rate(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("FX rate must be finite.")
        return value


class SourceRecord(StrictModel):
    id: str
    name: str
    source_url: str | None = None
    as_of_date: date
    retrieved_at: date | None = None
    data_status: DataStatus
    license_note: str | None = None
    fields_supported: list[str] = Field(default_factory=list)


def require_valid_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,79}", value):
        raise ValueError("Identifier has an invalid format.")
    return value


def model_to_dict(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="python")
