"""Exact 24-hour and 168-hour lag DAM Price supervised feature rows."""

from __future__ import annotations

import inspect
from dataclasses import MISSING, FrozenInstanceError, fields
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from energy_trading.application.errors import InvalidRequestError

# ``energy_trading.domain.models`` must initialize before
# ``energy_trading.domain.value_objects.money`` because the domain models
# package imports ``EnergyPrice`` from it during its own initialization.
# Importing the models package explicitly keeps that pre-existing order.
from energy_trading.domain.models.observations import MarketPriceRecord  # noqa: F401
from energy_trading.domain.value_objects.money import EnergyPrice
from energy_trading.ml.dam_price.lag_24h_168h_features import (
    DAMPriceLag24h168hFeatureRow,
    build_dam_price_lag_24h_168h_feature_rows,
)

_MIXED_MARKET_MESSAGE = (
    "DAM Price 24-hour and 168-hour lag features require history from exactly one market."
)
_MIXED_CURRENCY_MESSAGE = (
    "DAM Price 24-hour and 168-hour lag features require history in exactly one currency."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "DAM Price 24-hour and 168-hour lag features require unique historical timestamps."
)

SIX_FIELDS = (
    "market_id",
    "currency",
    "target_timestamp",
    "lag_24h_amount_per_mwh",
    "lag_168h_amount_per_mwh",
    "target_amount_per_mwh",
)

_LAG_24H = timedelta(hours=24)
_LAG_168H = timedelta(hours=168)


def _ts(day: int, hour: int = 16) -> datetime:
    return datetime(2026, 10, day, hour, 0, 0, tzinfo=UTC)


def _price(amount: str, *, currency: str = "AMD") -> EnergyPrice:
    return EnergyPrice(amount_per_mwh=Decimal(amount), currency=currency)


def _market(
    *,
    timestamp: datetime,
    market_id: str = "market-1",
    price: EnergyPrice | None = None,
    volume_mwh: str | None = None,
) -> MarketPriceRecord:
    values: dict[str, object] = {
        "market_id": market_id,
        "timestamp": timestamp,
        "price": price if price is not None else _price("12.50"),
    }
    if volume_mwh is not None:
        values["volume_mwh"] = Decimal(volume_mwh)
    return MarketPriceRecord(**values)  # type: ignore[arg-type]


def _build(
    history: tuple[MarketPriceRecord, ...],
) -> tuple[DAMPriceLag24h168hFeatureRow, ...]:
    return build_dam_price_lag_24h_168h_feature_rows(history=history)


def test_empty_history_returns_empty_tuple() -> None:
    result = _build(())
    assert result == ()
    assert isinstance(result, tuple)


def test_insufficient_history_returns_empty_tuple() -> None:
    target = _ts(8)
    history = (_market(timestamp=target - _LAG_24H),)
    assert _build(history) == ()


def test_one_exact_triple_produces_exactly_one_row() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_168H, price=_price("41.00")),
        _market(timestamp=target - _LAG_24H, price=_price("45.00")),
        _market(timestamp=target, price=_price("52.50")),
    )
    result = _build(history)
    assert len(result) == 1
    assert isinstance(result[0], DAMPriceLag24h168hFeatureRow)


def test_market_identity_is_preserved_exactly() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_168H, market_id="market-7", price=_price("41.00")),
        _market(timestamp=target - _LAG_24H, market_id="market-7", price=_price("45.00")),
        _market(timestamp=target, market_id="market-7", price=_price("52.50")),
    )
    row = _build(history)[0]
    assert row.market_id == "market-7"


def test_currency_is_preserved_exactly() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_168H, price=_price("41.00", currency="EUR")),
        _market(timestamp=target - _LAG_24H, price=_price("45.00", currency="EUR")),
        _market(timestamp=target, price=_price("52.50", currency="EUR")),
    )
    row = _build(history)[0]
    assert row.currency == "EUR"


def test_target_timestamp_is_preserved_exactly() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_168H, price=_price("41.00")),
        _market(timestamp=target - _LAG_24H, price=_price("45.00")),
        _market(timestamp=target, price=_price("52.50")),
    )
    row = _build(history)[0]
    assert row.target_timestamp == target


def test_lag_24h_amount_is_copied_from_the_exact_24h_observation() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_168H, price=_price("41.00")),
        _market(timestamp=target - _LAG_24H, price=_price("45.25")),
        _market(timestamp=target, price=_price("52.50")),
    )
    row = _build(history)[0]
    assert row.lag_24h_amount_per_mwh == Decimal("45.25")


def test_lag_168h_amount_is_copied_from_the_exact_168h_observation() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_168H, price=_price("41.75")),
        _market(timestamp=target - _LAG_24H, price=_price("45.00")),
        _market(timestamp=target, price=_price("52.50")),
    )
    row = _build(history)[0]
    assert row.lag_168h_amount_per_mwh == Decimal("41.75")


def test_target_amount_is_copied_from_the_exact_target_observation() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_168H, price=_price("41.00")),
        _market(timestamp=target - _LAG_24H, price=_price("45.00")),
        _market(timestamp=target, price=_price("52.50")),
    )
    row = _build(history)[0]
    assert row.target_amount_per_mwh == Decimal("52.50")


def test_canonical_decimal_precision_is_preserved() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_168H, price=_price("0.01")),
        _market(timestamp=target - _LAG_24H, price=_price("1234.567")),
        _market(timestamp=target, price=_price("0.001")),
    )
    row = _build(history)[0]
    assert isinstance(row.lag_24h_amount_per_mwh, Decimal)
    assert isinstance(row.lag_168h_amount_per_mwh, Decimal)
    assert isinstance(row.target_amount_per_mwh, Decimal)
    assert not isinstance(row.lag_24h_amount_per_mwh, float)
    assert row.lag_24h_amount_per_mwh == Decimal("1234.567")
    assert row.lag_168h_amount_per_mwh == Decimal("0.01")
    assert row.target_amount_per_mwh == Decimal("0.001")


def test_negative_lag_24h_amount_is_valid() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_168H, price=_price("41.00")),
        _market(timestamp=target - _LAG_24H, price=_price("-20.00")),
        _market(timestamp=target, price=_price("5.00")),
    )
    row = _build(history)[0]
    assert row.lag_24h_amount_per_mwh == Decimal("-20.00")
    assert row.lag_24h_amount_per_mwh < 0


def test_negative_lag_168h_amount_is_valid() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_168H, price=_price("-33.00")),
        _market(timestamp=target - _LAG_24H, price=_price("45.00")),
        _market(timestamp=target, price=_price("5.00")),
    )
    row = _build(history)[0]
    assert row.lag_168h_amount_per_mwh == Decimal("-33.00")
    assert row.lag_168h_amount_per_mwh < 0


def test_negative_target_amount_is_valid() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_168H, price=_price("41.00")),
        _market(timestamp=target - _LAG_24H, price=_price("45.00")),
        _market(timestamp=target, price=_price("-5.00")),
    )
    row = _build(history)[0]
    assert row.target_amount_per_mwh == Decimal("-5.00")
    assert row.target_amount_per_mwh < 0


def test_all_three_amounts_negative_are_valid() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_168H, price=_price("-11.00")),
        _market(timestamp=target - _LAG_24H, price=_price("-22.00")),
        _market(timestamp=target, price=_price("-33.00")),
    )
    row = _build(history)[0]
    assert row.lag_24h_amount_per_mwh == Decimal("-22.00")
    assert row.lag_168h_amount_per_mwh == Decimal("-11.00")
    assert row.target_amount_per_mwh == Decimal("-33.00")


def test_zero_amounts_are_valid() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_168H, price=_price("0")),
        _market(timestamp=target - _LAG_24H, price=_price("0.00")),
        _market(timestamp=target, price=_price("0")),
    )
    row = _build(history)[0]
    assert row.lag_24h_amount_per_mwh == Decimal("0.00")
    assert row.lag_168h_amount_per_mwh == Decimal("0")
    assert row.target_amount_per_mwh == Decimal("0")


def test_multiple_valid_targets_produce_multiple_rows() -> None:
    # Two valid targets require distinct exact-lag supports: the second target
    # needs its own exact 168h observation, which is not the first target's.
    base = _ts(10)
    history = (
        _market(timestamp=base - _LAG_168H, price=_price("30.00")),
        _market(timestamp=base - _LAG_168H + _LAG_24H, price=_price("40.00")),
        _market(timestamp=base - _LAG_24H, price=_price("31.00")),
        _market(timestamp=base, price=_price("32.00")),
        _market(timestamp=base + _LAG_24H, price=_price("33.00")),
    )
    result = _build(history)
    assert len(result) == 2
    assert tuple(row.target_timestamp for row in result) == (base, base + _LAG_24H)


def test_output_is_ordered_ascending_by_target_timestamp() -> None:
    base = _ts(10)
    history = (
        _market(timestamp=base - _LAG_168H, price=_price("30.00")),
        _market(timestamp=base - _LAG_168H + _LAG_24H, price=_price("31.00")),
        _market(timestamp=base - _LAG_168H + 2 * _LAG_24H, price=_price("32.00")),
        _market(timestamp=base - _LAG_24H, price=_price("33.00")),
        _market(timestamp=base, price=_price("34.00")),
        _market(timestamp=base + _LAG_24H, price=_price("35.00")),
        _market(timestamp=base + 2 * _LAG_24H, price=_price("36.00")),
    )
    result = _build(history)
    timestamps = tuple(row.target_timestamp for row in result)
    assert timestamps == tuple(sorted(timestamps))
    assert timestamps == (base, base + _LAG_24H, base + 2 * _LAG_24H)


def test_reversed_history_produces_equivalent_output() -> None:
    base = _ts(10)
    history = (
        _market(timestamp=base - _LAG_168H, price=_price("30.00")),
        _market(timestamp=base - _LAG_24H, price=_price("31.00")),
        _market(timestamp=base, price=_price("32.00")),
    )
    assert _build(history) == _build(tuple(reversed(history)))


def test_shuffled_history_produces_equivalent_output() -> None:
    base = _ts(10)
    history = (
        _market(timestamp=base - _LAG_168H, price=_price("30.00")),
        _market(timestamp=base - _LAG_24H, price=_price("31.00")),
        _market(timestamp=base, price=_price("32.00")),
    )
    shuffled = (history[1], history[2], history[0])
    assert _build(history) == _build(shuffled)


def test_missing_exact_24h_lag_skips_the_target() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_168H, price=_price("41.00")),
        _market(timestamp=target, price=_price("52.50")),
    )
    assert _build(history) == ()


def test_missing_exact_168h_lag_skips_the_target() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_24H, price=_price("45.00")),
        _market(timestamp=target, price=_price("52.50")),
    )
    assert _build(history) == ()


def test_target_with_only_the_24h_lag_produces_no_partial_row() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_24H, price=_price("45.00")),
        _market(timestamp=target, price=_price("52.50")),
    )
    result = _build(history)
    assert result == ()
    assert all(isinstance(row, DAMPriceLag24h168hFeatureRow) for row in result)


def test_target_with_only_the_168h_lag_produces_no_partial_row() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_168H, price=_price("41.00")),
        _market(timestamp=target, price=_price("52.50")),
    )
    assert _build(history) == ()


def test_near_24h_timestamp_is_not_accepted() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_168H, price=_price("41.00")),
        _market(timestamp=target - _LAG_24H + timedelta(hours=1), price=_price("45.00")),
        _market(timestamp=target, price=_price("52.50")),
    )
    assert _build(history) == ()


def test_near_168h_timestamp_is_not_accepted() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_168H + timedelta(hours=1), price=_price("41.00")),
        _market(timestamp=target - _LAG_24H, price=_price("45.00")),
        _market(timestamp=target, price=_price("52.50")),
    )
    assert _build(history) == ()


def test_167h_is_not_substituted_for_168h() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - timedelta(hours=167), price=_price("41.00")),
        _market(timestamp=target - _LAG_24H, price=_price("45.00")),
        _market(timestamp=target, price=_price("52.50")),
    )
    assert _build(history) == ()


def test_169h_is_not_substituted_for_168h() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - timedelta(hours=169), price=_price("41.00")),
        _market(timestamp=target - _LAG_24H, price=_price("45.00")),
        _market(timestamp=target, price=_price("52.50")),
    )
    assert _build(history) == ()


def test_duplicate_timestamps_fail_closed() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_168H, price=_price("41.00")),
        _market(timestamp=target - _LAG_24H, price=_price("45.00")),
        _market(timestamp=target, price=_price("52.50")),
        _market(timestamp=target, price=_price("99.99")),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _build(history)
    assert captured.value.message == _DUPLICATE_TIMESTAMP_MESSAGE


def test_duplicate_timestamp_fails_even_when_outside_any_valid_triple() -> None:
    target = _ts(8)
    unrelated = _ts(1)
    history = (
        _market(timestamp=unrelated, price=_price("1.00")),
        _market(timestamp=unrelated, price=_price("2.00")),
        _market(timestamp=target - _LAG_168H, price=_price("41.00")),
        _market(timestamp=target - _LAG_24H, price=_price("45.00")),
        _market(timestamp=target, price=_price("52.50")),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _build(history)
    assert captured.value.message == _DUPLICATE_TIMESTAMP_MESSAGE


def test_mixed_markets_fail_closed() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_168H, market_id="market-alpha", price=_price("41.00")),
        _market(timestamp=target - _LAG_24H, market_id="market-beta", price=_price("45.00")),
        _market(timestamp=target, market_id="market-beta", price=_price("52.50")),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _build(history)
    assert captured.value.message == _MIXED_MARKET_MESSAGE


def test_mixed_market_message_leaks_no_raw_market_id() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_168H, market_id="market-alpha", price=_price("41.00")),
        _market(timestamp=target - _LAG_24H, market_id="market-beta", price=_price("45.00")),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _build(history)
    assert "market-alpha" not in captured.value.message
    assert "market-beta" not in captured.value.message


def test_mixed_currencies_fail_closed() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_168H, price=_price("41.00", currency="AMD")),
        _market(timestamp=target - _LAG_24H, price=_price("45.00", currency="EUR")),
        _market(timestamp=target, price=_price("52.50", currency="AMD")),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _build(history)
    assert captured.value.message == _MIXED_CURRENCY_MESSAGE


def test_mixed_currency_message_leaks_no_raw_currency_code() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_168H, price=_price("41.00", currency="AMD")),
        _market(timestamp=target - _LAG_24H, price=_price("45.00", currency="EUR")),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _build(history)
    assert "AMD" not in captured.value.message
    assert "EUR" not in captured.value.message


def test_differing_volume_values_do_not_alter_feature_values() -> None:
    target = _ts(8)
    without_volume = (
        _market(timestamp=target - _LAG_168H, price=_price("41.00")),
        _market(timestamp=target - _LAG_24H, price=_price("45.00")),
        _market(timestamp=target, price=_price("52.50")),
    )
    with_volume = (
        _market(timestamp=target - _LAG_168H, price=_price("41.00"), volume_mwh="1000"),
        _market(timestamp=target - _LAG_24H, price=_price("45.00"), volume_mwh="2000"),
        _market(timestamp=target, price=_price("52.50"), volume_mwh="3000"),
    )
    assert _build(without_volume) == _build(with_volume)


def test_row_contains_no_volume_field() -> None:
    names = {item.name for item in fields(DAMPriceLag24h168hFeatureRow)}
    assert "volume_mwh" not in names
    assert "volume" not in names


def test_caller_history_and_records_remain_unchanged() -> None:
    target = _ts(8)
    first = _market(timestamp=target - _LAG_168H, price=_price("41.00"))
    second = _market(timestamp=target - _LAG_24H, price=_price("45.00"))
    third = _market(timestamp=target, price=_price("52.50"))
    history = (first, second, third)
    _build(history)
    assert history == (first, second, third)
    assert first.timestamp == target - _LAG_168H
    assert second.price.amount_per_mwh == Decimal("45.00")
    assert third.price.amount_per_mwh == Decimal("52.50")
    assert first.volume_mwh is None


def test_repeated_equivalent_call_returns_value_equivalent_output() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_168H, price=_price("41.00")),
        _market(timestamp=target - _LAG_24H, price=_price("45.00")),
        _market(timestamp=target, price=_price("52.50")),
    )
    assert _build(history) == _build(history)


def test_row_dataclass_is_frozen() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_168H, price=_price("41.00")),
        _market(timestamp=target - _LAG_24H, price=_price("45.00")),
        _market(timestamp=target, price=_price("52.50")),
    )
    row = _build(history)[0]
    with pytest.raises(FrozenInstanceError):
        row.lag_168h_amount_per_mwh = Decimal("0")  # type: ignore[misc]


def test_row_dataclass_is_slotted() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_168H, price=_price("41.00")),
        _market(timestamp=target - _LAG_24H, price=_price("45.00")),
        _market(timestamp=target, price=_price("52.50")),
    )
    row = _build(history)[0]
    assert DAMPriceLag24h168hFeatureRow.__slots__ == SIX_FIELDS
    assert not hasattr(row, "__dict__")


def test_row_contract_is_exactly_six_fields() -> None:
    names = tuple(item.name for item in fields(DAMPriceLag24h168hFeatureRow))
    assert names == SIX_FIELDS


def test_row_fields_have_no_defaults() -> None:
    defaults = tuple(
        DAMPriceLag24h168hFeatureRow.__dataclass_fields__[name].default for name in SIX_FIELDS
    )
    assert all(value is MISSING for value in defaults)
    assert DAMPriceLag24h168hFeatureRow.__dataclass_fields__[SIX_FIELDS[3]].default_factory is (
        MISSING
    )


def test_builder_is_synchronous_and_keyword_only() -> None:
    assert not inspect.iscoroutinefunction(build_dam_price_lag_24h_168h_feature_rows)
    parameters = inspect.signature(build_dam_price_lag_24h_168h_feature_rows).parameters
    assert tuple(parameters) == ("history",)
    assert parameters["history"].kind is inspect.Parameter.KEYWORD_ONLY


def test_result_is_a_tuple_of_the_exact_new_row_type() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_168H, price=_price("41.00")),
        _market(timestamp=target - _LAG_24H, price=_price("45.00")),
        _market(timestamp=target, price=_price("52.50")),
    )
    result = _build(history)
    assert isinstance(result, tuple)
    assert all(isinstance(row, DAMPriceLag24h168hFeatureRow) for row in result)


def test_one_feature_builder_of_chunk_173_is_not_called() -> None:
    from energy_trading.ml import dam_price

    assert not hasattr(dam_price, "build_dam_price_lag_24h_feature_rows")
    target = _ts(8)
    history = (
        _market(timestamp=target - _LAG_168H, price=_price("41.00")),
        _market(timestamp=target - _LAG_24H, price=_price("45.00")),
        _market(timestamp=target, price=_price("52.50")),
    )
    row = _build(history)[0]
    assert row.lag_24h_amount_per_mwh == Decimal("45.00")
    assert row.lag_168h_amount_per_mwh == Decimal("41.00")
