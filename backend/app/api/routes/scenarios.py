from fastapi import APIRouter, Request

from app.api.schemas import ExplanationResponse, ScenarioDefinitionResponse, ScenarioResponse
from app.domain.errors import ApiError
from app.domain.models import ExplanationRequest, Portfolio, ScenarioRequest
from app.engine.insights import generate_insights
from app.engine.scenarios import run_scenario
from app.services.explanation_service import explain_result
from app.services.source_service import sources_for_ids

router = APIRouter(tags=["Scenarios and explanations"])


@router.get(
    "/scenarios", response_model=list[ScenarioDefinitionResponse], summary="List scenario presets"
)
def list_scenarios(request: Request) -> list[dict]:
    return [
        {**scenario, "data_status": "illustrative"}
        for scenario in request.app.state.scenario_catalog
    ]


@router.post(
    "/portfolios/{portfolio_id}/scenarios/run",
    response_model=ScenarioResponse,
    summary="Run a deterministic stress simulation",
)
def run_portfolio_scenario(portfolio_id: str, payload: ScenarioRequest, request: Request) -> dict:
    portfolio = _get_portfolio(request, portfolio_id)
    result = run_scenario(
        portfolio,
        payload,
        request.app.state.fx_rates,
        request.app.state.fund_constituents,
        request.app.state.scenario_catalog,
    )
    request.app.state.scenario_results[result["result_id"]] = result
    while len(request.app.state.scenario_results) > 100:
        oldest_result_id = next(iter(request.app.state.scenario_results))
        del request.app.state.scenario_results[oldest_result_id]
    result["sources"] = sources_for_ids(
        request.app.state.sources,
        portfolio.holdings,
        set(result["source_ids"]),
    )
    return result


@router.post(
    "/portfolios/{portfolio_id}/explanations",
    response_model=ExplanationResponse,
    summary="Explain a server-calculated result",
)
def explain_portfolio_result(
    portfolio_id: str,
    payload: ExplanationRequest,
    request: Request,
) -> dict:
    portfolio = _get_portfolio(request, portfolio_id)
    result = request.app.state.scenario_results.get(payload.result_id)
    if result is None:
        for insight in generate_insights(
            portfolio,
            portfolio.base_currency.value,
            request.app.state.fx_rates,
            request.app.state.fund_constituents,
        ):
            if insight["id"] == payload.result_id:
                result = insight
                break
    if result is None:
        raise ApiError(
            404,
            "RESULT_NOT_FOUND",
            "The requested calculation result is unavailable; run the scenario "
            "or refresh insights first.",
        )
    if result.get("portfolio_id", portfolio_id) != portfolio_id:
        raise ApiError(404, "RESULT_NOT_FOUND", "The requested calculation result was not found.")
    return explain_result(result, payload.question)


def _get_portfolio(request: Request, portfolio_id: str) -> Portfolio:
    portfolio = request.app.state.portfolio_repository.get_portfolio(portfolio_id)
    if portfolio is None:
        raise ApiError(404, "PORTFOLIO_NOT_FOUND", "The requested portfolio was not found.")
    return portfolio
