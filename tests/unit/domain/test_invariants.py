"""Structural invariants on canonical domain contracts."""

import pytest
from pydantic import ValidationError

from energy_trading.domain.models import ClearingStatus
from energy_trading.domain.value_objects import MoneyAmount
from tests.unit.domain._factories import (
    amd_money,
    availability,
    bid,
    clearing,
    constraint,
    dlq,
    settlement,
    utc,
)


def test_available_capacity_cannot_exceed_total() -> None:
    with pytest.raises(ValidationError):
        availability(available_capacity_mw=25.0, total_capacity_mw=20.0)


def test_available_capacity_may_equal_total() -> None:
    record = availability(available_capacity_mw=20.0, total_capacity_mw=20.0)
    assert record.available_capacity_mw == record.total_capacity_mw


def test_regulatory_effective_window_must_be_ordered() -> None:
    with pytest.raises(ValidationError):
        constraint(effective_from="2026-06-01", effective_to="2026-05-01")


def test_regulatory_numeric_bounds_must_be_ordered() -> None:
    with pytest.raises(ValidationError):
        constraint(minimum_value=10.0, maximum_value=5.0)


def test_bid_rejects_zero_and_negative_quantity() -> None:
    with pytest.raises(ValidationError):
        bid(quantity_mw=0)
    with pytest.raises(ValidationError):
        bid(quantity_mw=-1.0)


def test_rejected_clearing_may_omit_price() -> None:
    result = clearing(
        status=ClearingStatus.REJECTED,
        cleared_quantity_mw=0.0,
        clearing_price=None,
    )
    assert result.clearing_price is None


def test_cleared_result_requires_price() -> None:
    with pytest.raises(ValidationError):
        clearing(status=ClearingStatus.CLEARED, clearing_price=None)


def test_settlement_rejects_non_positive_period() -> None:
    with pytest.raises(ValidationError):
        settlement(period_start=utc(hour=11), period_end=utc(hour=11))
    with pytest.raises(ValidationError):
        settlement(period_start=utc(hour=12), period_end=utc(hour=11))


def test_settlement_rejects_mixed_currencies() -> None:
    with pytest.raises(ValidationError):
        settlement(profit=MoneyAmount(amount=amd_money("1.00").amount, currency="EUR"))


def test_settlement_does_not_recompute_profit() -> None:
    result = settlement(
        revenue=amd_money("100.00"),
        procurement_cost=amd_money("60.00"),
        balancing_cost=amd_money("5.00"),
        profit=amd_money("1.00"),
    )
    assert result.profit.amount != (
        result.revenue.amount - result.procurement_cost.amount - result.balancing_cost.amount
    )


def test_dlq_rejects_empty_diagnostics() -> None:
    with pytest.raises(ValidationError):
        dlq(diagnostics=())
