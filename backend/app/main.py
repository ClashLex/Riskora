import logging

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes.portfolios import router as portfolios_router
from app.api.routes.scenarios import router as scenarios_router
from app.api.schemas import HealthResponse
from app.config import Settings
from app.domain.errors import ApiError
from app.domain.models import FundConstituent, FxRate, Portfolio, SourceRecord
from app.repositories.fixture_repository import InMemoryPortfolioRepository, load_fixture_data

load_dotenv()
logger = logging.getLogger("risvanta.api")
SERVICE_VERSION = "0.1.0"


def create_app(
    settings: Settings | None = None,
    portfolio_repository: InMemoryPortfolioRepository | None = None,
) -> FastAPI:
    settings = settings or Settings.from_environment()
    demo_portfolio, raw_constituents, raw_rates, scenarios, raw_sources = load_fixture_data()
    constituents = [FundConstituent.model_validate(item) for item in raw_constituents]
    fx_rates = [FxRate.model_validate(item) for item in raw_rates]
    sources = [SourceRecord.model_validate(item) for item in raw_sources]
    _validate_fixtures(demo_portfolio, constituents, fx_rates, sources)
    repository = portfolio_repository or InMemoryPortfolioRepository(demo_portfolio)

    app = FastAPI(
        title="Risvanta Backend",
        version=SERVICE_VERSION,
        description=(
            "Deterministic portfolio exposure and hypothetical stress analysis. "
            "Demo data is illustrative; this service is not a trading or investment-advice system."
        ),
        openapi_tags=[
            {"name": "Health", "description": "Service liveness."},
            {
                "name": "Portfolios",
                "description": "In-memory local portfolios and exposure analysis.",
            },
            {
                "name": "Scenarios and explanations",
                "description": "Deterministic stress simulations and grounded templates.",
            },
        ],
    )
    app.state.settings = settings
    app.state.portfolio_repository = repository
    app.state.fund_constituents = constituents
    app.state.fx_rates = fx_rates
    app.state.scenario_catalog = scenarios
    app.state.sources = sources
    app.state.scenario_results = {}

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(ApiError)
    async def handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {
                "field": ".".join(str(part) for part in error["loc"] if part != "body"),
                "message": error["msg"],
                "type": error["type"],
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "The request contains invalid fields.",
                    "details": {"issues": details},
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
        message = (
            "The requested resource was not found."
            if exc.status_code == 404
            else "The request could not be completed."
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": code, "message": message, "details": {}}},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        logger.error("Unexpected API error (%s)", type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected internal error occurred.",
                    "details": {},
                }
            },
        )

    @app.get(
        "/health", response_model=HealthResponse, tags=["Health"], summary="Check service liveness"
    )
    def health() -> dict:
        return {
            "status": "ok",
            "service": "risvanta-backend",
            "version": SERVICE_VERSION,
            "data_mode": settings.data_mode,
        }

    app.include_router(portfolios_router, prefix=settings.api_prefix)
    app.include_router(scenarios_router, prefix=settings.api_prefix)
    return app


def _validate_fixtures(
    portfolio: Portfolio,
    constituents: list[FundConstituent],
    rates: list[FxRate],
    sources: list[SourceRecord],
) -> None:
    source_ids = {source.id for source in sources}
    holding_ids = {holding.id for holding in portfolio.holdings}
    if any(holding.source_id not in source_ids for holding in portfolio.holdings):
        raise ValueError("Demo portfolio references a source record that does not exist.")
    if any(item.source_id not in source_ids for item in constituents):
        raise ValueError("Fund constituent fixture references a source record that does not exist.")
    if any(item.fund_id not in holding_ids for item in constituents):
        raise ValueError("Fund constituent fixture references an unknown demo holding.")
    if any(item.rate <= 0 for item in rates):
        raise ValueError("FX fixture rates must be positive.")
    if any(source.data_status.value == "verified_source" for source in sources):
        raise ValueError("Demo fixtures cannot be marked as verified sources.")


app = create_app()
