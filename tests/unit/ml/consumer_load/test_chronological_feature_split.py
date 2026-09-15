"""Chronological Consumer Load feature-row train/evaluation split."""

from __future__ import annotations

from datetime import timedelta

import pytest

from energy_trading.application.errors import InvalidRequestError
from energy_trading.ml.consumer_load.chronological_feature_split import (
    ConsumerLoadChronologicalFeatureSplit,
    split_consumer_load_feature_rows_chronologically,
)
from energy_trading.ml.consumer_load.lag_24h_features import ConsumerLoadLag24hFeatureRow
from tests.unit.domain._factories import utc

_EMPTY_ROWS_MESSAGE = "Consumer Load chronological feature split requires at least one feature row."
_MIXED_CONSUMER_MESSAGE = (
    "Consumer Load chronological feature split requires rows from exactly one consumer."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "Consumer Load chronological feature split requires unique target timestamps."
)
_OUT_OF_ORDER_MESSAGE = (
    "Consumer Load chronological feature split requires strictly increasing target timestamps."
)
_EMPTY_TRAINING_MESSAGE = (
    "Consumer Load chronological feature split requires a non-empty training partition."
)
_EMPTY_EVALUATION_MESSAGE = (
    "Consumer Load chronological feature split requires a non-empty evaluation partition."
)
_SPLIT_FIELDS = (
    "training_rows",
    "evaluation_rows",
)


def _row(
    *,
    hour: int,
    day: int = 1,
    value_mw: float = 8.0,
    lag_mw: float = 4.0,
    consumer_id: str = "consumer-1",
) -> ConsumerLoadLag24hFeatureRow:
    return ConsumerLoadLag24hFeatureRow(
        consumer_id=consumer_id,
        target_timestamp=utc(day=day, hour=hour),
        lag_24h_mw=lag_mw,
        target_value_mw=value_mw,
    )


def test_valid_rows_spanning_cutoff_produce_correct_partitions() -> None:
    earlier = _row(hour=10, value_mw=5.0, lag_mw=1.0)
    at_cutoff = _row(hour=12, value_mw=7.0, lag_mw=2.0)
    later = _row(hour=14, value_mw=9.0, lag_mw=3.0)
    rows = (earlier, at_cutoff, later)
    cutoff = utc(hour=12)
    result = split_consumer_load_feature_rows_chronologically(rows=rows, cutoff=cutoff)
    assert isinstance(result, ConsumerLoadChronologicalFeatureSplit)
    assert result.training_rows == (earlier,)
    assert result.evaluation_rows == (at_cutoff, later)
    assert result.training_rows[0] is earlier
    assert result.evaluation_rows[0] is at_cutoff
    assert result.evaluation_rows[1] is later


def test_rows_before_cutoff_go_only_to_training() -> None:
    first = _row(hour=8, value_mw=1.0)
    second = _row(hour=9, value_mw=2.0)
    third = _row(hour=11, value_mw=3.0)
    result = split_consumer_load_feature_rows_chronologically(
        rows=(first, second, third),
        cutoff=utc(hour=10),
    )
    assert result.training_rows == (first, second)
    assert third not in result.training_rows
    assert first not in result.evaluation_rows
    assert second not in result.evaluation_rows


def test_row_equal_to_cutoff_goes_to_evaluation() -> None:
    before = _row(hour=10, value_mw=1.0)
    equal = _row(hour=12, value_mw=2.0)
    result = split_consumer_load_feature_rows_chronologically(
        rows=(before, equal),
        cutoff=utc(hour=12),
    )
    assert equal not in result.training_rows
    assert result.evaluation_rows == (equal,)
    assert result.evaluation_rows[0].target_timestamp == utc(hour=12)


def test_rows_after_cutoff_go_only_to_evaluation() -> None:
    first = _row(hour=8, value_mw=1.0)
    second = _row(hour=11, value_mw=2.0)
    third = _row(hour=13, value_mw=3.0)
    result = split_consumer_load_feature_rows_chronologically(
        rows=(first, second, third),
        cutoff=utc(hour=10),
    )
    assert result.evaluation_rows == (second, third)
    assert first not in result.evaluation_rows
    assert second not in result.training_rows
    assert third not in result.training_rows


def test_original_order_is_preserved() -> None:
    first = _row(hour=8, value_mw=1.0)
    second = _row(hour=9, value_mw=2.0)
    third = _row(hour=11, value_mw=3.0)
    fourth = _row(hour=13, value_mw=4.0)
    result = split_consumer_load_feature_rows_chronologically(
        rows=(first, second, third, fourth),
        cutoff=utc(hour=10),
    )
    assert result.training_rows == (first, second)
    assert result.evaluation_rows == (third, fourth)
    assert tuple(id(row) for row in result.training_rows) == (id(first), id(second))
    assert tuple(id(row) for row in result.evaluation_rows) == (id(third), id(fourth))


def test_function_does_not_sort_input() -> None:
    first = _row(hour=8, value_mw=1.0)
    second = _row(hour=9, value_mw=2.0)
    third = _row(hour=11, value_mw=3.0)
    rows = (first, second, third)
    original_ids = tuple(id(row) for row in rows)
    split_consumer_load_feature_rows_chronologically(rows=rows, cutoff=utc(hour=10))
    assert tuple(id(row) for row in rows) == original_ids
    assert rows == (first, second, third)


def test_empty_rows_fail_closed() -> None:
    with pytest.raises(InvalidRequestError, match=_EMPTY_ROWS_MESSAGE) as caught:
        split_consumer_load_feature_rows_chronologically(rows=(), cutoff=utc(hour=12))
    assert caught.value.code == "invalid_request"


def test_all_rows_in_evaluation_fails_closed() -> None:
    rows = (_row(hour=12, value_mw=1.0), _row(hour=14, value_mw=2.0))
    with pytest.raises(InvalidRequestError, match=_EMPTY_TRAINING_MESSAGE) as caught:
        split_consumer_load_feature_rows_chronologically(rows=rows, cutoff=utc(hour=12))
    assert caught.value.code == "invalid_request"


def test_all_rows_in_training_fails_closed() -> None:
    rows = (_row(hour=8, value_mw=1.0), _row(hour=9, value_mw=2.0))
    with pytest.raises(InvalidRequestError, match=_EMPTY_EVALUATION_MESSAGE) as caught:
        split_consumer_load_feature_rows_chronologically(rows=rows, cutoff=utc(hour=10))
    assert caught.value.code == "invalid_request"


def test_duplicate_timestamps_fail_closed() -> None:
    stamp = utc(hour=12)
    rows = (
        _row(hour=10, value_mw=1.0),
        ConsumerLoadLag24hFeatureRow(
            consumer_id="consumer-1",
            target_timestamp=stamp,
            lag_24h_mw=2.0,
            target_value_mw=3.0,
        ),
        ConsumerLoadLag24hFeatureRow(
            consumer_id="consumer-1",
            target_timestamp=stamp,
            lag_24h_mw=4.0,
            target_value_mw=5.0,
        ),
    )
    with pytest.raises(InvalidRequestError, match=_DUPLICATE_TIMESTAMP_MESSAGE) as caught:
        split_consumer_load_feature_rows_chronologically(rows=rows, cutoff=utc(hour=11))
    assert caught.value.code == "invalid_request"


def test_out_of_order_timestamps_fail_closed() -> None:
    rows = (_row(hour=14, value_mw=2.0), _row(hour=10, value_mw=1.0))
    with pytest.raises(InvalidRequestError, match=_OUT_OF_ORDER_MESSAGE) as caught:
        split_consumer_load_feature_rows_chronologically(rows=rows, cutoff=utc(hour=12))
    assert caught.value.code == "invalid_request"


def test_mixed_consumers_fail_closed_without_raw_ids() -> None:
    rows = (
        _row(hour=10, value_mw=1.0, consumer_id="consumer-1"),
        _row(hour=14, value_mw=2.0, consumer_id="consumer-2"),
    )
    with pytest.raises(InvalidRequestError, match=_MIXED_CONSUMER_MESSAGE) as caught:
        split_consumer_load_feature_rows_chronologically(rows=rows, cutoff=utc(hour=12))
    assert caught.value.code == "invalid_request"
    assert "consumer-1" not in caught.value.message
    assert "consumer-2" not in caught.value.message


def test_malformed_input_does_not_return_partial_result() -> None:
    valid_prefix = (_row(hour=8, value_mw=1.0), _row(hour=10, value_mw=2.0))
    mixed = (
        *valid_prefix,
        _row(hour=14, value_mw=3.0, consumer_id="other"),
    )
    with pytest.raises(InvalidRequestError, match=_MIXED_CONSUMER_MESSAGE):
        split_consumer_load_feature_rows_chronologically(rows=mixed, cutoff=utc(hour=9))


def test_caller_rows_are_not_mutated() -> None:
    first = _row(hour=8, value_mw=1.0, lag_mw=0.5)
    second = _row(hour=12, value_mw=2.0, lag_mw=1.5)
    rows = (first, second)
    original_ids = tuple(id(row) for row in rows)
    result = split_consumer_load_feature_rows_chronologically(
        rows=rows,
        cutoff=utc(hour=10),
    )
    assert rows == (first, second)
    assert tuple(id(row) for row in rows) == original_ids
    assert rows[0] is first
    assert rows[1] is second
    assert result.training_rows[0] is first
    assert result.evaluation_rows[0] is second


def test_repeated_equal_calls_produce_value_equal_results() -> None:
    rows = (_row(hour=8, value_mw=1.0), _row(hour=12, value_mw=2.0))
    cutoff = utc(hour=10)
    first = split_consumer_load_feature_rows_chronologically(rows=rows, cutoff=cutoff)
    second = split_consumer_load_feature_rows_chronologically(rows=rows, cutoff=cutoff)
    assert first == second
    assert first is not second


def test_result_is_frozen_slotted_with_exactly_two_fields() -> None:
    result = split_consumer_load_feature_rows_chronologically(
        rows=(_row(hour=8, value_mw=1.0), _row(hour=12, value_mw=2.0)),
        cutoff=utc(hour=10),
    )
    assert ConsumerLoadChronologicalFeatureSplit.__slots__ == _SPLIT_FIELDS
    with pytest.raises(AttributeError):
        result.training_rows = ()  # type: ignore[misc]
    assert not hasattr(result, "__dict__")


def test_result_contract_has_no_percentage_ratio_or_metadata_fields() -> None:
    result = split_consumer_load_feature_rows_chronologically(
        rows=(_row(hour=8, value_mw=1.0), _row(hour=12, value_mw=2.0)),
        cutoff=utc(hour=10),
    )
    forbidden_attrs = (
        "cutoff",
        "percentage",
        "ratio",
        "train_ratio",
        "test_ratio",
        "seed",
        "random_state",
        "consumer_id",
        "workflow_id",
        "dataset",
        "metadata",
        "features",
    )
    for name in forbidden_attrs:
        assert not hasattr(result, name)


def test_split_does_not_manipulate_mw_values() -> None:
    first = _row(hour=8, value_mw=5.25, lag_mw=1.125)
    second = _row(hour=12, value_mw=9.75, lag_mw=3.5)
    result = split_consumer_load_feature_rows_chronologically(
        rows=(first, second),
        cutoff=utc(hour=10),
    )
    assert result.training_rows[0].lag_24h_mw == 1.125
    assert result.training_rows[0].target_value_mw == 5.25
    assert result.evaluation_rows[0].lag_24h_mw == 3.5
    assert result.evaluation_rows[0].target_value_mw == 9.75
    assert result.training_rows[0].lag_24h_mw is first.lag_24h_mw
    assert result.training_rows[0].target_value_mw is first.target_value_mw


def test_boundary_uses_target_timestamp_not_mw_values() -> None:
    earlier = _row(hour=8, value_mw=90.0, lag_mw=80.0)
    later = _row(hour=14, value_mw=1.0, lag_mw=0.5)
    result = split_consumer_load_feature_rows_chronologically(
        rows=(earlier, later),
        cutoff=utc(hour=12),
    )
    assert result.training_rows == (earlier,)
    assert result.evaluation_rows == (later,)
    assert result.training_rows[0].target_value_mw > result.evaluation_rows[0].target_value_mw


def test_cutoff_one_minute_after_training_row_keeps_it_in_training() -> None:
    training_row = _row(hour=10, value_mw=1.0)
    evaluation_row = _row(hour=12, value_mw=2.0)
    cutoff = utc(hour=10) + timedelta(minutes=1)
    result = split_consumer_load_feature_rows_chronologically(
        rows=(training_row, evaluation_row),
        cutoff=cutoff,
    )
    assert result.training_rows == (training_row,)
    assert result.evaluation_rows == (evaluation_row,)
