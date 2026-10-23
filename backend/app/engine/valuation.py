from collections import deque
from dataclasses import dataclass
from decimal import Decimal

from app.domain.models import FxRate, Holding, Portfolio

ZERO = Decimal("0")
ONE = Decimal("1")


@dataclass(frozen=True)
class Conversion:
    value: Decimal | None
    rate: Decimal | None
    source_ids: tuple[str, ...]
    path: tuple[str, ...]


def convert_amount(
    amount: Decimal,
    from_currency: str,
    to_currency: str,
    rates: list[FxRate],
) -> Conversion:
    if from_currency == to_currency:
        return Conversion(amount, ONE, (), (from_currency,))

    graph: dict[str, list[tuple[str, Decimal, str]]] = {}
    for record in rates:
        source = record.foreign_currency.value
        target = record.base_currency.value
        graph.setdefault(source, []).append((target, record.rate, record.source_id))
        graph.setdefault(target, []).append((source, ONE / record.rate, record.source_id))

    queue = deque([(from_currency, ONE, (), (from_currency,))])
    visited = {from_currency}
    while queue:
        currency, accumulated_rate, source_ids, path = queue.popleft()
        for next_currency, edge_rate, source_id in sorted(graph.get(currency, [])):
            if next_currency in visited:
                continue
            next_rate = accumulated_rate * edge_rate
            next_sources = tuple(dict.fromkeys((*source_ids, source_id)))
            next_path = (*path, next_currency)
            if next_currency == to_currency:
                return Conversion(amount * next_rate, next_rate, next_sources, next_path)
            visited.add(next_currency)
            queue.append((next_currency, next_rate, next_sources, next_path))
    return Conversion(None, None, (), ())


@dataclass(frozen=True)
class HoldingValuation:
    holding_id: str
    original_value: Decimal
    original_currency: str
    base_value: Decimal | None
    fx_rate: Decimal | None
    source_ids: tuple[str, ...]
    fx_path: tuple[str, ...]


@dataclass(frozen=True)
class PortfolioValuation:
    base_currency: str
    total_value: Decimal
    value_complete: bool
    holdings: tuple[HoldingValuation, ...]
    unconverted_holding_ids: tuple[str, ...]


def value_holding(holding: Holding, base_currency: str, rates: list[FxRate]) -> HoldingValuation:
    conversion = convert_amount(holding.market_value, holding.currency.value, base_currency, rates)
    return HoldingValuation(
        holding_id=holding.id,
        original_value=holding.market_value,
        original_currency=holding.currency.value,
        base_value=conversion.value,
        fx_rate=conversion.rate,
        source_ids=tuple(dict.fromkeys((holding.source_id, *conversion.source_ids))),
        fx_path=conversion.path,
    )


def value_portfolio(
    portfolio: Portfolio, base_currency: str, rates: list[FxRate]
) -> PortfolioValuation:
    values = tuple(value_holding(holding, base_currency, rates) for holding in portfolio.holdings)
    unconverted = tuple(item.holding_id for item in values if item.base_value is None)
    total = sum((item.base_value for item in values if item.base_value is not None), ZERO)
    return PortfolioValuation(
        base_currency=base_currency,
        total_value=total,
        value_complete=not unconverted,
        holdings=values,
        unconverted_holding_ids=unconverted,
    )
