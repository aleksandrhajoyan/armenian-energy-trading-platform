"""Exact previous-day persistence DAM Price backtest-case builder."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from tests.unit.domain._factories import amd_price, utc

from energy_trading.application.errors import InvalidRequestError
from energy_trading.domain.models.observations import MarketPriceRecord
from energy_trading.domain.value_objects.money import EnergyPrice
from energy_trading.ml.dam_price.previous_day_persistence_backtest import (
    PreviousDayPersistenceBacktestCase,
    build_previous_day_persistence_backtest_cases,
)

_MIXED_MARKET_MESSAGE = (
    "Previous-day persistence backtest requires history from exactly one market."
)
_MIXED_CURRENCY_MESSAGE = (
    "Previous-day persistence backtest requires history in exactly one currency."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "Previous-day persistence backtest requires unique historical timestamps."
)
_LAG = timedelta(hours=24)


def _ts(day: int, hour: int = 16) -> datetime:
    return datetime(2026, 10, day, hour, 0, 0, tzinfo=UTC)


def _market(
    *,
    timestamp: datetime,
    market_id: str = "market-1",
    price: EnergyPrice | None = None,
    volume_mwh: float | None = None,
) -> MarketPriceRecord:
    values: dict[str, object] = {
        "market_id": market_id,
        "timestamp": timestamp,
        "price": price if price is not None else amd_price(),
    }
    if volume_mwh is not None:
        values["volume_mwh"] = volume_mwh
    return MarketPriceRecord(**values)  # type: ignore[arg-type]


def _build(
    history: tuple[MarketPriceRecord, ...],
) -> tuple[PreviousDayPersistenceBacktestCase, ...]:
    return build_previous_day_persistence_backtest_cases(history=history)


def test_empty_history_returns_empty_tuple() -> None:
    result = _build(())
    assert result == ()
    assert isinstance(result, tuple)


def test_single_observation_returns_empty_tuple() -> None:
    result = _build((_market(timestamp=utc(hour=16)),))
    assert result == ()


def test_one_exact_pair_produces_one_case() -> None:
    target = utc(hour=16)
    lag_price = amd_price("45.00")
    actual_price = amd_price("52.50")
    history = (
        _market(timestamp=target - _LAG, price=lag_price),
        _market(timestamp=target, price=actual_price),
    )
    result = _build(history)
    assert len(result) == 1
    case = result[0]
    assert isinstance(case, PreviousDayPersistenceBacktestCase)
    assert case.market_id == "market-1"
    assert case.target_timestamp == target
    assert case.predicted_price == lag_price
    assert case.actual_price == actual_price
    assert case.predicted_price.amount_per_mwh == Decimal("45.00")
    assert case.actual_price.amount_per_mwh == Decimal("52.50")


def test_canonical_price_is_preserved_without_transformation() -> None:
    target = utc(hour=16)
    lag_price = EnergyPrice(amount_per_mwh=Decimal("-12.75"), currency="AMD")
    actual_price = EnergyPrice(amount_per_mwh=Decimal("0.01"), currency="AMD")
    history = (
        _market(timestamp=target - _LAG, price=lag_price),
        _market(timestamp=target, price=actual_price),
    )
    case = _build(history)[0]
    assert case.predicted_price == lag_price
    assert case.actual_price == actual_price
    assert isinstance(case.predicted_price.amount_per_mwh, Decimal)
    assert isinstance(case.actual_price.amount_per_mwh, Decimal)
    assert case.predicted_price.amount_per_mwh < 0
    assert case.predicted_price.currency == "AMD"
    assert case.actual_price.currency == "AMD"


def test_negative_actual_price_is_preserved() -> None:
    target = utc(hour=16)
    negative_actual = EnergyPrice(amount_per_mwh=Decimal("-3.50"), currency="AMD")
    history = (
        _market(timestamp=target - _LAG, price=amd_price("10.00")),
        _market(timestamp=target, price=negative_actual),
    )
    case = _build(history)[0]
    assert case.actual_price == negative_actual
    assert case.actual_price.amount_per_mwh == Decimal("-3.50")
    assert case.actual_price.amount_per_mwh < 0


def test_several_daily_pairs_yield_chronological_cases() -> None:
    history = tuple(
        _market(timestamp=_ts(day), price=amd_price(f"{10 + day}.00")) for day in range(1, 4)
    )
    result = _build(history)
    assert len(result) == 2
    timestamps = tuple(case.target_timestamp for case in result)
    assert timestamps == (_ts(2), _ts(3))
    assert timestamps == tuple(sorted(timestamps))


def test_out_of_order_input_produces_sorted_output() -> None:
    first = _ts(1)
    second = _ts(2)
    third = _ts(3)
    records = (
        _market(timestamp=first, price=amd_price("10.00")),
        _market(timestamp=second, price=amd_price("20.00")),
        _market(timestamp=third, price=amd_price("30.00")),
    )
    ordered = _build(records)
    shuffled = _build((records[2], records[0], records[1]))
    assert ordered == shuffled
    assert tuple(case.target_timestamp for case in shuffled) == (second, third)
    assert shuffled[0].predicted_price.amount_per_mwh == Decimal("10.00")
    assert shuffled[1].predicted_price.amount_per_mwh == Decimal("20.00")


def test_missing_exact_lag_is_skipped_not_raised() -> None:
    day_one = _ts(1)
    day_two = _ts(2)
    day_four = _ts(4)
    history = (
        _market(timestamp=day_one, price=amd_price("10.00")),
        _market(timestamp=day_two, price=amd_price("20.00")),
        _market(timestamp=day_four, price=amd_price("30.00")),
    )
    result = _build(history)
    assert tuple(case.target_timestamp for case in result) == (day_two,)


def test_history_with_gaps_keeps_only_exact_pairs() -> None:
    day_one = _ts(1)
    day_two = _ts(2)
    lonely = _ts(9)
    history = (
        _market(timestamp=day_one, price=amd_price("10.00")),
        _market(timestamp=day_two, price=amd_price("20.00")),
        _market(timestamp=lonely, price=amd_price("99.00")),
    )
    result = _build(history)
    assert len(result) == 1
    assert result[0].target_timestamp == day_two
    assert all(case.target_timestamp != lonely for case in result)


def test_near_but_not_exact_lag_is_not_used_as_prediction() -> None:
    target = utc(hour=16)
    near = target - _LAG + timedelta(minutes=1)
    history = (
        _market(timestamp=near, price=amd_price("99.00")),
        _market(timestamp=target, price=amd_price("50.00")),
    )
    result = _build(history)
    assert result == ()


def test_weekly_observation_is_not_a_previous_day_pair() -> None:
    target = utc(hour=16)
    history = (
        _market(timestamp=target - timedelta(hours=168), price=amd_price("99.00")),
        _market(timestamp=target, price=amd_price("50.00")),
    )
    result = _build(history)
    assert result == ()


def test_duplicate_history_timestamp_fails_closed() -> None:
    target = utc(hour=16)
    lag_timestamp = target - _LAG
    history = (
        _market(timestamp=lag_timestamp, price=amd_price("10.00")),
        _market(timestamp=lag_timestamp, price=amd_price("11.00")),
        _market(timestamp=target, price=amd_price("50.00")),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _build(history)
    assert captured.value.message == _DUPLICATE_TIMESTAMP_MESSAGE


def test_duplicate_timestamp_fails_closed_even_without_valid_pair() -> None:
    duplicate = utc(hour=3)
    history = (
        _market(timestamp=duplicate, price=amd_price("10.00")),
        _market(timestamp=duplicate, price=amd_price("11.00")),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _build(history)
    assert captured.value.message == _DUPLICATE_TIMESTAMP_MESSAGE


def test_mixed_market_history_fails_closed() -> None:
    target = utc(hour=16)
    history = (
        _market(timestamp=target - _LAG, market_id="market-a"),
        _market(timestamp=target, market_id="market-b"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _build(history)
    assert captured.value.message == _MIXED_MARKET_MESSAGE
    assert "market-a" not in captured.value.message
    assert "market-b" not in captured.value.message


def test_mixed_currency_history_fails_closed() -> None:
    target = utc(hour=16)
    history = (
        _market(
            timestamp=target - _LAG,
            price=EnergyPrice(amount_per_mwh=Decimal("10.00"), currency="AMD"),
        ),
        _market(
            timestamp=target,
            price=EnergyPrice(amount_per_mwh=Decimal("11.00"), currency="EUR"),
        ),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _build(history)
    assert captured.value.message == _MIXED_CURRENCY_MESSAGE
    assert "AMD" not in captured.value.message
    assert "EUR" not in captured.value.message


def test_volume_is_irrelevant_to_cases() -> None:
    target = utc(hour=16)
    history = (
        _market(timestamp=target - _LAG, price=amd_price("10.00"), volume_mwh=1000.0),
        _market(timestamp=target, price=amd_price("20.00"), volume_mwh=1.0),
    )
    case = _build(history)[0]
    assert case.predicted_price.amount_per_mwh == Decimal("10.00")
    assert case.actual_price.amount_per_mwh == Decimal("20.00")
    case_fields = {item.name for item in fields(PreviousDayPersistenceBacktestCase)}
    assert "volume_mwh" not in case_fields
    assert not hasattr(case, "volume_mwh")


def test_input_history_is_not_mutated() -> None:
    target = utc(hour=16)
    lag_record = _market(timestamp=target - _LAG, price=amd_price("10.00"))
    actual_record = _market(timestamp=target, price=amd_price("20.00"))
    history = (lag_record, actual_record)
    _build(history)
    assert history == (lag_record, actual_record)
    assert lag_record.price.amount_per_mwh == Decimal("10.00")
    assert actual_record.price.amount_per_mwh == Decimal("20.00")
    assert lag_record.timestamp == target - _LAG


def test_repeated_equal_inputs_are_value_equivalent() -> None:
    target = utc(hour=16)
    history = (
        _market(timestamp=target - _LAG, price=amd_price("10.00")),
        _market(timestamp=target, price=amd_price("20.00")),
    )
    assert _build(history) == _build(history)


def test_case_contract_is_frozen_slotted_and_exactly_four_fields() -> None:
    names = tuple(item.name for item in fields(PreviousDayPersistenceBacktestCase))
    assert names == ("market_id", "target_timestamp", "predicted_price", "actual_price")
    assert PreviousDayPersistenceBacktestCase.__slots__ == names
    target = utc(hour=16)
    case = _build(
        (
            _market(timestamp=target - _LAG, price=amd_price("10.00")),
            _market(timestamp=target, price=amd_price("20.00")),
        )
    )[0]
    with pytest.raises(FrozenInstanceError):
        case.actual_price = amd_price("1.00")  # type: ignore[misc]


def test_case_has_no_metric_or_identity_fields() -> None:
    names = {item.name for item in fields(PreviousDayPersistenceBacktestCase)}
    forbidden = {
        "residual",
        "error",
        "absolute_error",
        "percentage_error",
        "mae",
        "mse",
        "rmse",
        "mape",
        "weight",
        "forecast_run_id",
        "generated_at",
        "volume_mwh",
        "model_name",
        "model_version",
    }
    assert forbidden.isdisjoint(names)
    assert len(names) == 4


def test_builder_is_synchronous_and_keyword_only() -> None:
    import inspect

    assert not inspect.iscoroutinefunction(build_previous_day_persistence_backtest_cases)
    parameters = inspect.signature(build_previous_day_persistence_backtest_cases).parameters
    assert tuple(parameters) == ("history",)
    assert parameters["history"].kind is inspect.Parameter.KEYWORD_ONLY
