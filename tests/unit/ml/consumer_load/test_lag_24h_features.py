"""Exact 24-hour lag Consumer Load supervised feature rows."""

from __future__ import annotations

from datetime import timedelta

import pytest

from energy_trading.application.errors import InvalidRequestError
from energy_trading.ml.consumer_load.lag_24h_features import (
    ConsumerLoadLag24hFeatureRow,
    build_consumer_load_lag_24h_feature_rows,
)
from tests.unit.domain._factories import consumption, utc

_LAG = timedelta(hours=24)
_MIXED_CONSUMER_MESSAGE = (
    "Consumer Load 24-hour lag features require history from exactly one consumer."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "Consumer Load 24-hour lag features require unique historical timestamps."
)
_ROW_FIELDS = (
    "consumer_id",
    "target_timestamp",
    "lag_24h_mw",
    "target_value_mw",
)


def test_empty_history_returns_empty_tuple() -> None:
    assert build_consumer_load_lag_24h_feature_rows(history=()) == ()


def test_single_observation_returns_no_row() -> None:
    history = (consumption(timestamp=utc(hour=16), value_mw=7.25),)
    assert build_consumer_load_lag_24h_feature_rows(history=history) == ()


def test_exact_two_day_pair_produces_one_row() -> None:
    target_time = utc(hour=16)
    lag_time = target_time - _LAG
    lag_record = consumption(timestamp=lag_time, value_mw=4.5)
    target_record = consumption(timestamp=target_time, value_mw=7.25)
    result = build_consumer_load_lag_24h_feature_rows(
        history=(lag_record, target_record),
    )
    assert len(result) == 1
    row = result[0]
    assert isinstance(row, ConsumerLoadLag24hFeatureRow)
    assert row.lag_24h_mw == lag_record.value_mw
    assert row.lag_24h_mw == 4.5
    assert row.target_value_mw == target_record.value_mw
    assert row.target_value_mw == 7.25
    assert row.consumer_id == target_record.consumer_id
    assert row.consumer_id == "consumer-1"
    assert row.target_timestamp == target_time
    assert row.lag_24h_mw is lag_record.value_mw
    assert row.target_value_mw is target_record.value_mw


def test_canonical_mw_values_are_copied_without_mwh_conversion() -> None:
    target_time = utc(hour=12)
    lag_record = consumption(timestamp=target_time - _LAG, value_mw=3.125)
    target_record = consumption(timestamp=target_time, value_mw=9.75)
    result = build_consumer_load_lag_24h_feature_rows(
        history=(lag_record, target_record),
    )
    assert result[0].lag_24h_mw == 3.125
    assert result[0].target_value_mw == 9.75
    assert result[0].lag_24h_mw != result[0].target_value_mw * 1000
    assert result[0].target_value_mw != result[0].lag_24h_mw / 1000


def test_out_of_order_history_yields_chronological_rows() -> None:
    later = utc(hour=18)
    earlier = utc(hour=12)
    history = (
        consumption(timestamp=later, value_mw=6.0),
        consumption(timestamp=earlier - _LAG, value_mw=1.0),
        consumption(timestamp=later - _LAG, value_mw=2.0),
        consumption(timestamp=earlier, value_mw=5.0),
    )
    result = build_consumer_load_lag_24h_feature_rows(history=history)
    assert tuple(row.target_timestamp for row in result) == (earlier, later)
    assert result[0].lag_24h_mw == 1.0
    assert result[0].target_value_mw == 5.0
    assert result[1].lag_24h_mw == 2.0
    assert result[1].target_value_mw == 6.0


def test_multiple_complete_pairs_are_sorted_by_target_timestamp() -> None:
    first = utc(day=2, hour=10)
    second = utc(day=3, hour=10)
    third = utc(day=4, hour=10)
    history = (
        consumption(timestamp=third, value_mw=30.0),
        consumption(timestamp=first - _LAG, value_mw=1.0),
        consumption(timestamp=second, value_mw=20.0),
        consumption(timestamp=first, value_mw=10.0),
    )
    result = build_consumer_load_lag_24h_feature_rows(history=history)
    assert tuple(row.target_timestamp for row in result) == (first, second, third)
    assert tuple(row.lag_24h_mw for row in result) == (1.0, 10.0, 20.0)
    assert tuple(row.target_value_mw for row in result) == (10.0, 20.0, 30.0)


def test_missing_exact_lag_skips_only_that_candidate() -> None:
    paired_target = utc(hour=16)
    gapped_target = utc(hour=20)
    history = (
        consumption(timestamp=paired_target - _LAG, value_mw=4.0),
        consumption(timestamp=paired_target, value_mw=8.0),
        consumption(timestamp=gapped_target, value_mw=11.0),
    )
    result = build_consumer_load_lag_24h_feature_rows(history=history)
    assert len(result) == 1
    assert result[0].target_timestamp == paired_target
    assert result[0].lag_24h_mw == 4.0
    assert result[0].target_value_mw == 8.0


def test_near_timestamp_does_not_qualify() -> None:
    target = utc(hour=16)
    plus_one = (
        consumption(timestamp=(target - _LAG) + timedelta(minutes=1), value_mw=4.0),
        consumption(timestamp=target, value_mw=8.0),
    )
    minus_one = (
        consumption(timestamp=(target - _LAG) - timedelta(minutes=1), value_mw=4.0),
        consumption(timestamp=target, value_mw=8.0),
    )
    assert build_consumer_load_lag_24h_feature_rows(history=plus_one) == ()
    assert build_consumer_load_lag_24h_feature_rows(history=minus_one) == ()


def test_weekly_observation_is_not_a_fallback() -> None:
    target = utc(hour=16)
    history = (
        consumption(timestamp=target - timedelta(days=7), value_mw=4.0),
        consumption(timestamp=target, value_mw=8.0),
    )
    assert build_consumer_load_lag_24h_feature_rows(history=history) == ()


def test_gaps_do_not_use_nearest_or_interpolation() -> None:
    target = utc(hour=16)
    earlier_neighbor = (target - _LAG) - timedelta(hours=1)
    later_neighbor = (target - _LAG) + timedelta(hours=1)
    history = (
        consumption(timestamp=earlier_neighbor, value_mw=1.0),
        consumption(timestamp=later_neighbor, value_mw=9.0),
        consumption(timestamp=target, value_mw=5.0),
    )
    assert build_consumer_load_lag_24h_feature_rows(history=history) == ()


def test_duplicate_timestamp_fails_closed() -> None:
    stamp = utc(hour=16)
    history = (
        consumption(timestamp=stamp - _LAG, value_mw=1.0),
        consumption(timestamp=stamp, value_mw=2.0),
        consumption(timestamp=stamp, value_mw=9.0),
    )
    with pytest.raises(InvalidRequestError, match=_DUPLICATE_TIMESTAMP_MESSAGE) as caught:
        build_consumer_load_lag_24h_feature_rows(history=history)
    assert caught.value.code == "invalid_request"
    assert "2.0" not in caught.value.message
    assert "9.0" not in caught.value.message


def test_mixed_consumer_ids_fail_closed() -> None:
    target_time = utc(hour=16)
    history = (
        consumption(consumer_id="consumer-1", timestamp=target_time - _LAG, value_mw=1.0),
        consumption(consumer_id="consumer-2", timestamp=target_time, value_mw=2.0),
    )
    with pytest.raises(InvalidRequestError, match=_MIXED_CONSUMER_MESSAGE) as caught:
        build_consumer_load_lag_24h_feature_rows(history=history)
    assert caught.value.code == "invalid_request"
    assert "consumer-1" not in caught.value.message
    assert "consumer-2" not in caught.value.message


def test_ambiguous_history_does_not_return_partial_rows() -> None:
    target_time = utc(hour=16)
    mixed = (
        consumption(timestamp=target_time - _LAG, value_mw=1.0),
        consumption(timestamp=target_time, value_mw=2.0),
        consumption(consumer_id="other", timestamp=utc(hour=18), value_mw=3.0),
    )
    with pytest.raises(InvalidRequestError, match=_MIXED_CONSUMER_MESSAGE):
        build_consumer_load_lag_24h_feature_rows(history=mixed)


def test_caller_history_and_records_are_not_mutated() -> None:
    target_time = utc(hour=16)
    lag_record = consumption(timestamp=target_time - _LAG, value_mw=4.5)
    target_record = consumption(timestamp=target_time, value_mw=7.25)
    history = (target_record, lag_record)
    original_ids = tuple(id(record) for record in history)
    result = build_consumer_load_lag_24h_feature_rows(history=history)
    assert history == (target_record, lag_record)
    assert tuple(id(record) for record in history) == original_ids
    assert history[0] is target_record
    assert history[1] is lag_record
    assert result[0].target_timestamp == target_time


def test_repeated_equal_input_returns_value_equal_results() -> None:
    target_time = utc(hour=16)
    history = (
        consumption(timestamp=target_time - _LAG, value_mw=4.5),
        consumption(timestamp=target_time, value_mw=7.25),
    )
    first = build_consumer_load_lag_24h_feature_rows(history=history)
    second = build_consumer_load_lag_24h_feature_rows(history=history)
    assert first == second
    assert first is not second


def test_row_is_frozen_slotted_with_exactly_four_fields() -> None:
    target_time = utc(hour=16)
    result = build_consumer_load_lag_24h_feature_rows(
        history=(
            consumption(timestamp=target_time - _LAG, value_mw=4.5),
            consumption(timestamp=target_time, value_mw=7.25),
        ),
    )
    row = result[0]
    assert ConsumerLoadLag24hFeatureRow.__slots__ == _ROW_FIELDS
    with pytest.raises(AttributeError):
        row.lag_24h_mw = 0.0  # type: ignore[misc]
    assert not hasattr(row, "__dict__")


def test_row_contract_has_no_extra_feature_or_energy_conversion_fields() -> None:
    target_time = utc(hour=16)
    result = build_consumer_load_lag_24h_feature_rows(
        history=(
            consumption(timestamp=target_time - _LAG, value_mw=4.5),
            consumption(timestamp=target_time, value_mw=7.25),
        ),
    )
    row = result[0]
    assert ConsumerLoadLag24hFeatureRow.__slots__ == _ROW_FIELDS
    forbidden_attrs = (
        "lag_48h_mw",
        "lag_7d_mw",
        "lag_168h_mw",
        "rolling_mean_mw",
        "rolling_min_mw",
        "rolling_max_mw",
        "moving_std_mw",
        "hour_of_day",
        "day_of_week",
        "month",
        "holiday",
        "weather",
        "hydro",
        "generation",
        "news",
        "price",
        "features",
        "feature_vector",
        "value_mwh",
        "lag_24h_mwh",
        "target_value_mwh",
    )
    for name in forbidden_attrs:
        assert not hasattr(row, name)
