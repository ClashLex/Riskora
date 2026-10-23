import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from app.domain.errors import ApiError
from app.domain.models import Holding, Portfolio
from app.repositories.portfolio_repository import PortfolioRepository

DATA_DIRECTORY = Path(__file__).resolve().parent.parent / "data"


def load_json(filename: str):
    with (DATA_DIRECTORY / filename).open(encoding="utf-8") as fixture:
        return json.load(fixture)


def load_fixture_data() -> tuple[Portfolio, list[dict], list[dict], list[dict], list[dict]]:
    portfolio = Portfolio.model_validate(load_json("demo_portfolio.json"))
    constituents = load_json("demo_fund_holdings.json")
    fx_rates = load_json("demo_fx_rates.json")
    scenarios = load_json("demo_scenarios.json")
    sources = load_json("demo_sources.json")
    return portfolio, constituents, fx_rates, scenarios, sources


class InMemoryPortfolioRepository(PortfolioRepository):
    def __init__(self, demo_portfolio: Portfolio) -> None:
        self._demo_portfolio = demo_portfolio
        self._portfolios: dict[str, Portfolio] = {demo_portfolio.id: demo_portfolio}

    def list_portfolios(self) -> list[Portfolio]:
        return [deepcopy(portfolio) for portfolio in self._portfolios.values()]

    def get_portfolio(self, portfolio_id: str) -> Portfolio | None:
        portfolio = self._portfolios.get(portfolio_id)
        return deepcopy(portfolio) if portfolio else None

    def create_portfolio(self, portfolio: Portfolio) -> Portfolio:
        if portfolio.id in self._portfolios:
            raise ApiError(
                409, "PORTFOLIO_EXISTS", "A portfolio with this identifier already exists."
            )
        self._portfolios[portfolio.id] = deepcopy(portfolio)
        return deepcopy(portfolio)

    def add_holding(self, portfolio_id: str, holding: Holding) -> Portfolio:
        portfolio = self._require_portfolio(portfolio_id)
        if len(portfolio.holdings) >= 500:
            raise ApiError(
                400, "HOLDING_LIMIT_REACHED", "A portfolio cannot contain more than 500 holdings."
            )
        if any(existing.id == holding.id for existing in portfolio.holdings):
            raise ApiError(409, "HOLDING_EXISTS", "A holding with this identifier already exists.")
        updated = portfolio.model_copy(update={"holdings": [*portfolio.holdings, holding]})
        updated = Portfolio.model_validate(updated.model_dump())
        self._portfolios[portfolio_id] = updated
        return deepcopy(updated)

    def update_holding(self, portfolio_id: str, holding_id: str, values: dict) -> Portfolio:
        portfolio = self._require_portfolio(portfolio_id)
        holdings = []
        found = False
        for holding in portfolio.holdings:
            if holding.id == holding_id:
                updated_holding = Holding.model_validate({**holding.model_dump(), **values})
                holdings.append(updated_holding)
                found = True
            else:
                holdings.append(holding)
        if not found:
            raise ApiError(404, "HOLDING_NOT_FOUND", "The requested holding was not found.")
        updated = Portfolio.model_validate({**portfolio.model_dump(), "holdings": holdings})
        self._portfolios[portfolio_id] = updated
        return deepcopy(updated)

    def delete_holding(self, portfolio_id: str, holding_id: str) -> None:
        portfolio = self._require_portfolio(portfolio_id)
        holdings = [holding for holding in portfolio.holdings if holding.id != holding_id]
        if len(holdings) == len(portfolio.holdings):
            raise ApiError(404, "HOLDING_NOT_FOUND", "The requested holding was not found.")
        self._portfolios[portfolio_id] = Portfolio.model_validate(
            {**portfolio.model_dump(), "holdings": holdings}
        )

    def reset_demo(self, portfolio_id: str) -> Portfolio:
        if portfolio_id != self._demo_portfolio.id:
            raise ApiError(404, "PORTFOLIO_NOT_FOUND", "The requested portfolio was not found.")
        self._portfolios[portfolio_id] = deepcopy(self._demo_portfolio)
        return deepcopy(self._demo_portfolio)

    def _require_portfolio(self, portfolio_id: str) -> Portfolio:
        portfolio = self._portfolios.get(portfolio_id)
        if portfolio is None:
            raise ApiError(404, "PORTFOLIO_NOT_FOUND", "The requested portfolio was not found.")
        return portfolio


def new_portfolio_id() -> str:
    return f"portfolio-{uuid4().hex[:16]}"
