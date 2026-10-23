from datetime import date
from decimal import Decimal

from app.domain.models import Currency, FxRate
from app.engine.valuation import convert_amount, value_holding
from tests.helpers import holding


def fx_rate(base: str, foreign: str, rate: str) -> FxRate:
    return FxRate(
        base_currency=Currency(base),
        foreign_currency=Currency(foreign),
        rate=Decimal(rate),
        as_of_date=date(2026, 6, 30),
        source_label="Test fixture",
        source_id="src-test-fx",
    )


def test_base_currency_holding_needs_no_conversion() -> None:
    value = value_holding(holding("usd-stock", "250"), "USD", [])
    assert value.base_value == Decimal("250")
    assert value.fx_rate == Decimal("1")


def test_foreign_currency_conversion_obeys_base_per_foreign_convention() -> None:
    value = convert_amount(Decimal("100"), "EUR", "USD", [fx_rate("USD", "EUR", "1.08")])
    assert value.value == Decimal("108.00")
    assert value.path == ("EUR", "USD")


def test_missing_rate_is_explicit_not_an_implicit_one() -> None:
    value = convert_amount(Decimal("100"), "CHF", "USD", [])
    assert value.value is None
    assert value.rate is None


def test_cross_rate_uses_declared_pair_direction() -> None:
    rates = [fx_rate("USD", "EUR", "2"), fx_rate("USD", "GBP", "0.5")]
    value = convert_amount(Decimal("10"), "EUR", "GBP", rates)
    assert value.value == Decimal("40")
    assert value.path == ("EUR", "USD", "GBP")


def test_foreign_fx_rate_must_be_positive_and_finite() -> None:
    base = {
        "base_currency": "USD",
        "foreign_currency": "EUR",
        "as_of_date": date(2026, 6, 30),
        "source_label": "test",
        "source_id": "src-test",
    }
    import pytest

    with pytest.raises(ValueError):
        FxRate(**base, rate="0")
    with pytest.raises(ValueError):
        FxRate(**base, rate="NaN")
