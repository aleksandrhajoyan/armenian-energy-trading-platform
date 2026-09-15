"""Chronological Consumer Load 24h+168h feature-row train/evaluation split."""

from __future__ import annotations

import pytest

from energy_trading.application.errors import InvalidRequestError
from energy_trading.ml.consumer_load.lag_24h_168h_chronological_split import (
    ConsumerLoadLag24h168hChronologicalFeatureSplit,
    split_consumer_load_lag_24h_168h_feature_rows_chronologically,
)
from energy_trading.ml.consumer_load.lag_24h_168h_features import (
    ConsumerLoadLag24h168hFeatureRow,
)
from tests.unit.domain._factories import utc

_EMPTY_ROWS_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag chronological feature split "
    "requires at least one feature row."
)
_MIXED_CONSUMER_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag chronological feature split "
    "requires rows from exactly one consumer."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag chronological feature split "
    "requires unique target timestamps."
)
_OUT_OF_ORDER_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag chronological feature split "
    "requires strictly increasing target timestamps."
)
_EMPTY_TRAINING_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag chronological feature split "
    "requires a non-empty training partition."
)
_EMPTY_EVALUATION_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag chronological feature split "
    "requires a non-empty evaluation partition."
)
_SPLIT_FIELDS = (
    "training_rows",
    "evaluation_rows",
)


def _row(
    *,
    hour: int,
    day: int = 15,
    lag_24h_mw: float = 4.0,
    lag_168h_mw: float = 2.0,
    target_value_mw: float = 8.0,
    consumer_id: str = "consumer-1",
) -> ConsumerLoadLag24h168hFeatureRow:
    return ConsumerLoadLag24h168hFeatureRow(
        consumer_id=consumer_id,
        target_timestamp=utc(day=day, hour=hour),
        lag_24h_mw=lag_24h_mw,
        lag_168h_mw=lag_168h_mw,
        target_value_mw=target_value_mw,
    )


def test_rows_before_cutoff_go_to_training_and_at_or_after_go_to_evaluation() -> None:
    earlier = _row(hour=10, lag_24h_mw=1.0, lag_168h_mw=0.5, target_value_mw=5.0)
    at_cutoff = _row(hour=12, lag_24h_mw=2.0, lag_168h_mw=1.0, target_value_mw=7.0)
    later = _row(hour=14, lag_24h_mw=3.0, lag_168h_mw=1.5, target_value_mw=9.0)
    rows = (earlier, at_cutoff, later)
    result = split_consumer_load_lag_24h_168h_feature_rows_chronologically(
        rows=rows,
        cutoff=utc(day=15, hour=12),
    )
    assert isinstance(result, ConsumerLoadLag24h168hChronologicalFeatureSplit)
    assert result.training_rows == (earlier,)
    assert result.evaluation_rows == (at_cutoff, later)
    assert result.training_rows[0] is earlier
    assert result.evaluation_rows[0] is at_cutoff
    assert result.evaluation_rows[1] is later


def test_row_exactly_equal_to_cutoff_is_evaluation() -> None:
    before = _row(hour=10, target_value_mw=1.0)
    equal = _row(hour=12, target_value_mw=2.0)
    result = split_consumer_load_lag_24h_168h_feature_rows_chronologically(
        rows=(before, equal),
        cutoff=utc(day=15, hour=12),
    )
    assert equal not in result.training_rows
    assert result.evaluation_rows == (equal,)
    assert result.evaluation_rows[0].target_timestamp == utc(day=15, hour=12)


def test_training_order_is_preserved() -> None:
    first = _row(hour=8, target_value_mw=1.0)
    second = _row(hour=9, target_value_mw=2.0)
    third = _row(hour=11, target_value_mw=3.0)
    fourth = _row(hour=13, target_value_mw=4.0)
    result = split_consumer_load_lag_24h_168h_feature_rows_chronologically(
        rows=(first, second, third, fourth),
        cutoff=utc(day=15, hour=10),
    )
    assert result.training_rows == (first, second)
    assert tuple(id(row) for row in result.training_rows) == (id(first), id(second))


def test_evaluation_order_is_preserved() -> None:
    first = _row(hour=8, target_value_mw=1.0)
    second = _row(hour=9, target_value_mw=2.0)
    third = _row(hour=11, target_value_mw=3.0)
    fourth = _row(hour=13, target_value_mw=4.0)
    result = split_consumer_load_lag_24h_168h_feature_rows_chronologically(
        rows=(first, second, third, fourth),
        cutoff=utc(day=15, hour=10),
    )
    assert result.evaluation_rows == (third, fourth)
    assert tuple(id(row) for row in result.evaluation_rows) == (id(third), id(fourth))


def test_result_is_frozen_slotted_with_exactly_two_fields() -> None:
    result = split_consumer_load_lag_24h_168h_feature_rows_chronologically(
        rows=(_row(hour=8), _row(hour=12)),
        cutoff=utc(day=15, hour=10),
    )
    assert ConsumerLoadLag24h168hChronologicalFeatureSplit.__slots__ == _SPLIT_FIELDS
    with pytest.raises(AttributeError):
        result.training_rows = ()  # type: ignore[misc]
    assert not hasattr(result, "__dict__")
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
        "validation_rows",
        "holdout_ratio",
    )
    for name in forbidden_attrs:
        assert not hasattr(result, name)


def test_empty_rows_fail_closed() -> None:
    with pytest.raises(InvalidRequestError, match=_EMPTY_ROWS_MESSAGE) as caught:
        split_consumer_load_lag_24h_168h_feature_rows_chronologically(
            rows=(),
            cutoff=utc(day=15, hour=12),
        )
    assert caught.value.code == "invalid_request"


def test_mixed_consumers_fail_closed_without_raw_ids() -> None:
    rows = (
        _row(hour=10, consumer_id="consumer-1"),
        _row(hour=14, consumer_id="consumer-2"),
    )
    with pytest.raises(InvalidRequestError, match=_MIXED_CONSUMER_MESSAGE) as caught:
        split_consumer_load_lag_24h_168h_feature_rows_chronologically(
            rows=rows,
            cutoff=utc(day=15, hour=12),
        )
    assert caught.value.code == "invalid_request"
    assert "consumer-1" not in caught.value.message
    assert "consumer-2" not in caught.value.message


def test_duplicate_timestamps_fail_closed() -> None:
    stamp = utc(day=15, hour=12)
    rows = (
        _row(hour=10, target_value_mw=1.0),
        ConsumerLoadLag24h168hFeatureRow(
            consumer_id="consumer-1",
            target_timestamp=stamp,
            lag_24h_mw=2.0,
            lag_168h_mw=1.0,
            target_value_mw=3.0,
        ),
        ConsumerLoadLag24h168hFeatureRow(
            consumer_id="consumer-1",
            target_timestamp=stamp,
            lag_24h_mw=4.0,
            lag_168h_mw=2.0,
            target_value_mw=5.0,
        ),
    )
    with pytest.raises(InvalidRequestError, match=_DUPLICATE_TIMESTAMP_MESSAGE) as caught:
        split_consumer_load_lag_24h_168h_feature_rows_chronologically(
            rows=rows,
            cutoff=utc(day=15, hour=11),
        )
    assert caught.value.code == "invalid_request"


def test_decreasing_out_of_order_rows_fail_closed() -> None:
    rows = (_row(hour=14, target_value_mw=2.0), _row(hour=10, target_value_mw=1.0))
    with pytest.raises(InvalidRequestError, match=_OUT_OF_ORDER_MESSAGE) as caught:
        split_consumer_load_lag_24h_168h_feature_rows_chronologically(
            rows=rows,
            cutoff=utc(day=15, hour=12),
        )
    assert caught.value.code == "invalid_request"


def test_cutoff_at_or_before_first_row_fails_closed_with_empty_training() -> None:
    rows = (_row(hour=12, target_value_mw=1.0), _row(hour=14, target_value_mw=2.0))
    with pytest.raises(InvalidRequestError, match=_EMPTY_TRAINING_MESSAGE) as caught:
        split_consumer_load_lag_24h_168h_feature_rows_chronologically(
            rows=rows,
            cutoff=utc(day=15, hour=12),
        )
    assert caught.value.code == "invalid_request"


def test_cutoff_after_last_row_fails_closed_with_empty_evaluation() -> None:
    rows = (_row(hour=8, target_value_mw=1.0), _row(hour=9, target_value_mw=2.0))
    with pytest.raises(InvalidRequestError, match=_EMPTY_EVALUATION_MESSAGE) as caught:
        split_consumer_load_lag_24h_168h_feature_rows_chronologically(
            rows=rows,
            cutoff=utc(day=15, hour=10),
        )
    assert caught.value.code == "invalid_request"


def test_single_row_cannot_form_both_partitions() -> None:
    only = _row(hour=12, target_value_mw=1.0)
    with pytest.raises(InvalidRequestError, match=_EMPTY_TRAINING_MESSAGE):
        split_consumer_load_lag_24h_168h_feature_rows_chronologically(
            rows=(only,),
            cutoff=utc(day=15, hour=12),
        )
    with pytest.raises(InvalidRequestError, match=_EMPTY_EVALUATION_MESSAGE):
        split_consumer_load_lag_24h_168h_feature_rows_chronologically(
            rows=(only,),
            cutoff=utc(day=15, hour=13),
        )


def test_two_row_minimal_valid_split() -> None:
    first = _row(hour=8, lag_24h_mw=1.25, lag_168h_mw=0.75, target_value_mw=5.25)
    second = _row(hour=12, lag_24h_mw=3.5, lag_168h_mw=2.25, target_value_mw=9.75)
    result = split_consumer_load_lag_24h_168h_feature_rows_chronologically(
        rows=(first, second),
        cutoff=utc(day=15, hour=10),
    )
    assert result.training_rows == (first,)
    assert result.evaluation_rows == (second,)
    assert result.training_rows[0] is first
    assert result.evaluation_rows[0] is second


def test_caller_rows_and_objects_are_not_mutated() -> None:
    first = _row(hour=8, lag_24h_mw=0.5, lag_168h_mw=0.25, target_value_mw=1.0)
    second = _row(hour=12, lag_24h_mw=1.5, lag_168h_mw=0.75, target_value_mw=2.0)
    rows = (first, second)
    original_ids = tuple(id(row) for row in rows)
    result = split_consumer_load_lag_24h_168h_feature_rows_chronologically(
        rows=rows,
        cutoff=utc(day=15, hour=10),
    )
    assert rows == (first, second)
    assert tuple(id(row) for row in rows) == original_ids
    assert rows[0] is first
    assert rows[1] is second
    assert result.training_rows[0] is first
    assert result.evaluation_rows[0] is second


def test_repeated_equal_input_returns_value_equivalent_split() -> None:
    rows = (_row(hour=8), _row(hour=12))
    cutoff = utc(day=15, hour=10)
    first = split_consumer_load_lag_24h_168h_feature_rows_chronologically(
        rows=rows,
        cutoff=cutoff,
    )
    second = split_consumer_load_lag_24h_168h_feature_rows_chronologically(
        rows=rows,
        cutoff=cutoff,
    )
    assert first == second
    assert first is not second


def test_only_timestamps_determine_partition_not_feature_values() -> None:
    earlier = _row(hour=8, lag_24h_mw=90.0, lag_168h_mw=80.0, target_value_mw=70.0)
    later = _row(hour=14, lag_24h_mw=0.5, lag_168h_mw=0.25, target_value_mw=1.0)
    result = split_consumer_load_lag_24h_168h_feature_rows_chronologically(
        rows=(earlier, later),
        cutoff=utc(day=15, hour=12),
    )
    assert result.training_rows == (earlier,)
    assert result.evaluation_rows == (later,)
    assert result.training_rows[0].lag_24h_mw == 90.0
    assert result.training_rows[0].lag_168h_mw == 80.0
    assert result.training_rows[0].target_value_mw == 70.0
    assert result.evaluation_rows[0].lag_24h_mw == 0.5
    assert result.evaluation_rows[0].lag_168h_mw == 0.25
    assert result.evaluation_rows[0].target_value_mw == 1.0
    assert result.training_rows[0].target_value_mw > result.evaluation_rows[0].target_value_mw
    assert result.training_rows[0].lag_24h_mw is earlier.lag_24h_mw
    assert result.training_rows[0].lag_168h_mw is earlier.lag_168h_mw
    assert result.training_rows[0].target_value_mw is earlier.target_value_mw


def test_return_contract_is_concrete_split_of_chunk_141_rows() -> None:
    first = _row(hour=8)
    second = _row(hour=12)
    result = split_consumer_load_lag_24h_168h_feature_rows_chronologically(
        rows=(first, second),
        cutoff=utc(day=15, hour=10),
    )
    assert type(result) is ConsumerLoadLag24h168hChronologicalFeatureSplit
    assert type(result.training_rows) is tuple
    assert type(result.evaluation_rows) is tuple
    assert all(type(row) is ConsumerLoadLag24h168hFeatureRow for row in result.training_rows)
    assert all(type(row) is ConsumerLoadLag24h168hFeatureRow for row in result.evaluation_rows)


def test_malformed_out_of_order_input_fails_rather_than_sorting() -> None:
    later = _row(hour=14, target_value_mw=2.0)
    earlier = _row(hour=10, target_value_mw=1.0)
    rows = (later, earlier)
    with pytest.raises(InvalidRequestError, match=_OUT_OF_ORDER_MESSAGE):
        split_consumer_load_lag_24h_168h_feature_rows_chronologically(
            rows=rows,
            cutoff=utc(day=15, hour=12),
        )
    assert rows == (later, earlier)
