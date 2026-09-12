"""Application-owned forecasting execution port contract."""

from __future__ import annotations

import inspect
from typing import Protocol

from energy_trading.application.orchestration import (
    ForecastingExecutionPort,
    ForecastingPlan,
    ForecastingSuccess,
)
from energy_trading.application.ports.consumer_load_forecast_model import (
    ConsumerLoadForecastModelRequest,
)
from energy_trading.application.ports.dam_price_forecast_model import (
    DAMPriceForecastModelRequest,
)
from energy_trading.domain.models.forecasting import LoadForecastPoint, PriceForecastPoint
from energy_trading.domain.models.observations import MarketPriceRecord
from tests.unit.domain._factories import amd_price, consumption, utc


class _StructuralForecastingExecutionFake:
    """Test-only fake that structurally satisfies ``ForecastingExecutionPort``.

    Not a production executor. Does not inherit a production base class.
    """

    def __init__(self, success: ForecastingSuccess) -> None:
        self._success = success
        self.received: ForecastingPlan | None = None

    async def execute(self, *, plan: ForecastingPlan) -> ForecastingSuccess:
        self.received = plan
        return self._success


def _as_execution_port(
    fake: _StructuralForecastingExecutionFake,
) -> ForecastingExecutionPort:
    """Application-shaped call site: the port type is the only accepted argument."""

    return fake


def _load_request() -> ConsumerLoadForecastModelRequest:
    return ConsumerLoadForecastModelRequest(
        consumer_id="consumer-1",
        history=(consumption(),),
        target_timestamps=(utc(hour=16),),
    )


def _dam_request() -> DAMPriceForecastModelRequest:
    market = MarketPriceRecord.model_validate(
        {
            "market_id": "market-1",
            "timestamp": utc(),
            "price": amd_price(),
        }
    )
    return DAMPriceForecastModelRequest(
        market_id="market-1",
        currency="AMD",
        history=(market,),
        target_timestamps=(utc(hour=16),),
    )


def _plan() -> ForecastingPlan:
    return ForecastingPlan(
        consumer_load_request=_load_request(),
        dam_price_request=_dam_request(),
    )


def _load_point() -> LoadForecastPoint:
    return LoadForecastPoint.model_validate(
        {
            "forecast_run_id": "run-1",
            "consumer_id": "consumer-1",
            "generated_at": utc(),
            "target_timestamp": utc(hour=16),
            "value_mw": 3.25,
        }
    )


def _price_point() -> PriceForecastPoint:
    return PriceForecastPoint.model_validate(
        {
            "forecast_run_id": "run-1",
            "market_id": "market-1",
            "generated_at": utc(),
            "target_timestamp": utc(hour=16),
            "price": amd_price("45.00"),
        }
    )


def _success() -> ForecastingSuccess:
    return ForecastingSuccess(
        consumer_load_forecast=(_load_point(),),
        dam_price_forecast=(_price_point(),),
    )


def test_forecasting_execution_port_exists_and_is_a_protocol() -> None:
    assert issubclass(ForecastingExecutionPort, Protocol)


def test_execution_port_public_method_is_exactly_execute() -> None:
    defined_methods = {
        name
        for name, value in vars(ForecastingExecutionPort).items()
        if callable(value) and not name.startswith("_")
    }
    assert defined_methods == {"execute"}
    forbidden = {
        "run",
        "forecast",
        "execute_parallel",
        "execute_load_then_price",
        "execute_price_then_load",
        "fan_out",
        "fan_in",
        "gather",
        "join",
        "invoke",
        "dispatch",
        "retry",
        "fallback",
        "cancel",
        "close",
        "start",
        "stop",
    }
    assert forbidden.isdisjoint(dir(ForecastingExecutionPort))


def test_execute_is_asynchronous() -> None:
    assert inspect.iscoroutinefunction(ForecastingExecutionPort.execute)


def test_execute_signature_is_keyword_only_plan_with_no_defaults() -> None:
    signature = inspect.signature(ForecastingExecutionPort.execute)
    assert tuple(signature.parameters) == ("self", "plan")
    plan_parameter = signature.parameters["plan"]
    assert plan_parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert plan_parameter.default is inspect.Parameter.empty
    assert plan_parameter.annotation is ForecastingPlan
    assert signature.return_annotation is ForecastingSuccess
    assert not any(
        parameter.kind is inspect.Parameter.VAR_POSITIONAL
        for parameter in signature.parameters.values()
    )
    assert not any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )


def test_execution_port_has_no_generic_type_parameters() -> None:
    assert ForecastingExecutionPort.__parameters__ == ()
    assert ForecastingExecutionPort.__type_params__ == ()


def test_execution_fake_does_not_inherit_production_base() -> None:
    assert ForecastingExecutionPort not in _StructuralForecastingExecutionFake.__mro__
    assert not any(
        base.__name__ in {"ForecastingExecutionPort", "Protocol"}
        for base in _StructuralForecastingExecutionFake.__bases__
    )


async def test_execution_fake_satisfies_port_with_real_plan_and_success() -> None:
    plan = _plan()
    success = _success()
    fake = _StructuralForecastingExecutionFake(success)
    port = _as_execution_port(fake)
    assert inspect.iscoroutinefunction(port.execute)
    result = await port.execute(plan=plan)
    assert result is success
    assert fake.received is plan
    assert isinstance(result, ForecastingSuccess)
    assert isinstance(plan, ForecastingPlan)
