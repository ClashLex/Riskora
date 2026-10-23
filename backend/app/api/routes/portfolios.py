from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Request, Response, status

from app.api.schemas import (
    ExposureResponse,
    InsightResponse,
    PortfolioResponse,
    PortfolioSummaryResponse,
)
from app.domain.errors import ApiError
from app.domain.models import (
    Currency,
    DataStatus,
    Holding,
    HoldingCreate,
    HoldingPatch,
    Portfolio,
    PortfolioCreate,
)
from app.engine.exposure import analyze_exposure
from app.engine.insights import generate_insights
from app.repositories.fixture_repository import new_portfolio_id
from app.services.portfolio_service import portfolio_response, portfolio_summary
from app.services.source_service import sources_for_ids

router = APIRouter(prefix="/portfolios", tags=["Portfolios"])


@router.get("", response_model=list[PortfolioSummaryResponse], summary="List local portfolios")
def list_portfolios(request: Request) -> list[dict]:
    rates = request.app.state.fx_rates
    return [
        portfolio_summary(portfolio, rates)
        for portfolio in request.app.state.portfolio_repository.list_portfolios()
    ]


@router.post(
    "",
    response_model=PortfolioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create portfolio",
)
def create_portfolio(payload: PortfolioCreate, request: Request) -> dict:
    portfolio = Portfolio(
        id=new_portfolio_id(),
        name=payload.name,
        base_currency=payload.base_currency,
        holdings=[],
        data_status=DataStatus.USER_ENTERED,
        created_at=datetime.now(UTC),
        is_demo=False,
    )
    created = request.app.state.portfolio_repository.create_portfolio(portfolio)
    return portfolio_response(created, request.app.state.fx_rates)


@router.get(
    "/{portfolio_id}", response_model=PortfolioResponse, summary="Get portfolio and holdings"
)
def get_portfolio(portfolio_id: str, request: Request) -> dict:
    portfolio = _get_portfolio(request, portfolio_id)
    return portfolio_response(portfolio, request.app.state.fx_rates)


@router.post(
    "/{portfolio_id}/holdings",
    response_model=PortfolioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a holding",
)
def add_holding(portfolio_id: str, payload: HoldingCreate, request: Request) -> dict:
    _get_portfolio(request, portfolio_id)
    holding = Holding(
        id=f"holding-{uuid4().hex[:16]}",
        **payload.model_dump(),
        data_status=DataStatus.USER_ENTERED,
        is_demo=False,
    )
    portfolio = request.app.state.portfolio_repository.add_holding(portfolio_id, holding)
    return portfolio_response(portfolio, request.app.state.fx_rates)


@router.patch(
    "/{portfolio_id}/holdings/{holding_id}",
    response_model=PortfolioResponse,
    summary="Update a holding",
)
def update_holding(
    portfolio_id: str, holding_id: str, payload: HoldingPatch, request: Request
) -> dict:
    values = payload.model_dump(exclude_unset=True, mode="python")
    if not values:
        raise ApiError(400, "EMPTY_UPDATE", "Provide at least one field to update.")
    portfolio = request.app.state.portfolio_repository.update_holding(
        portfolio_id, holding_id, values
    )
    return portfolio_response(portfolio, request.app.state.fx_rates)


@router.delete(
    "/{portfolio_id}/holdings/{holding_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a holding",
)
def delete_holding(portfolio_id: str, holding_id: str, request: Request) -> Response:
    request.app.state.portfolio_repository.delete_holding(portfolio_id, holding_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{portfolio_id}/load-demo",
    response_model=PortfolioResponse,
    summary="Reset the illustrative demo portfolio",
)
def load_demo(portfolio_id: str, request: Request) -> dict:
    portfolio = request.app.state.portfolio_repository.reset_demo(portfolio_id)
    return portfolio_response(portfolio, request.app.state.fx_rates)


@router.get(
    "/{portfolio_id}/exposure",
    response_model=ExposureResponse,
    summary="Analyze portfolio exposure and look-through",
)
def get_exposure(
    portfolio_id: str,
    request: Request,
    base_currency: Currency | None = None,
) -> dict:
    portfolio = _get_portfolio(request, portfolio_id)
    target_currency = (base_currency or portfolio.base_currency).value
    result = analyze_exposure(
        portfolio,
        target_currency,
        request.app.state.fx_rates,
        request.app.state.fund_constituents,
    )
    result["sources"] = sources_for_ids(
        request.app.state.sources,
        portfolio.holdings,
        set(result["source_ids"]),
    )
    return result


@router.get(
    "/{portfolio_id}/insights",
    response_model=list[InsightResponse],
    summary="Get deterministic portfolio insights",
)
def get_insights(
    portfolio_id: str,
    request: Request,
    base_currency: Currency | None = None,
) -> list[dict]:
    portfolio = _get_portfolio(request, portfolio_id)
    target_currency = (base_currency or portfolio.base_currency).value
    return generate_insights(
        portfolio,
        target_currency,
        request.app.state.fx_rates,
        request.app.state.fund_constituents,
    )


def _get_portfolio(request: Request, portfolio_id: str) -> Portfolio:
    portfolio = request.app.state.portfolio_repository.get_portfolio(portfolio_id)
    if portfolio is None:
        raise ApiError(404, "PORTFOLIO_NOT_FOUND", "The requested portfolio was not found.")
    return portfolio
