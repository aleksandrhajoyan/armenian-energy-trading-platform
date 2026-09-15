"""Exact previous-day persistence Consumer Load backtest cases."""

from __future__ import annotations

from datetime import timedelta

import pytest

from energy_trading.application.errors import InvalidRequestError
from energy_trading.ml.consumer_load.previous_day_persistence_backtest import (
    PreviousDayPersistenceBacktestCase,
    build_previous_day_persistence_backtest_cases,
)
from tests.unit.domain._factories import consumption, utc

_LAG = timedelta(hours=24)
_MIXED_CONSUMER_MESSAGE = (
    "Previous-day persistence backtest requires history from exactly one consumer."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "Previous-day persistence backtest requires unique historical timestamps."
)


def test_empty_history_returns_empty_tuple() -> None:
    assert build_previous_day_persistence_backtest_cases(history=()) == ()


def test_single_observation_returns_no_case() -> None:
    history = (consumption(timestamp=utc(hour=16), value_mw=7.25),)
    assert build_previous_day_persistence_backtest_cases(history=history) == ()


def test_exact_two_day_pair_produces_one_case() -> None:
    actual_time = utc(hour=16)
    lag_time = actual_time - _LAG
    lag_record = consumption(timestamp=lag_time, value_mw=4.5)
    actual_record = consumption(timestamp=actual_time, value_mw=7.25)
    result = build_previous_day_persistence_backtest_cases(
        history=(lag_record, actual_record),
    )
    assert len(result) == 1
    case = result[0]
    assert isinstance(case, PreviousDayPersistenceBacktestCase)
    assert case.predicted_value_mw == lag_record.value_mw
    assert case.predicted_value_mw == 4.5
    assert case.actual_value_mw == actual_record.value_mw
    assert case.actual_value_mw == 7.25
    assert case.consumer_id == actual_record.consumer_id
    assert case.consumer_id == "consumer-1"
    assert case.target_timestamp == actual_time
    assert case.predicted_value_mw is lag_record.value_mw
    assert case.actual_value_mw is actual_record.value_mw


def test_canonical_mw_values_are_copied_without_mwh_conversion() -> None:
    actual_time = utc(hour=12)
    lag_record = consumption(timestamp=actual_time - _LAG, value_mw=3.125)
    actual_record = consumption(timestamp=actual_time, value_mw=9.75)
    result = build_previous_day_persistence_backtest_cases(
        history=(lag_record, actual_record),
    )
    assert result[0].predicted_value_mw == 3.125
    assert result[0].actual_value_mw == 9.75
    assert result[0].predicted_value_mw != result[0].actual_value_mw * 1000
    assert result[0].actual_value_mw != result[0].predicted_value_mw / 1000


def test_out_of_order_history_yields_chronological_cases() -> None:
    later = utc(hour=18)
    earlier = utc(hour=12)
    history = (
        consumption(timestamp=later, value_mw=6.0),
        consumption(timestamp=earlier - _LAG, value_mw=1.0),
        consumption(timestamp=later - _LAG, value_mw=2.0),
        consumption(timestamp=earlier, value_mw=5.0),
    )
    result = build_previous_day_persistence_backtest_cases(history=history)
    assert tuple(case.target_timestamp for case in result) == (earlier, later)
    assert result[0].predicted_value_mw == 1.0
    assert result[0].actual_value_mw == 5.0
    assert result[1].predicted_value_mw == 2.0
    assert result[1].actual_value_mw == 6.0


def test_multiple_valid_pairs_are_sorted_by_target_timestamp() -> None:
    first = utc(day=2, hour=10)
    second = utc(day=3, hour=10)
    third = utc(day=4, hour=10)
    history = (
        consumption(timestamp=third, value_mw=30.0),
        consumption(timestamp=first - _LAG, value_mw=1.0),
        consumption(timestamp=second, value_mw=20.0),
        consumption(timestamp=first, value_mw=10.0),
    )
    result = build_previous_day_persistence_backtest_cases(history=history)
    assert tuple(case.target_timestamp for case in result) == (first, second, third)
    assert tuple(case.predicted_value_mw for case in result) == (1.0, 10.0, 20.0)
    assert tuple(case.actual_value_mw for case in result) == (10.0, 20.0, 30.0)


def test_missing_exact_lag_skips_only_that_candidate() -> None:
    paired_target = utc(hour=16)
    gapped_target = utc(hour=20)
    history = (
        consumption(timestamp=paired_target - _LAG, value_mw=4.0),
        consumption(timestamp=paired_target, value_mw=8.0),
        consumption(timestamp=gapped_target, value_mw=11.0),
    )
    result = build_previous_day_persistence_backtest_cases(history=history)
    assert len(result) == 1
    assert result[0].target_timestamp == paired_target
    assert result[0].predicted_value_mw == 4.0
    assert result[0].actual_value_mw == 8.0


def test_near_timestamp_does_not_qualify() -> None:
    target = utc(hour=16)
    history = (
        consumption(timestamp=(target - _LAG) + timedelta(minutes=1), value_mw=4.0),
        consumption(timestamp=target, value_mw=8.0),
    )
    assert build_previous_day_persistence_backtest_cases(history=history) == ()


def test_weekly_observation_is_not_a_fallback() -> None:
    target = utc(hour=16)
    history = (
        consumption(timestamp=target - timedelta(days=7), value_mw=4.0),
        consumption(timestamp=target, value_mw=8.0),
    )
    assert build_previous_day_persistence_backtest_cases(history=history) == ()


def test_gaps_do_not_use_nearest_or_interpolation() -> None:
    target = utc(hour=16)
    earlier_neighbor = (target - _LAG) - timedelta(hours=1)
    later_neighbor = (target - _LAG) + timedelta(hours=1)
    history = (
        consumption(timestamp=earlier_neighbor, value_mw=1.0),
        consumption(timestamp=later_neighbor, value_mw=9.0),
        consumption(timestamp=target, value_mw=5.0),
    )
    assert build_previous_day_persistence_backtest_cases(history=history) == ()


def test_duplicate_timestamp_fails_closed() -> None:
    stamp = utc(hour=16)
    history = (
        consumption(timestamp=stamp - _LAG, value_mw=1.0),
        consumption(timestamp=stamp, value_mw=2.0),
        consumption(timestamp=stamp, value_mw=9.0),
    )
    with pytest.raises(InvalidRequestError, match=_DUPLICATE_TIMESTAMP_MESSAGE) as caught:
        build_previous_day_persistence_backtest_cases(history=history)
    assert caught.value.code == "invalid_request"
    assert "2.0" not in caught.value.message
    assert "9.0" not in caught.value.message


def test_mixed_consumer_ids_fail_closed() -> None:
    actual_time = utc(hour=16)
    history = (
        consumption(consumer_id="consumer-1", timestamp=actual_time - _LAG, value_mw=1.0),
        consumption(consumer_id="consumer-2", timestamp=actual_time, value_mw=2.0),
    )
    with pytest.raises(InvalidRequestError, match=_MIXED_CONSUMER_MESSAGE) as caught:
        build_previous_day_persistence_backtest_cases(history=history)
    assert caught.value.code == "invalid_request"
    assert "consumer-1" not in caught.value.message
    assert "consumer-2" not in caught.value.message


def test_ambiguous_history_does_not_return_partial_cases() -> None:
    actual_time = utc(hour=16)
    valid_pair = (
        consumption(timestamp=actual_time - _LAG, value_mw=1.0),
        consumption(timestamp=actual_time, value_mw=2.0),
        consumption(consumer_id="other", timestamp=utc(hour=18), value_mw=3.0),
    )
    with pytest.raises(InvalidRequestError, match=_MIXED_CONSUMER_MESSAGE):
        build_previous_day_persistence_backtest_cases(history=valid_pair)


def test_caller_history_and_records_are_not_mutated() -> None:
    actual_time = utc(hour=16)
    lag_record = consumption(timestamp=actual_time - _LAG, value_mw=4.5)
    actual_record = consumption(timestamp=actual_time, value_mw=7.25)
    history = (actual_record, lag_record)
    original_ids = tuple(id(record) for record in history)
    result = build_previous_day_persistence_backtest_cases(history=history)
    assert history == (actual_record, lag_record)
    assert tuple(id(record) for record in history) == original_ids
    assert history[0] is actual_record
    assert history[1] is lag_record
    assert result[0].target_timestamp == actual_time


def test_repeated_equal_input_returns_value_equal_results() -> None:
    actual_time = utc(hour=16)
    history = (
        consumption(timestamp=actual_time - _LAG, value_mw=4.5),
        consumption(timestamp=actual_time, value_mw=7.25),
    )
    first = build_previous_day_persistence_backtest_cases(history=history)
    second = build_previous_day_persistence_backtest_cases(history=history)
    assert first == second
    assert first is not second


def test_case_contract_has_no_residual_or_metric_fields() -> None:
    actual_time = utc(hour=16)
    result = build_previous_day_persistence_backtest_cases(
        history=(
            consumption(timestamp=actual_time - _LAG, value_mw=4.5),
            consumption(timestamp=actual_time, value_mw=7.25),
        ),
    )
    assert PreviousDayPersistenceBacktestCase.__slots__ == (
        "consumer_id",
        "target_timestamp",
        "predicted_value_mw",
        "actual_value_mw",
    )
    assert not hasattr(result[0], "residual")
    assert not hasattr(result[0], "error")
    assert not hasattr(result[0], "mae")
    assert not hasattr(result[0], "mse")
    assert not hasattr(result[0], "rmse")
    assert not hasattr(result[0], "mape")
    assert not hasattr(result[0], "metric")
