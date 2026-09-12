"""Application-owned forecasting plan contract."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime, timedelta, timezone

import pytest

from energy_trading.application.orchestration import ForecastingPlan
from energy_trading.application.ports.consumer_load_forecast_model import (
    ConsumerLoadForecastModelRequest,
)
from energy_trading.application.ports.dam_price_forecast_model import (
    DAMPriceForecastModelRequest,
)
from energy_trading.domain.models.observations import MarketPriceRecord
from tests.unit.domain._factories import amd_price, consumption, utc


def _load_request(**overrides: object) -> ConsumerLoadForecastModelRequest:
    values: dict[str, object] = {
        "consumer_id": "consumer-1",
        "history": (consumption(),),
        "target_timestamps": (utc(hour=16),),
    }
    values.update(overrides)
    return ConsumerLoadForecastModelRequest(**values)  # type: ignore[arg-type]


def _market(**overrides: object) -> MarketPriceRecord:
    values: dict[str, object] = {
        "market_id": "market-1",
        "timestamp": utc(),
        "price": amd_price(),
    }
    values.update(overrides)
    return MarketPriceRecord.model_validate(values)


def _dam_request(**overrides: object) -> DAMPriceForecastModelRequest:
    values: dict[str, object] = {
        "market_id": "market-1",
        "currency": "AMD",
        "history": (_market(),),
        "target_timestamps": (utc(hour=16),),
    }
    values.update(overrides)
    return DAMPriceForecastModelRequest(**values)  # type: ignore[arg-type]


def test_plan_can_be_constructed_from_existing_request_dtos() -> None:
    load_request = _load_request()
    dam_request = _dam_request()
    plan = ForecastingPlan(
        consumer_load_request=load_request,
        dam_price_request=dam_request,
    )
    assert isinstance(plan.consumer_load_request, ConsumerLoadForecastModelRequest)
    assert isinstance(plan.dam_price_request, DAMPriceForecastModelRequest)


def test_plan_preserves_supplied_request_objects_exactly() -> None:
    load_request = _load_request()
    dam_request = _dam_request()
    plan = ForecastingPlan(
        consumer_load_request=load_request,
        dam_price_request=dam_request,
    )
    assert plan.consumer_load_request is load_request
    assert plan.dam_price_request is dam_request


def test_plan_is_frozen() -> None:
    plan = ForecastingPlan(
        consumer_load_request=_load_request(),
        dam_price_request=_dam_request(),
    )
    with pytest.raises(FrozenInstanceError):
        plan.consumer_load_request = _load_request()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        plan.dam_price_request = _dam_request()  # type: ignore[misc]


def test_plan_is_slotted_and_has_no_instance_dict() -> None:
    plan = ForecastingPlan(
        consumer_load_request=_load_request(),
        dam_price_request=_dam_request(),
    )
    assert hasattr(ForecastingPlan, "__slots__")
    assert not hasattr(plan, "__dict__")


def test_plan_construction_does_not_alter_nested_requests() -> None:
    load_history = (consumption(consumer_id="consumer-west"),)
    load_targets = (utc(hour=12), utc(hour=13))
    load_request = _load_request(
        consumer_id="consumer-west",
        history=load_history,
        target_timestamps=load_targets,
    )
    dam_history = (_market(market_id="market-east"),)
    dam_targets = (utc(hour=18),)
    dam_request = _dam_request(
        market_id="market-east",
        history=dam_history,
        target_timestamps=dam_targets,
    )
    plan = ForecastingPlan(
        consumer_load_request=load_request,
        dam_price_request=dam_request,
    )
    assert plan.consumer_load_request is load_request
    assert plan.dam_price_request is dam_request
    assert plan.consumer_load_request.consumer_id == "consumer-west"
    assert plan.consumer_load_request.history is load_request.history
    assert plan.consumer_load_request.target_timestamps == load_request.target_timestamps
    assert plan.dam_price_request.market_id == "market-east"
    assert plan.dam_price_request.currency == "AMD"
    assert plan.dam_price_request.history is dam_request.history
    assert plan.dam_price_request.target_timestamps == dam_request.target_timestamps


def test_plan_allows_distinct_target_horizons_between_requests() -> None:
    load_request = _load_request(
        consumer_id="consumer-west",
        history=(),
        target_timestamps=(
            datetime(2026, 10, 1, 0, tzinfo=UTC),
            datetime(2026, 10, 1, 1, tzinfo=UTC),
        ),
    )
    dam_request = _dam_request(
        market_id="market-east",
        currency="EUR",
        history=(),
        target_timestamps=(datetime(2026, 10, 2, 12, tzinfo=timezone(timedelta(hours=4))),),
    )
    plan = ForecastingPlan(
        consumer_load_request=load_request,
        dam_price_request=dam_request,
    )
    assert plan.consumer_load_request.target_timestamps != plan.dam_price_request.target_timestamps
    assert len(plan.consumer_load_request.target_timestamps) != len(
        plan.dam_price_request.target_timestamps
    )
    assert plan.consumer_load_request.consumer_id != plan.dam_price_request.market_id
    assert plan.consumer_load_request is load_request
    assert plan.dam_price_request is dam_request


def test_plan_public_fields_are_exactly_the_two_requests() -> None:
    field_names = tuple(item.name for item in fields(ForecastingPlan))
    assert field_names == ("consumer_load_request", "dam_price_request")
