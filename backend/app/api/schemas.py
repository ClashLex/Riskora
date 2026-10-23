from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.domain.models import DataStatus, Holding


class ResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthResponse(ResponseModel):
    status: str
    service: str
    version: str
    data_mode: str


class HoldingValuationResponse(ResponseModel):
    holding_id: str
    original_value: float
    original_currency: str
    base_value: float | None
    fx_rate: float | None
    fx_path: list[str]
    source_ids: list[str]


class PortfolioResponse(ResponseModel):
    id: str
    name: str
    base_currency: str
    holdings: list[Holding]
    total_value: float
    value_complete: bool
    data_status: DataStatus
    as_of_dates: list[date]
    holding_valuations: list[HoldingValuationResponse]
    warnings: list[str]
    created_at: datetime
    is_demo: bool


class PortfolioSummaryResponse(ResponseModel):
    id: str
    name: str
    base_currency: str
    total_value: float
    value_complete: bool
    holding_count: int
    data_status: DataStatus
    is_demo: bool


class ExposureContribution(ResponseModel):
    id: str
    name: str
    value: float
    holding_ids: list[str]
    is_fund_derived: bool
    data_status: str
    source_ids: list[str]
    as_of_date: date


class ExposureGroup(ResponseModel):
    key: str
    value: float
    percent: float
    contributions: list[ExposureContribution]
    source_ids: list[str]
    as_of_dates: list[date]
    data_statuses: list[str]


class FundCoverage(ResponseModel):
    holding_id: str
    coverage_percent: float
    covered_value: float
    uncovered_percent: float


class Overlap(ResponseModel):
    underlying_asset_id: str
    name: str
    total_exposure: float
    direct_exposure: float
    fund_derived_exposure: float
    fund_count: int
    direct_holding_count: int
    holding_ids: list[str]
    source_ids: list[str]


class ExposurePositionResponse(ResponseModel):
    id: str
    name: str
    value: float
    asset_class: str
    sector: str | None
    country: str | None
    currency: str | None
    underlying_asset_id: str | None
    holding_ids: list[str]
    source_ids: list[str]
    as_of_date: date
    data_status: str
    is_fund_derived: bool


class SourceResponse(ResponseModel):
    id: str
    name: str
    source_url: str | None
    as_of_date: date
    retrieved_at: date | None
    data_status: DataStatus
    license_note: str | None
    fields_supported: list[str]


class ExposureResponse(ResponseModel):
    portfolio_id: str
    base_currency: str
    total_portfolio_value: float
    value_complete: bool
    coverage_percent: float
    groups: dict[str, list[ExposureGroup]]
    positions: list[ExposurePositionResponse]
    fund_coverage: list[FundCoverage]
    overlaps: list[Overlap]
    unmapped_holding_ids: list[str]
    unconverted_holding_ids: list[str]
    source_ids: list[str]
    sources: list[SourceResponse]
    as_of_dates: list[date]
    data_statuses: list[str]
    warnings: list[str]


class InsightResponse(ResponseModel):
    id: str
    type: str
    title: str
    severity: str
    explanation: str
    calculation_details: dict[str, Any]
    related_holding_ids: list[str]
    source_ids: list[str]
    data_status: str
    as_of_date: date
    limitations: list[str]


class ScenarioRow(ResponseModel):
    id: str
    name: str
    exposure_base_value: float
    asset_return: float | None
    fx_return: float | None
    estimated_change_base_value: float | None
    post_shock_base_value: float | None
    data_status: str
    is_modelled: bool
    holding_ids: list[str]
    source_ids: list[str]
    as_of_date: date
    explanation: str


class ScenarioResponse(ResponseModel):
    result_id: str
    portfolio_id: str
    scenario_id: str
    base_currency: str
    portfolio_value_before: float
    portfolio_value_after: float | None
    estimated_change: float | None
    modeled_estimated_change: float
    estimated_change_percent: float | None
    is_complete: bool
    is_simulation: bool
    data_status: str
    as_of_date: date
    assumptions: list[str]
    limitations: list[str]
    rows: list[ScenarioRow]
    source_ids: list[str]
    sources: list[SourceResponse]
    warnings: list[str]


class ScenarioDefinitionResponse(ResponseModel):
    id: str
    name: str
    description: str
    default_asset_shock_percent: float
    default_fx_shock_percent: float
    method: str
    limitations: list[str]
    data_status: str


class ExplanationResponse(ResponseModel):
    result_id: str
    explanation: str
    mode: str
    source_ids: list[str]
    data_status: str
    as_of_date: date
