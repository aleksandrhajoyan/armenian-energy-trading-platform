"""Exact previous-day persistence DAM Price Forecast baseline."""

from __future__ import annotations

import inspect
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from tests.unit.domain._factories import amd_price, utc

from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.ports.dam_price_forecast_model import (
    DAMPriceForecastModelPort,
    DAMPriceForecastModelRequest,
)
from energy_trading.domain.models.forecasting import PriceForecastPoint
from energy_trading.domain.models.observations import MarketPriceRecord
from energy_trading.domain.value_objects.money import EnergyPrice
from energy_trading.ml.dam_price.previous_day_persistence import (
    PreviousDayPersistenceDAMPriceForecastModel,
)

_MISSING_LAG_MESSAGE = (
    "Previous-day persistence requires exactly one history observation at the 24-hour lag."
)
_DUPLICATE_LAG_MESSAGE = "Previous-day persistence requires a unique 24-hour lag observation."
_LAG = timedelta(hours=24)


def _as_model_port(
    model: PreviousDayPersistenceDAMPriceForecastModel,
) -> DAMPriceForecastModelPort:
    return model


def _market(
    *,
    timestamp: datetime,
    market_id: str = "market-1",
    price: EnergyPrice | None = None,
) -> MarketPriceRecord:
    return MarketPriceRecord(
        market_id=market_id,
        timestamp=timestamp,
        price=price if price is not None else amd_price(),
    )


def _request(**overrides: object) -> DAMPriceForecastModelRequest:
    target = utc(hour=16)
    values: dict[str, object] = {
        "forecast_run_id": "run-1",
        "generated_at": utc(hour=9),
        "market_id": "market-1",
        "currency": "AMD",
        "history": (_market(timestamp=target - _LAG, price=amd_price("45.00")),),
        "target_timestamps": (target,),
    }
    values.update(overrides)
    return DAMPriceForecastModelRequest(**values)  # type: ignore[arg-type]


def test_structural_port_conformance_without_inheritance() -> None:
    model = PreviousDayPersistenceDAMPriceForecastModel()
    port = _as_model_port(model)
    assert port is model
    assert DAMPriceForecastModelPort not in PreviousDayPersistenceDAMPriceForecastModel.__mro__
    assert not any(
        base.__name__
        in {
            "DAMPriceForecastModelPort",
            "Protocol",
            "ABC",
            "ModelPort",
            "ForecastPort",
        }
        for base in PreviousDayPersistenceDAMPriceForecastModel.__bases__
    )
    assert inspect.iscoroutinefunction(port.forecast)
    parameters = inspect.signature(PreviousDayPersistenceDAMPriceForecastModel.forecast).parameters
    assert tuple(parameters) == ("self", "request")
    assert parameters["request"].kind is inspect.Parameter.KEYWORD_ONLY


async def test_single_exact_previous_day_observation_copies_price_unchanged() -> None:
    target = utc(hour=16)
    history_record = _market(timestamp=target - _LAG, price=amd_price("45.00"))
    request = _request(history=(history_record,), target_timestamps=(target,))
    result = await PreviousDayPersistenceDAMPriceForecastModel().forecast(request=request)
    assert len(result) == 1
    point = result[0]
    assert isinstance(point, PriceForecastPoint)
    assert point.target_timestamp == target
    assert point.price == history_record.price
    assert point.price.amount_per_mwh == Decimal("45.00")
    assert isinstance(point.price.amount_per_mwh, Decimal)
    assert point.price.currency == "AMD"


async def test_identity_fields_pass_through_unchanged() -> None:
    target = utc(hour=16)
    generated_at = utc(hour=11)
    request = _request(
        forecast_run_id="run-explicit",
        generated_at=generated_at,
        history=(_market(timestamp=target - _LAG),),
        target_timestamps=(target,),
    )
    result = await PreviousDayPersistenceDAMPriceForecastModel().forecast(request=request)
    point = result[0]
    assert point.forecast_run_id == "run-explicit"
    assert point.forecast_run_id == request.forecast_run_id
    assert point.generated_at == generated_at
    assert point.generated_at == request.generated_at
    assert point.market_id == "market-1"
    assert point.market_id == request.market_id


async def test_multiple_targets_one_output_each_in_requested_order() -> None:
    first = utc(hour=16)
    second = utc(hour=17)
    third = utc(hour=18)
    history = (
        _market(timestamp=first - _LAG, price=amd_price("10.00")),
        _market(timestamp=second - _LAG, price=amd_price("20.00")),
        _market(timestamp=third - _LAG, price=amd_price("30.00")),
    )
    request = _request(history=history, target_timestamps=(first, second, third))
    result = await PreviousDayPersistenceDAMPriceForecastModel().forecast(request=request)
    assert len(result) == 3
    assert tuple(point.target_timestamp for point in result) == (first, second, third)
    assert tuple(point.price.amount_per_mwh for point in result) == (
        Decimal("10.00"),
        Decimal("20.00"),
        Decimal("30.00"),
    )


async def test_out_of_order_targets_follow_request_order() -> None:
    late = utc(hour=18)
    early = utc(hour=16)
    history = (
        _market(timestamp=late - _LAG, price=amd_price("30.00")),
        _market(timestamp=early - _LAG, price=amd_price("10.00")),
    )
    request = _request(history=history, target_timestamps=(late, early))
    result = await PreviousDayPersistenceDAMPriceForecastModel().forecast(request=request)
    assert tuple(point.target_timestamp for point in result) == (late, early)
    assert result[0].price.amount_per_mwh == Decimal("30.00")
    assert result[1].price.amount_per_mwh == Decimal("10.00")


async def test_duplicate_targets_are_not_deduplicated() -> None:
    first = utc(hour=16)
    second = utc(hour=17)
    history = (
        _market(timestamp=first - _LAG, price=amd_price("10.00")),
        _market(timestamp=second - _LAG, price=amd_price("20.00")),
    )
    request = _request(history=history, target_timestamps=(first, first, second))
    result = await PreviousDayPersistenceDAMPriceForecastModel().forecast(request=request)
    assert len(result) == 3
    assert tuple(point.target_timestamp for point in result) == (first, first, second)
    assert result[0].price.amount_per_mwh == Decimal("10.00")
    assert result[1].price.amount_per_mwh == Decimal("10.00")
    assert result[2].price.amount_per_mwh == Decimal("20.00")


async def test_missing_exact_lag_fails_closed() -> None:
    target = utc(hour=16)
    request = _request(history=(), target_timestamps=(target,))
    with pytest.raises(InvalidRequestError) as captured:
        await PreviousDayPersistenceDAMPriceForecastModel().forecast(request=request)
    assert captured.value.message == _MISSING_LAG_MESSAGE


async def test_near_but_not_exact_lag_is_not_accepted() -> None:
    target = utc(hour=16)
    near = target - _LAG + timedelta(minutes=1)
    request = _request(
        history=(_market(timestamp=near),),
        target_timestamps=(target,),
    )
    with pytest.raises(InvalidRequestError) as captured:
        await PreviousDayPersistenceDAMPriceForecastModel().forecast(request=request)
    assert captured.value.message == _MISSING_LAG_MESSAGE


async def test_weekly_lag_is_not_used_as_fallback() -> None:
    target = utc(hour=16)
    request = _request(
        history=(_market(timestamp=target - timedelta(hours=168)),),
        target_timestamps=(target,),
    )
    with pytest.raises(InvalidRequestError) as captured:
        await PreviousDayPersistenceDAMPriceForecastModel().forecast(request=request)
    assert captured.value.message == _MISSING_LAG_MESSAGE


async def test_forward_lag_is_not_used() -> None:
    target = utc(hour=16)
    request = _request(
        history=(_market(timestamp=target + _LAG),),
        target_timestamps=(target,),
    )
    with pytest.raises(InvalidRequestError) as captured:
        await PreviousDayPersistenceDAMPriceForecastModel().forecast(request=request)
    assert captured.value.message == _MISSING_LAG_MESSAGE


async def test_empty_history_with_required_target_fails_closed() -> None:
    request = _request(history=(), target_timestamps=(utc(hour=16),))
    assert request.history == ()
    with pytest.raises(InvalidRequestError):
        await PreviousDayPersistenceDAMPriceForecastModel().forecast(request=request)


async def test_duplicate_exact_historical_lag_fails_closed() -> None:
    target = utc(hour=16)
    lag_timestamp = target - _LAG
    first = _market(timestamp=lag_timestamp, price=amd_price("10.00"))
    second = _market(timestamp=lag_timestamp, price=amd_price("99.00"))
    request = _request(history=(first, second), target_timestamps=(target,))
    with pytest.raises(InvalidRequestError) as captured:
        await PreviousDayPersistenceDAMPriceForecastModel().forecast(request=request)
    assert captured.value.message == _DUPLICATE_LAG_MESSAGE


async def test_no_partial_result_when_a_later_target_fails() -> None:
    first = utc(hour=16)
    second = utc(hour=17)
    history = (_market(timestamp=first - _LAG, price=amd_price("10.00")),)
    request = _request(history=history, target_timestamps=(first, second))
    with pytest.raises(InvalidRequestError):
        await PreviousDayPersistenceDAMPriceForecastModel().forecast(request=request)


async def test_negative_canonical_price_is_preserved() -> None:
    target = utc(hour=16)
    negative = EnergyPrice(amount_per_mwh=Decimal("-12.75"), currency="AMD")
    request = _request(
        history=(_market(timestamp=target - _LAG, price=negative),),
        target_timestamps=(target,),
    )
    result = await PreviousDayPersistenceDAMPriceForecastModel().forecast(request=request)
    assert result[0].price.amount_per_mwh == Decimal("-12.75")
    assert result[0].price.amount_per_mwh < 0
    assert result[0].price == negative


async def test_price_currency_is_not_converted() -> None:
    target = utc(hour=16)
    history_record = _market(timestamp=target - _LAG, price=amd_price("45.00"))
    request = _request(history=(history_record,), target_timestamps=(target,))
    result = await PreviousDayPersistenceDAMPriceForecastModel().forecast(request=request)
    assert result[0].price.currency == history_record.price.currency
    assert result[0].price.currency == request.currency


async def test_repeated_equivalent_requests_are_value_equivalent() -> None:
    target = utc(hour=16)
    request = _request(
        history=(_market(timestamp=target - _LAG, price=amd_price("45.00")),),
        target_timestamps=(target,),
    )
    first = await PreviousDayPersistenceDAMPriceForecastModel().forecast(request=request)
    second = await PreviousDayPersistenceDAMPriceForecastModel().forecast(request=request)
    assert first == second


async def test_inference_does_not_mutate_request_or_history() -> None:
    target = utc(hour=16)
    history_record = _market(timestamp=target - _LAG, price=amd_price("45.00"))
    request = _request(history=(history_record,), target_timestamps=(target,))
    await PreviousDayPersistenceDAMPriceForecastModel().forecast(request=request)
    assert request.forecast_run_id == "run-1"
    assert request.generated_at == utc(hour=9)
    assert request.market_id == "market-1"
    assert request.currency == "AMD"
    assert request.history == (history_record,)
    assert request.target_timestamps == (target,)
    assert history_record.price.amount_per_mwh == Decimal("45.00")


async def test_other_market_records_are_ignored_for_lag_matching() -> None:
    target = utc(hour=16)
    history = (
        _market(timestamp=target - _LAG, price=amd_price("45.00")),
        _market(timestamp=target, price=amd_price("99.00")),
        _market(timestamp=target - timedelta(hours=23), price=amd_price("98.00")),
    )
    request = _request(history=history, target_timestamps=(target,))
    result = await PreviousDayPersistenceDAMPriceForecastModel().forecast(request=request)
    assert len(result) == 1
    assert result[0].price.amount_per_mwh == Decimal("45.00")


async def test_output_timestamps_use_target_not_lag_timestamp() -> None:
    target = utc(hour=16)
    request = _request(
        history=(_market(timestamp=target - _LAG),),
        target_timestamps=(target,),
    )
    result = await PreviousDayPersistenceDAMPriceForecastModel().forecast(request=request)
    assert result[0].target_timestamp == target
    assert result[0].target_timestamp != target - _LAG


def test_model_defines_no_constructor_dependency() -> None:
    assert PreviousDayPersistenceDAMPriceForecastModel.__init__ is object.__init__
    model = PreviousDayPersistenceDAMPriceForecastModel()
    assert isinstance(model, PreviousDayPersistenceDAMPriceForecastModel)


def test_module_lag_is_exactly_twenty_four_hours() -> None:
    from energy_trading.ml.dam_price import previous_day_persistence as module

    assert module._LAG == timedelta(hours=24)
    target = datetime(2026, 10, 1, 16, 0, 0, tzinfo=UTC)
    lag_timestamp = target - module._LAG
    assert lag_timestamp == datetime(2026, 9, 30, 16, 0, 0, tzinfo=UTC)
    assert target - lag_timestamp == timedelta(hours=24)
    assert lag_timestamp.hour == target.hour
