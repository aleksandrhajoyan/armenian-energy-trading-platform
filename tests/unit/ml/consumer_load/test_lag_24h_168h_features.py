"""Exact 24-hour plus 168-hour lag Consumer Load supervised feature rows."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from energy_trading.application.errors import InvalidRequestError
from energy_trading.domain.models.observations import ConsumptionRecord
from energy_trading.ml.consumer_load.lag_24h_168h_features import (
    ConsumerLoadLag24h168hFeatureRow,
    build_consumer_load_lag_24h_168h_feature_rows,
)
from tests.unit.domain._factories import consumption, utc

_LAG_24H = timedelta(hours=24)
_LAG_168H = timedelta(hours=168)
_MIXED_CONSUMER_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag features require history from exactly one consumer."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag features require unique historical timestamps."
)
_ROW_FIELDS = (
    "consumer_id",
    "target_timestamp",
    "lag_24h_mw",
    "lag_168h_mw",
    "target_value_mw",
)


def _triple(
    *,
    target_time: datetime | None = None,
    lag_24h_mw: float = 4.5,
    lag_168h_mw: float = 2.25,
    target_mw: float = 7.25,
    consumer_id: str = "consumer-1",
) -> tuple[datetime, ConsumptionRecord, ConsumptionRecord, ConsumptionRecord]:
    target = utc(day=15, hour=16) if target_time is None else target_time
    lag_24h = consumption(
        consumer_id=consumer_id,
        timestamp=target - _LAG_24H,
        value_mw=lag_24h_mw,
    )
    lag_168h = consumption(
        consumer_id=consumer_id,
        timestamp=target - _LAG_168H,
        value_mw=lag_168h_mw,
    )
    actual = consumption(consumer_id=consumer_id, timestamp=target, value_mw=target_mw)
    return target, lag_24h, lag_168h, actual


def test_one_exact_valid_row_with_both_lags() -> None:
    target, lag_24h, lag_168h, actual = _triple()
    result = build_consumer_load_lag_24h_168h_feature_rows(
        history=(lag_168h, lag_24h, actual),
    )
    assert len(result) == 1
    row = result[0]
    assert isinstance(row, ConsumerLoadLag24h168hFeatureRow)
    assert row.lag_24h_mw == lag_24h.value_mw
    assert row.lag_24h_mw == 4.5
    assert row.lag_168h_mw == lag_168h.value_mw
    assert row.lag_168h_mw == 2.25
    assert row.target_value_mw == actual.value_mw
    assert row.target_value_mw == 7.25
    assert row.consumer_id == actual.consumer_id
    assert row.consumer_id == "consumer-1"
    assert row.target_timestamp == target
    assert row.lag_24h_mw is lag_24h.value_mw
    assert row.lag_168h_mw is lag_168h.value_mw
    assert row.target_value_mw is actual.value_mw


def test_multiple_valid_rows_are_chronological() -> None:
    first = utc(day=15, hour=16)
    second = utc(day=16, hour=16)
    history = (
        consumption(timestamp=second, value_mw=30.0),
        consumption(timestamp=first - _LAG_168H, value_mw=1.0),
        consumption(timestamp=second - _LAG_168H, value_mw=2.0),
        consumption(timestamp=first - _LAG_24H, value_mw=10.0),
        consumption(timestamp=first, value_mw=20.0),
    )
    result = build_consumer_load_lag_24h_168h_feature_rows(history=history)
    assert tuple(row.target_timestamp for row in result) == (first, second)
    assert tuple(row.lag_24h_mw for row in result) == (10.0, 20.0)
    assert tuple(row.lag_168h_mw for row in result) == (1.0, 2.0)
    assert tuple(row.target_value_mw for row in result) == (20.0, 30.0)


def test_exact_lag_24h_mw_is_copied_unchanged() -> None:
    _, lag_24h, lag_168h, actual = _triple(lag_24h_mw=3.125)
    result = build_consumer_load_lag_24h_168h_feature_rows(
        history=(lag_24h, lag_168h, actual),
    )
    assert result[0].lag_24h_mw == 3.125
    assert result[0].lag_24h_mw is lag_24h.value_mw
    assert result[0].lag_24h_mw != result[0].target_value_mw * 1000


def test_exact_lag_168h_mw_is_copied_unchanged() -> None:
    _, lag_24h, lag_168h, actual = _triple(lag_168h_mw=11.75)
    result = build_consumer_load_lag_24h_168h_feature_rows(
        history=(lag_24h, lag_168h, actual),
    )
    assert result[0].lag_168h_mw == 11.75
    assert result[0].lag_168h_mw is lag_168h.value_mw
    assert result[0].lag_168h_mw != result[0].target_value_mw / 1000


def test_target_actual_is_copied_unchanged() -> None:
    _, lag_24h, lag_168h, actual = _triple(target_mw=9.75)
    result = build_consumer_load_lag_24h_168h_feature_rows(
        history=(lag_24h, lag_168h, actual),
    )
    assert result[0].target_value_mw == 9.75
    assert result[0].target_value_mw is actual.value_mw


def test_identity_and_target_timestamp_are_preserved() -> None:
    target, lag_24h, lag_168h, actual = _triple(consumer_id="consumer-1")
    result = build_consumer_load_lag_24h_168h_feature_rows(
        history=(lag_24h, lag_168h, actual),
    )
    assert result[0].consumer_id == actual.consumer_id
    assert result[0].target_timestamp == target
    assert result[0].target_timestamp is actual.timestamp


def test_row_is_frozen_slotted_with_exactly_five_fields() -> None:
    _, lag_24h, lag_168h, actual = _triple()
    result = build_consumer_load_lag_24h_168h_feature_rows(
        history=(lag_24h, lag_168h, actual),
    )
    row = result[0]
    assert ConsumerLoadLag24h168hFeatureRow.__slots__ == _ROW_FIELDS
    with pytest.raises(AttributeError):
        row.lag_24h_mw = 0.0  # type: ignore[misc]
    assert not hasattr(row, "__dict__")
    forbidden_attrs = (
        "lag_48h_mw",
        "lag_7d_mw",
        "rolling_mean_mw",
        "hour_of_day",
        "day_of_week",
        "holiday",
        "weather",
        "features",
        "feature_vector",
        "value_mwh",
    )
    for name in forbidden_attrs:
        assert not hasattr(row, name)


def test_empty_history_returns_empty_tuple() -> None:
    assert build_consumer_load_lag_24h_168h_feature_rows(history=()) == ()


def test_missing_exact_24h_lag_skips_that_target() -> None:
    target, _, lag_168h, actual = _triple()
    result = build_consumer_load_lag_24h_168h_feature_rows(history=(lag_168h, actual))
    assert result == ()
    assert target not in {row.target_timestamp for row in result}


def test_missing_exact_168h_lag_skips_that_target() -> None:
    target, lag_24h, _, actual = _triple()
    result = build_consumer_load_lag_24h_168h_feature_rows(history=(lag_24h, actual))
    assert result == ()
    assert target not in {row.target_timestamp for row in result}


def test_missing_either_required_lag_does_not_produce_a_partial_row() -> None:
    target = utc(day=15, hour=16)
    only_24h = (
        consumption(timestamp=target - _LAG_24H, value_mw=4.0),
        consumption(timestamp=target, value_mw=8.0),
    )
    only_168h = (
        consumption(timestamp=target - _LAG_168H, value_mw=2.0),
        consumption(timestamp=target, value_mw=8.0),
    )
    assert build_consumer_load_lag_24h_168h_feature_rows(history=only_24h) == ()
    assert build_consumer_load_lag_24h_168h_feature_rows(history=only_168h) == ()


def test_near_24h_timestamp_is_not_substituted() -> None:
    target, _, lag_168h, actual = _triple()
    plus_one = (
        lag_168h,
        consumption(timestamp=(target - _LAG_24H) + timedelta(minutes=1), value_mw=4.0),
        actual,
    )
    minus_one = (
        lag_168h,
        consumption(timestamp=(target - _LAG_24H) - timedelta(minutes=1), value_mw=4.0),
        actual,
    )
    assert build_consumer_load_lag_24h_168h_feature_rows(history=plus_one) == ()
    assert build_consumer_load_lag_24h_168h_feature_rows(history=minus_one) == ()


def test_near_168h_timestamp_is_not_substituted() -> None:
    target, lag_24h, _, actual = _triple()
    plus_one = (
        lag_24h,
        consumption(timestamp=(target - _LAG_168H) + timedelta(minutes=1), value_mw=2.0),
        actual,
    )
    minus_one = (
        lag_24h,
        consumption(timestamp=(target - _LAG_168H) - timedelta(minutes=1), value_mw=2.0),
        actual,
    )
    hours_167 = (
        lag_24h,
        consumption(timestamp=target - timedelta(hours=167), value_mw=2.0),
        actual,
    )
    hours_169 = (
        lag_24h,
        consumption(timestamp=target - timedelta(hours=169), value_mw=2.0),
        actual,
    )
    assert build_consumer_load_lag_24h_168h_feature_rows(history=plus_one) == ()
    assert build_consumer_load_lag_24h_168h_feature_rows(history=minus_one) == ()
    assert build_consumer_load_lag_24h_168h_feature_rows(history=hours_167) == ()
    assert build_consumer_load_lag_24h_168h_feature_rows(history=hours_169) == ()


def test_unsorted_input_yields_deterministic_chronological_output() -> None:
    later = utc(day=16, hour=18)
    earlier = utc(day=15, hour=12)
    history = (
        consumption(timestamp=later, value_mw=6.0),
        consumption(timestamp=earlier - _LAG_168H, value_mw=0.5),
        consumption(timestamp=later - _LAG_24H, value_mw=2.0),
        consumption(timestamp=earlier, value_mw=5.0),
        consumption(timestamp=later - _LAG_168H, value_mw=1.5),
        consumption(timestamp=earlier - _LAG_24H, value_mw=1.0),
    )
    result = build_consumer_load_lag_24h_168h_feature_rows(history=history)
    assert tuple(row.target_timestamp for row in result) == (earlier, later)
    assert result[0].lag_24h_mw == 1.0
    assert result[0].lag_168h_mw == 0.5
    assert result[0].target_value_mw == 5.0
    assert result[1].lag_24h_mw == 2.0
    assert result[1].lag_168h_mw == 1.5
    assert result[1].target_value_mw == 6.0


def test_mixed_consumers_fail_closed() -> None:
    target = utc(day=15, hour=16)
    history = (
        consumption(consumer_id="consumer-1", timestamp=target - _LAG_168H, value_mw=1.0),
        consumption(consumer_id="consumer-1", timestamp=target - _LAG_24H, value_mw=2.0),
        consumption(consumer_id="consumer-2", timestamp=target, value_mw=3.0),
    )
    with pytest.raises(InvalidRequestError, match=_MIXED_CONSUMER_MESSAGE) as caught:
        build_consumer_load_lag_24h_168h_feature_rows(history=history)
    assert caught.value.code == "invalid_request"


def test_duplicate_timestamps_fail_closed() -> None:
    target = utc(day=15, hour=16)
    history = (
        consumption(timestamp=target - _LAG_168H, value_mw=1.0),
        consumption(timestamp=target - _LAG_24H, value_mw=2.0),
        consumption(timestamp=target, value_mw=3.0),
        consumption(timestamp=target, value_mw=9.0),
    )
    with pytest.raises(InvalidRequestError, match=_DUPLICATE_TIMESTAMP_MESSAGE) as caught:
        build_consumer_load_lag_24h_168h_feature_rows(history=history)
    assert caught.value.code == "invalid_request"
    assert "3.0" not in caught.value.message
    assert "9.0" not in caught.value.message


def test_raw_consumer_ids_are_not_leaked_in_mixed_consumer_failure_text() -> None:
    target = utc(day=15, hour=16)
    history = (
        consumption(consumer_id="consumer-1", timestamp=target - _LAG_168H, value_mw=1.0),
        consumption(consumer_id="consumer-1", timestamp=target - _LAG_24H, value_mw=2.0),
        consumption(consumer_id="consumer-2", timestamp=target, value_mw=3.0),
    )
    with pytest.raises(InvalidRequestError, match=_MIXED_CONSUMER_MESSAGE) as caught:
        build_consumer_load_lag_24h_168h_feature_rows(history=history)
    assert "consumer-1" not in caught.value.message
    assert "consumer-2" not in caught.value.message


def test_caller_history_and_records_are_not_mutated() -> None:
    _, lag_24h, lag_168h, actual = _triple()
    history = (actual, lag_24h, lag_168h)
    original_ids = tuple(id(record) for record in history)
    result = build_consumer_load_lag_24h_168h_feature_rows(history=history)
    assert history == (actual, lag_24h, lag_168h)
    assert tuple(id(record) for record in history) == original_ids
    assert history[0] is actual
    assert history[1] is lag_24h
    assert history[2] is lag_168h
    assert result[0].target_timestamp == actual.timestamp


def test_repeated_equal_input_returns_value_equal_results() -> None:
    _, lag_24h, lag_168h, actual = _triple()
    history = (lag_24h, lag_168h, actual)
    first = build_consumer_load_lag_24h_168h_feature_rows(history=history)
    second = build_consumer_load_lag_24h_168h_feature_rows(history=history)
    assert first == second
    assert first is not second


def test_return_type_is_tuple_of_exact_row_dto() -> None:
    _, lag_24h, lag_168h, actual = _triple()
    result = build_consumer_load_lag_24h_168h_feature_rows(
        history=(lag_24h, lag_168h, actual),
    )
    assert type(result) is tuple
    assert all(type(row) is ConsumerLoadLag24h168hFeatureRow for row in result)


def test_no_row_from_only_a_24h_lag_without_168h() -> None:
    target, lag_24h, _, actual = _triple()
    history = (lag_24h, actual)
    result = build_consumer_load_lag_24h_168h_feature_rows(history=history)
    assert result == ()
    assert not any(row.target_timestamp == target for row in result)


def test_no_row_from_only_a_168h_lag_without_24h() -> None:
    target, _, lag_168h, actual = _triple()
    history = (lag_168h, actual)
    result = build_consumer_load_lag_24h_168h_feature_rows(history=history)
    assert result == ()
    assert not any(row.target_timestamp == target for row in result)
