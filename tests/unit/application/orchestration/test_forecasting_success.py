"""Application-owned forecasting success aggregate contract."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime, timedelta, timezone

import pytest

from energy_trading.application.orchestration import ForecastingSuccess
from energy_trading.domain.models.forecasting import LoadForecastPoint, PriceForecastPoint
from tests.unit.domain._factories import amd_price, utc


def _load_point(**overrides: object) -> LoadForecastPoint:
    values: dict[str, object] = {
        "forecast_run_id": "run-1",
        "consumer_id": "consumer-1",
        "generated_at": utc(),
        "target_timestamp": utc(hour=16),
        "value_mw": 3.25,
    }
    values.update(overrides)
    return LoadForecastPoint.model_validate(values)


def _price_point(**overrides: object) -> PriceForecastPoint:
    values: dict[str, object] = {
        "forecast_run_id": "run-1",
        "market_id": "market-1",
        "generated_at": utc(),
        "target_timestamp": utc(hour=16),
        "price": amd_price("45.00"),
    }
    values.update(overrides)
    return PriceForecastPoint.model_validate(values)


def test_success_can_be_constructed_from_canonical_forecast_points() -> None:
    load_forecast = (_load_point(),)
    price_forecast = (_price_point(),)
    success = ForecastingSuccess(
        consumer_load_forecast=load_forecast,
        dam_price_forecast=price_forecast,
    )
    assert isinstance(success.consumer_load_forecast[0], LoadForecastPoint)
    assert isinstance(success.dam_price_forecast[0], PriceForecastPoint)


def test_success_preserves_supplied_load_tuple_exactly() -> None:
    load_forecast = (_load_point(), _load_point(target_timestamp=utc(hour=17)))
    success = ForecastingSuccess(
        consumer_load_forecast=load_forecast,
        dam_price_forecast=(),
    )
    assert success.consumer_load_forecast is load_forecast


def test_success_preserves_supplied_price_tuple_exactly() -> None:
    price_forecast = (_price_point(), _price_point(target_timestamp=utc(hour=17)))
    success = ForecastingSuccess(
        consumer_load_forecast=(),
        dam_price_forecast=price_forecast,
    )
    assert success.dam_price_forecast is price_forecast


def test_success_is_frozen() -> None:
    success = ForecastingSuccess(
        consumer_load_forecast=(_load_point(),),
        dam_price_forecast=(_price_point(),),
    )
    with pytest.raises(FrozenInstanceError):
        success.consumer_load_forecast = ()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        success.dam_price_forecast = ()  # type: ignore[misc]


def test_success_is_slotted_and_has_no_instance_dict() -> None:
    success = ForecastingSuccess(
        consumer_load_forecast=(_load_point(),),
        dam_price_forecast=(_price_point(),),
    )
    assert hasattr(ForecastingSuccess, "__slots__")
    assert not hasattr(success, "__dict__")


def test_success_allows_both_empty_tuples() -> None:
    empty_load: tuple[LoadForecastPoint, ...] = ()
    empty_price: tuple[PriceForecastPoint, ...] = ()
    success = ForecastingSuccess(
        consumer_load_forecast=empty_load,
        dam_price_forecast=empty_price,
    )
    assert success.consumer_load_forecast is empty_load
    assert success.dam_price_forecast is empty_price


def test_success_allows_one_empty_and_one_non_empty_tuple() -> None:
    load_forecast = (_load_point(),)
    empty_price: tuple[PriceForecastPoint, ...] = ()
    success = ForecastingSuccess(
        consumer_load_forecast=load_forecast,
        dam_price_forecast=empty_price,
    )
    assert success.consumer_load_forecast is load_forecast
    assert success.dam_price_forecast is empty_price


def test_success_allows_different_tuple_lengths() -> None:
    load_forecast = (_load_point(), _load_point(target_timestamp=utc(hour=17)))
    price_forecast = (_price_point(),)
    success = ForecastingSuccess(
        consumer_load_forecast=load_forecast,
        dam_price_forecast=price_forecast,
    )
    assert len(success.consumer_load_forecast) != len(success.dam_price_forecast)
    assert success.consumer_load_forecast is load_forecast
    assert success.dam_price_forecast is price_forecast


def test_success_allows_distinct_timestamps_between_outputs() -> None:
    load_forecast = (
        _load_point(
            consumer_id="consumer-west",
            target_timestamp=datetime(2026, 10, 1, 0, tzinfo=UTC),
        ),
        _load_point(
            consumer_id="consumer-west",
            target_timestamp=datetime(2026, 10, 1, 1, tzinfo=UTC),
        ),
    )
    price_forecast = (
        _price_point(
            market_id="market-east",
            target_timestamp=datetime(2026, 10, 2, 12, tzinfo=timezone(timedelta(hours=4))),
        ),
    )
    success = ForecastingSuccess(
        consumer_load_forecast=load_forecast,
        dam_price_forecast=price_forecast,
    )
    assert success.consumer_load_forecast[0].target_timestamp != (
        success.dam_price_forecast[0].target_timestamp
    )
    assert success.consumer_load_forecast[0].consumer_id != (
        success.dam_price_forecast[0].market_id
    )
    assert success.consumer_load_forecast is load_forecast
    assert success.dam_price_forecast is price_forecast


def test_success_rejects_non_tuple_containers() -> None:
    with pytest.raises(TypeError, match="consumer_load_forecast must be an immutable tuple"):
        ForecastingSuccess(
            consumer_load_forecast=[_load_point()],  # type: ignore[arg-type]
            dam_price_forecast=(),
        )
    with pytest.raises(TypeError, match="dam_price_forecast must be an immutable tuple"):
        ForecastingSuccess(
            consumer_load_forecast=(),
            dam_price_forecast=[_price_point()],  # type: ignore[arg-type]
        )


def test_success_rejects_wrong_element_types() -> None:
    with pytest.raises(
        TypeError,
        match="consumer_load_forecast must contain LoadForecastPoint values",
    ):
        ForecastingSuccess(
            consumer_load_forecast=(_price_point(),),  # type: ignore[arg-type]
            dam_price_forecast=(),
        )
    with pytest.raises(
        TypeError,
        match="dam_price_forecast must contain PriceForecastPoint values",
    ):
        ForecastingSuccess(
            consumer_load_forecast=(),
            dam_price_forecast=(_load_point(),),  # type: ignore[arg-type]
        )


def test_success_public_fields_are_exactly_the_two_forecast_tuples() -> None:
    field_names = tuple(item.name for item in fields(ForecastingSuccess))
    assert field_names == ("consumer_load_forecast", "dam_price_forecast")
