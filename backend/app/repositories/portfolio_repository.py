from abc import ABC, abstractmethod

from app.domain.models import Holding, Portfolio


class PortfolioRepository(ABC):
    @abstractmethod
    def list_portfolios(self) -> list[Portfolio]:
        raise NotImplementedError

    @abstractmethod
    def get_portfolio(self, portfolio_id: str) -> Portfolio | None:
        raise NotImplementedError

    @abstractmethod
    def create_portfolio(self, portfolio: Portfolio) -> Portfolio:
        raise NotImplementedError

    @abstractmethod
    def add_holding(self, portfolio_id: str, holding: Holding) -> Portfolio:
        raise NotImplementedError

    @abstractmethod
    def update_holding(self, portfolio_id: str, holding_id: str, values: dict) -> Portfolio:
        raise NotImplementedError

    @abstractmethod
    def delete_holding(self, portfolio_id: str, holding_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def reset_demo(self, portfolio_id: str) -> Portfolio:
        raise NotImplementedError
