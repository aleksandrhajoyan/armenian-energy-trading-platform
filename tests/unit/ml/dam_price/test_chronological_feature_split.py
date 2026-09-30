"""Chronological split of exact 24-hour lag DAM Price feature rows."""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from tests.unit.domain._factories import utc

from energy_trading.application.errors import InvalidRequestError
from energy_trading.ml.dam_price.chronological_feature_split import (
    DAMPriceChronologicalFeatureSplit,
    split_dam_price_feature_rows_chronologically,
)
from energy_trading.ml.dam_price.lag_24h_features import DAMPriceLag24hFeatureRow

_EMPTY_ROWS_MESSAGE = "DAM Price chronological feature split requires at least one feature row."
_MIXED_MARKET_MESSAGE = (
    "DAM Price chronological feature split requires rows from exactly one market."
)
_MIXED_CURRENCY_MESSAGE = (
    "DAM Price chronological feature split requires rows in exactly one currency."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "DAM Price chronological feature split requires unique target timestamps."
)
_OUT_OF_ORDER_MESSAGE = (
    "DAM Price chronological feature split requires strictly increasing target timestamps."
)
_EMPTY_TRAINING_MESSAGE = (
    "DAM Price chronological feature split requires a non-empty training partition."
)
_EMPTY_EVALUATION_MESSAGE = (
    "DAM Price chronological feature split requires a non-empty evaluation partition."
)


def _ts(day: int, hour: int = 16) -> datetime:
    return datetime(2026, 10, day, hour, 0, 0, tzinfo=UTC)


def _row(
    *,
    day: int,
    lag: str = "10.00",
    target: str = "20.00",
    market_id: str = "market-1",
    currency: str = "AMD",
) -> DAMPriceLag24hFeatureRow:
    return DAMPriceLag24hFeatureRow(
        market_id=market_id,
        currency=currency,
        target_timestamp=_ts(day),
        lag_24h_amount_per_mwh=Decimal(lag),
        target_amount_per_mwh=Decimal(target),
    )


def _split(
    rows: tuple[DAMPriceLag24hFeatureRow, ...],
    cutoff: datetime,
) -> DAMPriceChronologicalFeatureSplit:
    return split_dam_price_feature_rows_chronologically(rows=rows, cutoff=cutoff)


def test_normal_spanning_split_partitions_exactly() -> None:
    first = _row(day=1)
    second = _row(day=2)
    third = _row(day=3)
    fourth = _row(day=4)
    rows = (first, second, third, fourth)
    result = _split(rows, _ts(3))
    assert result.training_rows == (first, second)
    assert result.evaluation_rows == (third, fourth)
    assert len(result.training_rows) == 2
    assert len(result.evaluation_rows) == 2


def test_row_equal_to_cutoff_belongs_to_evaluation() -> None:
    before = _row(day=2)
    at_cutoff = _row(day=3)
    after = _row(day=4)
    result = _split((before, at_cutoff, after), _ts(3))
    assert result.training_rows == (before,)
    assert result.evaluation_rows == (at_cutoff, after)
    assert at_cutoff in result.evaluation_rows
    assert at_cutoff not in result.training_rows


def test_training_partition_preserves_input_order() -> None:
    first = _row(day=1)
    second = _row(day=2)
    third = _row(day=3)
    boundary = _row(day=4)
    result = _split((first, second, third, boundary), _ts(4))
    assert result.training_rows == (first, second, third)
    assert tuple(row.target_timestamp for row in result.training_rows) == (
        _ts(1),
        _ts(2),
        _ts(3),
    )


def test_evaluation_partition_preserves_input_order() -> None:
    boundary = _row(day=1)
    first = _row(day=5)
    second = _row(day=6)
    third = _row(day=7)
    result = _split((boundary, first, second, third), _ts(4))
    assert result.evaluation_rows == (first, second, third)
    assert tuple(row.target_timestamp for row in result.evaluation_rows) == (
        _ts(5),
        _ts(6),
        _ts(7),
    )


def test_original_row_objects_are_preserved_by_identity() -> None:
    first = _row(day=1)
    second = _row(day=2)
    third = _row(day=3)
    result = _split((first, second, third), _ts(3))
    assert result.training_rows[0] is first
    assert result.training_rows[1] is second
    assert result.evaluation_rows[0] is third


def test_feature_and_target_values_are_unchanged() -> None:
    row = _row(day=1, lag="0.01", target="1234.567")
    other = _row(day=5, lag="-7.25", target="88.009")
    result = _split((row, other), _ts(3))
    copied = result.training_rows[0]
    assert copied.lag_24h_amount_per_mwh == Decimal("0.01")
    assert copied.target_amount_per_mwh == Decimal("1234.567")
    assert isinstance(copied.lag_24h_amount_per_mwh, Decimal)
    assert isinstance(copied.target_amount_per_mwh, Decimal)
    assert result.evaluation_rows[0].lag_24h_amount_per_mwh == Decimal("-7.25")
    assert result.evaluation_rows[0].target_amount_per_mwh == Decimal("88.009")


def test_negative_feature_values_split_normally_without_clamping() -> None:
    training = _row(day=1, lag="-20.00", target="-5.00")
    evaluation = _row(day=5, lag="-30.00", target="-15.00")
    result = _split((training, evaluation), _ts(3))
    assert result.training_rows[0].lag_24h_amount_per_mwh == Decimal("-20.00")
    assert result.training_rows[0].target_amount_per_mwh == Decimal("-5.00")
    assert result.training_rows[0].target_amount_per_mwh < 0
    assert result.evaluation_rows[0].lag_24h_amount_per_mwh == Decimal("-30.00")
    assert result.evaluation_rows[0].lag_24h_amount_per_mwh < 0


def test_empty_rows_fail_closed() -> None:
    with pytest.raises(InvalidRequestError) as captured:
        _split((), _ts(3))
    assert captured.value.message == _EMPTY_ROWS_MESSAGE


def test_all_evaluation_fails_closed() -> None:
    rows = (_row(day=5), _row(day=6))
    with pytest.raises(InvalidRequestError) as captured:
        _split(rows, _ts(1))
    assert captured.value.message == _EMPTY_TRAINING_MESSAGE


def test_all_training_fails_closed() -> None:
    rows = (_row(day=1), _row(day=2))
    with pytest.raises(InvalidRequestError) as captured:
        _split(rows, _ts(9))
    assert captured.value.message == _EMPTY_EVALUATION_MESSAGE


def test_duplicate_target_timestamps_fail_closed() -> None:
    rows = (_row(day=2), _row(day=2, target="21.00"))
    with pytest.raises(InvalidRequestError) as captured:
        _split(rows, _ts(3))
    assert captured.value.message == _DUPLICATE_TIMESTAMP_MESSAGE


def test_out_of_order_timestamps_fail_closed() -> None:
    rows = (_row(day=6), _row(day=5))
    with pytest.raises(InvalidRequestError) as captured:
        _split(rows, _ts(3))
    assert captured.value.message == _OUT_OF_ORDER_MESSAGE


def test_out_of_order_input_is_not_silently_sorted() -> None:
    late = _row(day=6)
    early = _row(day=5)
    with pytest.raises(InvalidRequestError) as captured:
        _split((late, early), _ts(6))
    assert captured.value.message == _OUT_OF_ORDER_MESSAGE
    # The same rows in chronological order are accepted with the same cutoff,
    # proving the failure above was chronology, not another row property.
    accepted = _split((early, late), _ts(6))
    assert accepted.training_rows == (early,)
    assert accepted.evaluation_rows == (late,)


def test_mixed_markets_fail_closed_without_leaking_ids() -> None:
    rows = (
        _row(day=1, market_id="market-alpha"),
        _row(day=5, market_id="market-beta"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _split(rows, _ts(3))
    assert captured.value.message == _MIXED_MARKET_MESSAGE
    assert "market-alpha" not in captured.value.message
    assert "market-beta" not in captured.value.message


def test_mixed_currencies_fail_closed_without_leaking_codes() -> None:
    rows = (
        _row(day=1, currency="AMD"),
        _row(day=5, currency="EUR"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _split(rows, _ts(3))
    assert captured.value.message == _MIXED_CURRENCY_MESSAGE
    assert "AMD" not in captured.value.message
    assert "EUR" not in captured.value.message


def test_partition_depends_only_on_timestamp_relative_to_cutoff() -> None:
    # Deliberately descending price levels: if partitioning depended on any
    # amount rather than the timestamp, these rows would be misplaced.
    high = _row(day=1, lag="900.00", target="950.00")
    mid = _row(day=2, lag="500.00", target="450.00")
    low = _row(day=5, lag="1.00", target="2.00")
    result = _split((high, mid, low), _ts(3))
    assert result.training_rows == (high, mid)
    assert result.evaluation_rows == (low,)


def test_input_rows_are_not_mutated() -> None:
    first = _row(day=1)
    second = _row(day=5)
    rows = (first, second)
    _split(rows, _ts(3))
    assert rows == (first, second)
    assert first.target_timestamp == _ts(1)
    assert first.lag_24h_amount_per_mwh == Decimal("10.00")
    assert second.lag_24h_amount_per_mwh == Decimal("10.00")


def test_repeated_equal_calls_are_value_equivalent() -> None:
    rows = (_row(day=1), _row(day=5))
    assert _split(rows, _ts(3)) == _split(rows, _ts(3))


def test_result_contract_is_frozen_slotted_and_exactly_two_fields() -> None:
    names = tuple(item.name for item in fields(DAMPriceChronologicalFeatureSplit))
    assert names == ("training_rows", "evaluation_rows")
    assert DAMPriceChronologicalFeatureSplit.__slots__ == names
    result = _split((_row(day=1), _row(day=5)), _ts(3))
    with pytest.raises(FrozenInstanceError):
        result.training_rows = ()  # type: ignore[misc]


def test_result_exposes_no_metadata_fields() -> None:
    names = {item.name for item in fields(DAMPriceChronologicalFeatureSplit)}
    forbidden = {
        "cutoff",
        "ratio",
        "percentage",
        "training_count",
        "evaluation_count",
        "case_count",
        "model_name",
        "model_version",
        "market_id",
        "currency",
        "metadata",
    }
    assert forbidden.isdisjoint(names)
    assert len(names) == 2


def test_splitter_is_synchronous_and_keyword_only() -> None:
    assert not inspect.iscoroutinefunction(split_dam_price_feature_rows_chronologically)
    parameters = inspect.signature(split_dam_price_feature_rows_chronologically).parameters
    assert tuple(parameters) == ("rows", "cutoff")
    assert parameters["rows"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["cutoff"].kind is inspect.Parameter.KEYWORD_ONLY


def test_split_uses_the_supplied_cutoff_only() -> None:
    rows = (_row(day=1), _row(day=3), _row(day=5))
    early = _split(rows, _ts(2))
    late = _split(rows, _ts(4))
    assert early.training_rows == (rows[0],)
    assert early.evaluation_rows == (rows[1], rows[2])
    assert late.training_rows == (rows[0], rows[1])
    assert late.evaluation_rows == (rows[2],)
    assert utc(hour=16) == _ts(1, hour=16)
