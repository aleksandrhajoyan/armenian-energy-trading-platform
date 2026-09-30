"""Exact 24-hour lag DAM Price supervised feature rows."""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError, fields
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
from energy_trading.ml.dam_price.lag_24h_features import (
    DAMPriceLag24hFeatureRow,
    build_dam_price_lag_24h_feature_rows,
)

_MIXED_MARKET_MESSAGE = "DAM Price 24-hour lag features require history from exactly one market."
_MIXED_CURRENCY_MESSAGE = "DAM Price 24-hour lag features require history in exactly one currency."
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "DAM Price 24-hour lag features require unique historical timestamps."
)
_LAG = timedelta(hours=24)


def _ts(day: int, hour: int = 16) -> datetime:
    return datetime(2026, 10, day, hour, 0, 0, tzinfo=UTC)


def _price(amount: str, *, currency: str = "AMD") -> EnergyPrice:
    return EnergyPrice(amount_per_mwh=Decimal(amount), currency=currency)


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
        "price": price if price is not None else _price("12.50"),
    }
    if volume_mwh is not None:
        values["volume_mwh"] = volume_mwh
    return MarketPriceRecord(**values)  # type: ignore[arg-type]


def _build(
    history: tuple[MarketPriceRecord, ...],
) -> tuple[DAMPriceLag24hFeatureRow, ...]:
    return build_dam_price_lag_24h_feature_rows(history=history)


def test_empty_history_returns_empty_tuple() -> None:
    result = _build(())
    assert result == ()
    assert isinstance(result, tuple)


def test_single_observation_returns_empty_tuple() -> None:
    assert _build((_market(timestamp=_ts(1)),)) == ()


def test_one_exact_pair_produces_one_row() -> None:
    target = _ts(2)
    history = (
        _market(timestamp=target - _LAG, price=_price("45.00")),
        _market(timestamp=target, price=_price("52.50")),
    )
    result = _build(history)
    assert len(result) == 1
    row = result[0]
    assert isinstance(row, DAMPriceLag24hFeatureRow)
    assert row.market_id == "market-1"
    assert row.currency == "AMD"
    assert row.target_timestamp == target
    assert row.lag_24h_amount_per_mwh == Decimal("45.00")
    assert row.target_amount_per_mwh == Decimal("52.50")


def test_canonical_decimal_values_are_preserved() -> None:
    target = _ts(2)
    history = (
        _market(timestamp=target - _LAG, price=_price("0.01")),
        _market(timestamp=target, price=_price("1234.567")),
    )
    row = _build(history)[0]
    assert isinstance(row.lag_24h_amount_per_mwh, Decimal)
    assert isinstance(row.target_amount_per_mwh, Decimal)
    assert not isinstance(row.lag_24h_amount_per_mwh, float)
    assert row.lag_24h_amount_per_mwh == Decimal("0.01")
    assert row.target_amount_per_mwh == Decimal("1234.567")


def test_negative_lag_price_is_preserved() -> None:
    target = _ts(2)
    history = (
        _market(timestamp=target - _LAG, price=_price("-20.00")),
        _market(timestamp=target, price=_price("5.00")),
    )
    row = _build(history)[0]
    assert row.lag_24h_amount_per_mwh == Decimal("-20.00")
    assert row.lag_24h_amount_per_mwh < 0


def test_negative_target_price_is_preserved() -> None:
    target = _ts(2)
    history = (
        _market(timestamp=target - _LAG, price=_price("10.00")),
        _market(timestamp=target, price=_price("-5.00")),
    )
    row = _build(history)[0]
    assert row.target_amount_per_mwh == Decimal("-5.00")
    assert row.target_amount_per_mwh < 0


def test_both_prices_negative_are_preserved_without_clamping() -> None:
    target = _ts(2)
    history = (
        _market(timestamp=target - _LAG, price=_price("-20.00")),
        _market(timestamp=target, price=_price("-5.00")),
    )
    row = _build(history)[0]
    assert row.lag_24h_amount_per_mwh == Decimal("-20.00")
    assert row.target_amount_per_mwh == Decimal("-5.00")


def test_multiple_daily_observations_produce_chronological_rows() -> None:
    history = tuple(
        _market(timestamp=_ts(day), price=_price(f"{10 + day}.00")) for day in range(1, 4)
    )
    result = _build(history)
    assert len(result) == 2
    assert tuple(row.target_timestamp for row in result) == (_ts(2), _ts(3))
    assert result[0].lag_24h_amount_per_mwh == Decimal("11.00")
    assert result[0].target_amount_per_mwh == Decimal("12.00")
    assert result[1].lag_24h_amount_per_mwh == Decimal("12.00")
    assert result[1].target_amount_per_mwh == Decimal("13.00")


def test_out_of_order_history_produces_ascending_rows() -> None:
    first = _ts(1)
    second = _ts(2)
    third = _ts(3)
    records = (
        _market(timestamp=first, price=_price("10.00")),
        _market(timestamp=second, price=_price("20.00")),
        _market(timestamp=third, price=_price("30.00")),
    )
    ordered = _build(records)
    shuffled = _build((records[2], records[0], records[1]))
    assert ordered == shuffled
    assert tuple(row.target_timestamp for row in shuffled) == (second, third)


def test_missing_exact_lag_is_omitted_not_raised() -> None:
    history = (
        _market(timestamp=_ts(1), price=_price("10.00")),
        _market(timestamp=_ts(2), price=_price("20.00")),
        _market(timestamp=_ts(4), price=_price("40.00")),
    )
    result = _build(history)
    assert tuple(row.target_timestamp for row in result) == (_ts(2),)


def test_near_but_not_exact_lag_does_not_qualify() -> None:
    target = _ts(2)
    near = target - _LAG + timedelta(minutes=1)
    history = (
        _market(timestamp=near, price=_price("99.00")),
        _market(timestamp=target, price=_price("50.00")),
    )
    assert _build(history) == ()


def test_weekly_lag_is_not_used_as_fallback() -> None:
    target = _ts(8)
    history = (
        _market(timestamp=target - timedelta(hours=168), price=_price("99.00")),
        _market(timestamp=target, price=_price("50.00")),
    )
    assert _build(history) == ()


def test_gaps_are_not_interpolated() -> None:
    history = (
        _market(timestamp=_ts(1), price=_price("10.00")),
        _market(timestamp=_ts(5), price=_price("50.00")),
    )
    assert _build(history) == ()


def test_duplicate_history_timestamp_fails_closed() -> None:
    duplicate = _ts(1)
    history = (
        _market(timestamp=duplicate, price=_price("10.00")),
        _market(timestamp=duplicate, price=_price("11.00")),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _build(history)
    assert captured.value.message == _DUPLICATE_TIMESTAMP_MESSAGE


def test_duplicate_timestamp_fails_closed_even_without_valid_pair() -> None:
    duplicate = _ts(9, hour=3)
    history = (
        _market(timestamp=duplicate, price=_price("10.00")),
        _market(timestamp=duplicate, price=_price("11.00")),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _build(history)
    assert captured.value.message == _DUPLICATE_TIMESTAMP_MESSAGE


def test_duplicate_timestamp_does_not_return_partial_rows() -> None:
    first = _ts(1)
    second = _ts(2)
    history = (
        _market(timestamp=first, price=_price("10.00")),
        _market(timestamp=second, price=_price("20.00")),
        _market(timestamp=second, price=_price("21.00")),
    )
    with pytest.raises(InvalidRequestError):
        _build(history)


def test_mixed_market_history_fails_closed_without_leaking_ids() -> None:
    target = _ts(2)
    history = (
        _market(timestamp=target - _LAG, market_id="market-alpha"),
        _market(timestamp=target, market_id="market-beta"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _build(history)
    assert captured.value.message == _MIXED_MARKET_MESSAGE
    assert "market-alpha" not in captured.value.message
    assert "market-beta" not in captured.value.message


def test_mixed_currency_history_fails_closed_without_leaking_codes() -> None:
    target = _ts(2)
    history = (
        _market(timestamp=target - _LAG, price=_price("10.00", currency="AMD")),
        _market(timestamp=target, price=_price("11.00", currency="EUR")),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _build(history)
    assert captured.value.message == _MIXED_CURRENCY_MESSAGE
    assert "AMD" not in captured.value.message
    assert "EUR" not in captured.value.message


def test_shared_currency_is_copied_into_every_row() -> None:
    history = tuple(
        _market(timestamp=_ts(day), price=_price(f"{10 + day}.00", currency="EUR"))
        for day in range(1, 4)
    )
    result = _build(history)
    assert len(result) == 2
    assert all(row.currency == "EUR" for row in result)


def test_volume_is_ignored_and_absent_from_the_row() -> None:
    target = _ts(2)
    history = (
        _market(timestamp=target - _LAG, price=_price("10.00"), volume_mwh=1000.0),
        _market(timestamp=target, price=_price("20.00"), volume_mwh=1.0),
    )
    row = _build(history)[0]
    assert row.lag_24h_amount_per_mwh == Decimal("10.00")
    assert row.target_amount_per_mwh == Decimal("20.00")
    row_fields = {item.name for item in fields(DAMPriceLag24hFeatureRow)}
    assert "volume_mwh" not in row_fields
    assert not hasattr(row, "volume_mwh")


def test_rows_are_ascending_by_target_timestamp() -> None:
    history = tuple(_market(timestamp=_ts(day)) for day in (4, 1, 3, 2))
    result = _build(history)
    timestamps = tuple(row.target_timestamp for row in result)
    assert timestamps == tuple(sorted(timestamps))
    assert timestamps == (_ts(2), _ts(3), _ts(4))


def test_input_history_is_not_mutated() -> None:
    target = _ts(2)
    lag_record = _market(timestamp=target - _LAG, price=_price("10.00"))
    target_record = _market(timestamp=target, price=_price("20.00"))
    history = (lag_record, target_record)
    _build(history)
    assert history == (lag_record, target_record)
    assert lag_record.price.amount_per_mwh == Decimal("10.00")
    assert target_record.price.amount_per_mwh == Decimal("20.00")
    assert lag_record.timestamp == target - _LAG


def test_repeated_equal_inputs_are_value_equivalent() -> None:
    target = _ts(2)
    history = (
        _market(timestamp=target - _LAG, price=_price("10.00")),
        _market(timestamp=target, price=_price("20.00")),
    )
    assert _build(history) == _build(history)


def test_row_contract_is_frozen_slotted_and_exactly_five_fields() -> None:
    names = tuple(item.name for item in fields(DAMPriceLag24hFeatureRow))
    assert names == (
        "market_id",
        "currency",
        "target_timestamp",
        "lag_24h_amount_per_mwh",
        "target_amount_per_mwh",
    )
    assert DAMPriceLag24hFeatureRow.__slots__ == names
    target = _ts(2)
    row = _build(
        (
            _market(timestamp=target - _LAG),
            _market(timestamp=target),
        )
    )[0]
    with pytest.raises(FrozenInstanceError):
        row.target_amount_per_mwh = Decimal("0")  # type: ignore[misc]


def test_row_exposes_no_extra_engineered_feature() -> None:
    names = {item.name for item in fields(DAMPriceLag24hFeatureRow)}
    forbidden = {
        "volume_mwh",
        "volume",
        "hour",
        "weekday",
        "month",
        "holiday",
        "weather",
        "generation",
        "hydro",
        "renewable",
        "rolling_mean",
        "volatility",
        "lag_168h_amount_per_mwh",
        "spread",
        "residual",
        "forecast_run_id",
        "generated_at",
        "model_name",
        "model_version",
    }
    assert forbidden.isdisjoint(names)
    assert len(names) == 5


def test_builder_is_synchronous_and_keyword_only() -> None:
    assert not inspect.iscoroutinefunction(build_dam_price_lag_24h_feature_rows)
    parameters = inspect.signature(build_dam_price_lag_24h_feature_rows).parameters
    assert tuple(parameters) == ("history",)
    assert parameters["history"].kind is inspect.Parameter.KEYWORD_ONLY


def test_market_id_comes_from_the_target_record() -> None:
    target = _ts(2)
    history = (
        _market(timestamp=target - _LAG, market_id="market-1"),
        _market(timestamp=target, market_id="market-1"),
    )
    row = _build(history)[0]
    assert row.market_id == "market-1"
    assert row.market_id == history[1].market_id
