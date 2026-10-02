"""Chronological split of exact 24-hour plus 168-hour lag DAM Price feature rows."""

from __future__ import annotations

import inspect
import typing
from dataclasses import MISSING, FrozenInstanceError, fields
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from energy_trading.application.errors import InvalidRequestError

# ``energy_trading.domain.models`` must initialize before
# ``energy_trading.domain.value_objects`` because the domain models package
# imports ``EnergyPrice`` from it during its own initialization. Importing the
# models package explicitly keeps that pre-existing order; the splitter itself
# does not consume ``MarketPriceRecord``.
from energy_trading.domain.models.observations import MarketPriceRecord  # noqa: F401
from energy_trading.ml.dam_price import lag_24h_168h_chronological_feature_split as split_module
from energy_trading.ml.dam_price import lag_24h_168h_features
from energy_trading.ml.dam_price.chronological_feature_split import (
    DAMPriceChronologicalFeatureSplit,
)
from energy_trading.ml.dam_price.lag_24h_168h_chronological_feature_split import (
    DAMPriceLag24h168hChronologicalFeatureSplit,
    split_dam_price_lag_24h_168h_feature_rows_chronologically,
)
from energy_trading.ml.dam_price.lag_24h_168h_features import DAMPriceLag24h168hFeatureRow

_PREFIX = "DAM Price 24h+168h chronological feature split requires"
_EMPTY_ROWS_MESSAGE = f"{_PREFIX} at least one feature row."
_MIXED_MARKET_MESSAGE = f"{_PREFIX} rows from exactly one market."
_MIXED_CURRENCY_MESSAGE = f"{_PREFIX} rows in exactly one currency."
_DUPLICATE_TIMESTAMP_MESSAGE = f"{_PREFIX} unique target timestamps."
_OUT_OF_ORDER_MESSAGE = f"{_PREFIX} strictly increasing target timestamps."
_EMPTY_TRAINING_MESSAGE = f"{_PREFIX} a non-empty training partition."
_EMPTY_EVALUATION_MESSAGE = f"{_PREFIX} a non-empty evaluation partition."


def _ts(day: int, hour: int = 16) -> datetime:
    return datetime(2026, 10, day, hour, 0, 0, tzinfo=UTC)


def _row(
    *,
    day: int,
    lag_24h: str = "10.00",
    lag_168h: str = "12.00",
    target: str = "20.00",
    market_id: str = "market-1",
    currency: str = "AMD",
) -> DAMPriceLag24h168hFeatureRow:
    return DAMPriceLag24h168hFeatureRow(
        market_id=market_id,
        currency=currency,
        target_timestamp=_ts(day),
        lag_24h_amount_per_mwh=Decimal(lag_24h),
        lag_168h_amount_per_mwh=Decimal(lag_168h),
        target_amount_per_mwh=Decimal(target),
    )


def _split(
    rows: tuple[DAMPriceLag24h168hFeatureRow, ...],
    cutoff: datetime,
) -> DAMPriceLag24h168hChronologicalFeatureSplit:
    return split_dam_price_lag_24h_168h_feature_rows_chronologically(rows=rows, cutoff=cutoff)


def _fail(rows: tuple[DAMPriceLag24h168hFeatureRow, ...], cutoff: datetime) -> str:
    with pytest.raises(InvalidRequestError) as captured:
        _split(rows, cutoff)
    return captured.value.message


def test_normal_valid_split_partitions_exactly() -> None:
    first, second, third, fourth = (_row(day=day) for day in (1, 2, 3, 4))
    result = _split((first, second, third, fourth), _ts(3))
    assert isinstance(result, DAMPriceLag24h168hChronologicalFeatureSplit)
    assert result.training_rows == (first, second)
    assert result.evaluation_rows == (third, fourth)


def test_training_rows_are_exactly_strictly_before_cutoff() -> None:
    rows = tuple(_row(day=day) for day in (1, 2, 3, 4, 5))
    cutoff = _ts(3)
    result = _split(rows, cutoff)
    assert result.training_rows == tuple(row for row in rows if row.target_timestamp < cutoff)
    assert all(row.target_timestamp < cutoff for row in result.training_rows)


def test_evaluation_rows_are_exactly_at_or_after_cutoff() -> None:
    rows = tuple(_row(day=day) for day in (1, 2, 3, 4, 5))
    cutoff = _ts(3)
    result = _split(rows, cutoff)
    assert result.evaluation_rows == tuple(row for row in rows if row.target_timestamp >= cutoff)
    assert all(row.target_timestamp >= cutoff for row in result.evaluation_rows)


def test_row_equal_to_cutoff_belongs_to_evaluation() -> None:
    before = _row(day=2)
    at_cutoff = _row(day=3)
    after = _row(day=4)
    result = _split((before, at_cutoff, after), _ts(3))
    assert result.training_rows == (before,)
    assert result.evaluation_rows == (at_cutoff, after)
    assert all(row is not at_cutoff for row in result.training_rows)


def test_training_partition_preserves_input_order() -> None:
    first, second, third, boundary = (_row(day=day) for day in (1, 2, 3, 4))
    result = _split((first, second, third, boundary), _ts(4))
    assert tuple(row.target_timestamp for row in result.training_rows) == (
        _ts(1),
        _ts(2),
        _ts(3),
    )


def test_evaluation_partition_preserves_input_order() -> None:
    boundary, first, second, third = (_row(day=day) for day in (1, 5, 6, 7))
    result = _split((boundary, first, second, third), _ts(4))
    assert tuple(row.target_timestamp for row in result.evaluation_rows) == (
        _ts(5),
        _ts(6),
        _ts(7),
    )


def test_original_row_objects_are_preserved_by_identity() -> None:
    first, second, third = (_row(day=day) for day in (1, 2, 3))
    result = _split((first, second, third), _ts(3))
    assert result.training_rows[0] is first
    assert result.training_rows[1] is second
    assert result.evaluation_rows[0] is third


def test_canonical_decimal_values_are_unchanged() -> None:
    training = _row(day=1, lag_24h="0.01", lag_168h="99.999", target="1234.567")
    evaluation = _row(day=5, lag_24h="7.25", lag_168h="0", target="88.009")
    result = _split((training, evaluation), _ts(3))
    for row in (*result.training_rows, *result.evaluation_rows):
        assert isinstance(row.lag_24h_amount_per_mwh, Decimal)
        assert isinstance(row.lag_168h_amount_per_mwh, Decimal)
        assert isinstance(row.target_amount_per_mwh, Decimal)
    assert result.evaluation_rows[0].lag_168h_amount_per_mwh == Decimal("0")


def test_lag_24h_value_is_unchanged() -> None:
    result = _split((_row(day=1, lag_24h="0.01"), _row(day=5, lag_24h="7.25")), _ts(3))
    assert str(result.training_rows[0].lag_24h_amount_per_mwh) == "0.01"
    assert str(result.evaluation_rows[0].lag_24h_amount_per_mwh) == "7.25"


def test_lag_168h_value_is_unchanged() -> None:
    result = _split((_row(day=1, lag_168h="99.999"), _row(day=5, lag_168h="3.10")), _ts(3))
    assert str(result.training_rows[0].lag_168h_amount_per_mwh) == "99.999"
    assert str(result.evaluation_rows[0].lag_168h_amount_per_mwh) == "3.10"


def test_target_value_is_unchanged() -> None:
    result = _split((_row(day=1, target="1234.567"), _row(day=5, target="88.009")), _ts(3))
    assert str(result.training_rows[0].target_amount_per_mwh) == "1234.567"
    assert str(result.evaluation_rows[0].target_amount_per_mwh) == "88.009"


def test_negative_lag_24h_is_accepted_normally() -> None:
    result = _split((_row(day=1, lag_24h="-20.00"), _row(day=5, lag_24h="-30.00")), _ts(3))
    assert result.training_rows[0].lag_24h_amount_per_mwh == Decimal("-20.00")
    assert result.evaluation_rows[0].lag_24h_amount_per_mwh == Decimal("-30.00")


def test_negative_lag_168h_is_accepted_normally() -> None:
    result = _split((_row(day=1, lag_168h="-40.00"), _row(day=5, lag_168h="-50.00")), _ts(3))
    assert result.training_rows[0].lag_168h_amount_per_mwh == Decimal("-40.00")
    assert result.evaluation_rows[0].lag_168h_amount_per_mwh == Decimal("-50.00")


def test_negative_target_is_accepted_normally() -> None:
    result = _split((_row(day=1, target="-5.00"), _row(day=5, target="-15.00")), _ts(3))
    assert result.training_rows[0].target_amount_per_mwh == Decimal("-5.00")
    assert result.evaluation_rows[0].target_amount_per_mwh == Decimal("-15.00")


def test_values_do_not_influence_partition_membership() -> None:
    # Deliberately descending price levels: if partitioning depended on any
    # amount rather than the timestamp, these rows would be misplaced.
    high = _row(day=1, lag_24h="900.00", lag_168h="950.00", target="990.00")
    mid = _row(day=2, lag_24h="500.00", lag_168h="-450.00", target="450.00")
    low = _row(day=5, lag_24h="-1.00", lag_168h="1.00", target="2.00")
    result = _split((high, mid, low), _ts(3))
    assert result.training_rows == (high, mid)
    assert result.evaluation_rows == (low,)
    swapped = (
        _row(day=1, lag_24h="-1.00", lag_168h="1.00", target="2.00"),
        _row(day=2, lag_24h="-1.00", lag_168h="1.00", target="2.00"),
        _row(day=5, lag_24h="900.00", lag_168h="950.00", target="990.00"),
    )
    swapped_result = _split(swapped, _ts(3))
    assert len(swapped_result.training_rows) == 2
    assert len(swapped_result.evaluation_rows) == 1


def test_empty_rows_fail_closed() -> None:
    assert _fail((), _ts(3)) == _EMPTY_ROWS_MESSAGE


def test_cutoff_at_first_row_fails_with_empty_training() -> None:
    rows = (_row(day=5), _row(day=6))
    assert _fail(rows, _ts(5)) == _EMPTY_TRAINING_MESSAGE


def test_cutoff_before_first_row_fails_with_empty_training() -> None:
    rows = (_row(day=5), _row(day=6))
    assert _fail(rows, _ts(1)) == _EMPTY_TRAINING_MESSAGE


def test_cutoff_after_last_row_fails_with_empty_evaluation() -> None:
    rows = (_row(day=1), _row(day=2))
    assert _fail(rows, _ts(9)) == _EMPTY_EVALUATION_MESSAGE


def test_one_row_cannot_create_both_partitions() -> None:
    row = (_row(day=5),)
    assert _fail(row, _ts(1)) == _EMPTY_TRAINING_MESSAGE
    assert _fail(row, _ts(5)) == _EMPTY_TRAINING_MESSAGE
    assert _fail(row, _ts(9)) == _EMPTY_EVALUATION_MESSAGE


def test_minimal_two_row_split_succeeds() -> None:
    first = _row(day=1)
    second = _row(day=2)
    result = _split((first, second), _ts(2))
    assert result.training_rows == (first,)
    assert result.evaluation_rows == (second,)


def test_duplicate_target_timestamps_fail_closed() -> None:
    rows = (_row(day=1), _row(day=2), _row(day=2, target="21.00"))
    assert _fail(rows, _ts(2)) == _DUPLICATE_TIMESTAMP_MESSAGE


def test_out_of_order_rows_fail_closed() -> None:
    rows = (_row(day=1), _row(day=6), _row(day=5))
    assert _fail(rows, _ts(3)) == _OUT_OF_ORDER_MESSAGE


def test_same_rows_in_chronological_order_succeed() -> None:
    early = _row(day=5)
    late = _row(day=6)
    result = _split((early, late), _ts(6))
    assert result.training_rows == (early,)
    assert result.evaluation_rows == (late,)


def test_malformed_rows_are_not_sorted_automatically() -> None:
    late = _row(day=6)
    early = _row(day=5)
    # The same rows in chronological order are accepted with the same cutoff
    # (see the test above), so this failure is chronology, not another row
    # property.
    assert _fail((late, early), _ts(6)) == _OUT_OF_ORDER_MESSAGE


def test_mixed_markets_fail_closed() -> None:
    rows = (_row(day=1, market_id="market-alpha"), _row(day=5, market_id="market-beta"))
    assert _fail(rows, _ts(3)) == _MIXED_MARKET_MESSAGE


def test_mixed_market_message_leaks_no_market_id() -> None:
    rows = (_row(day=1, market_id="market-alpha"), _row(day=5, market_id="market-beta"))
    message = _fail(rows, _ts(3))
    assert "market-alpha" not in message
    assert "market-beta" not in message


def test_mixed_currencies_fail_closed() -> None:
    rows = (_row(day=1, currency="AMD"), _row(day=5, currency="EUR"))
    assert _fail(rows, _ts(3)) == _MIXED_CURRENCY_MESSAGE


def test_mixed_currency_message_leaks_no_currency_code() -> None:
    rows = (_row(day=1, currency="AMD"), _row(day=5, currency="EUR"))
    message = _fail(rows, _ts(3))
    assert "AMD" not in message
    assert "EUR" not in message


def test_input_tuple_is_not_mutated() -> None:
    first = _row(day=1)
    second = _row(day=5)
    rows = (first, second)
    _split(rows, _ts(3))
    assert rows == (first, second)
    assert rows[0] is first
    assert rows[1] is second


def test_row_objects_are_not_mutated() -> None:
    first = _row(day=1, lag_24h="-1.50", lag_168h="2.25", target="3.75")
    before = (
        first.market_id,
        first.currency,
        first.target_timestamp,
        first.lag_24h_amount_per_mwh,
        first.lag_168h_amount_per_mwh,
        first.target_amount_per_mwh,
    )
    _split((first, _row(day=5)), _ts(3))
    after = (
        first.market_id,
        first.currency,
        first.target_timestamp,
        first.lag_24h_amount_per_mwh,
        first.lag_168h_amount_per_mwh,
        first.target_amount_per_mwh,
    )
    assert before == after


def test_repeated_equal_calls_are_value_equivalent() -> None:
    rows = (_row(day=1), _row(day=3), _row(day=5))
    assert _split(rows, _ts(3)) == _split(rows, _ts(3))


def test_result_is_frozen() -> None:
    result = _split((_row(day=1), _row(day=5)), _ts(3))
    with pytest.raises(FrozenInstanceError):
        result.training_rows = ()  # type: ignore[misc]


def test_result_is_slotted() -> None:
    assert DAMPriceLag24h168hChronologicalFeatureSplit.__slots__ == (
        "training_rows",
        "evaluation_rows",
    )
    result = _split((_row(day=1), _row(day=5)), _ts(3))
    assert not hasattr(result, "__dict__")


def test_result_has_exactly_two_fields() -> None:
    names = tuple(item.name for item in fields(DAMPriceLag24h168hChronologicalFeatureSplit))
    assert names == ("training_rows", "evaluation_rows")


def test_result_fields_have_no_defaults() -> None:
    for item in fields(DAMPriceLag24h168hChronologicalFeatureSplit):
        assert item.default is MISSING
        assert item.default_factory is MISSING


def test_result_fields_are_exact_two_lag_row_tuples() -> None:
    hints = typing.get_type_hints(DAMPriceLag24h168hChronologicalFeatureSplit)
    expected = tuple[DAMPriceLag24h168hFeatureRow, ...]
    assert hints == {"training_rows": expected, "evaluation_rows": expected}
    assert DAMPriceLag24h168hChronologicalFeatureSplit is not DAMPriceChronologicalFeatureSplit


def test_splitter_is_synchronous() -> None:
    assert not inspect.iscoroutinefunction(
        split_dam_price_lag_24h_168h_feature_rows_chronologically
    )


def test_splitter_is_keyword_only() -> None:
    parameters = inspect.signature(
        split_dam_price_lag_24h_168h_feature_rows_chronologically
    ).parameters
    assert tuple(parameters) == ("rows", "cutoff")
    for parameter in parameters.values():
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    rows = (_row(day=1), _row(day=5))
    with pytest.raises(TypeError):
        split_dam_price_lag_24h_168h_feature_rows_chronologically(rows, _ts(3))  # type: ignore[misc]


def test_cutoff_is_required() -> None:
    parameters = inspect.signature(
        split_dam_price_lag_24h_168h_feature_rows_chronologically
    ).parameters
    assert parameters["cutoff"].default is inspect.Parameter.empty
    assert parameters["rows"].default is inspect.Parameter.empty
    with pytest.raises(TypeError):
        split_dam_price_lag_24h_168h_feature_rows_chronologically(  # type: ignore[call-arg]
            rows=(_row(day=1), _row(day=5))
        )


def test_different_cutoffs_produce_different_partitions() -> None:
    rows = (_row(day=1), _row(day=3), _row(day=5))
    early = _split(rows, _ts(2))
    late = _split(rows, _ts(4))
    assert early.training_rows == (rows[0],)
    assert early.evaluation_rows == (rows[1], rows[2])
    assert late.training_rows == (rows[0], rows[1])
    assert late.evaluation_rows == (rows[2],)
    assert early != late


def test_feature_builder_is_not_called(monkeypatch: pytest.MonkeyPatch) -> None:
    def _forbidden(**_: object) -> object:
        msg = "two-lag feature builder must not be called by the splitter"
        raise AssertionError(msg)

    monkeypatch.setattr(
        lag_24h_168h_features, "build_dam_price_lag_24h_168h_feature_rows", _forbidden
    )
    assert not hasattr(split_module, "build_dam_price_lag_24h_168h_feature_rows")
    result = _split((_row(day=1), _row(day=5)), _ts(3))
    assert len(result.training_rows) == 1
    assert len(result.evaluation_rows) == 1
