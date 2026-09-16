"""Concurrent Phase 3 forecasting executor over Consumer Load and DAM agents."""

from __future__ import annotations

import asyncio
import inspect

import pytest

from energy_trading.application.agents.consumer_load_forecast import ConsumerLoadForecastAgent
from energy_trading.application.agents.dam_price_forecast import DAMPriceForecastAgent
from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.orchestration import (
    ForecastingExecutionPort,
    ForecastingPlan,
    ForecastingSuccess,
    ParallelForecastingExecutionService,
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


class _GatedModel:
    """Test-only model fake. Not a production adapter."""

    def __init__(
        self,
        started: asyncio.Event,
        proceed: asyncio.Event,
        points: tuple[object, ...] = (),
        error: Exception | None = None,
    ) -> None:
        self.started = started
        self.proceed = proceed
        self.points = points
        self.error = error
        self.calls: list[object] = []
        self.completed = False
        self.cancelled = False

    async def forecast(self, *, request: object) -> tuple[object, ...]:
        self.calls.append(request)
        self.started.set()
        try:
            await self.proceed.wait()
            if self.error is not None:
                raise self.error
            self.completed = True
            return self.points
        except asyncio.CancelledError:
            self.cancelled = True
            raise


class _ImmediateModel:
    """Test-only model fake. Not a production adapter."""

    def __init__(
        self,
        points: tuple[object, ...] = (),
        error: Exception | None = None,
    ) -> None:
        self.points = points
        self.error = error
        self.calls: list[object] = []

    async def forecast(self, *, request: object) -> tuple[object, ...]:
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        return self.points


def _load_request() -> ConsumerLoadForecastModelRequest:
    return ConsumerLoadForecastModelRequest(
        forecast_run_id="run-1",
        generated_at=utc(),
        consumer_id="consumer-1",
        history=(consumption(),),
        target_timestamps=(utc(hour=16), utc(hour=17)),
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
        target_timestamps=(utc(hour=16), utc(hour=17)),
    )


def _plan(
    consumer_load_request: ConsumerLoadForecastModelRequest | None = None,
    dam_price_request: DAMPriceForecastModelRequest | None = None,
) -> ForecastingPlan:
    return ForecastingPlan(
        consumer_load_request=(
            consumer_load_request if consumer_load_request is not None else _load_request()
        ),
        dam_price_request=dam_price_request if dam_price_request is not None else _dam_request(),
    )


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


def _as_execution_port(
    executor: ParallelForecastingExecutionService,
) -> ForecastingExecutionPort:
    return executor


def _executor(
    consumer_model: object,
    dam_model: object,
) -> tuple[ParallelForecastingExecutionService, ConsumerLoadForecastAgent, DAMPriceForecastAgent]:
    consumer_agent = ConsumerLoadForecastAgent(consumer_model)  # type: ignore[arg-type]
    dam_agent = DAMPriceForecastAgent(dam_model)  # type: ignore[arg-type]
    executor = ParallelForecastingExecutionService(
        consumer_load_forecast=consumer_agent,
        dam_price_forecast=dam_agent,
    )
    return executor, consumer_agent, dam_agent


def test_executor_does_not_inherit_protocol() -> None:
    assert ForecastingExecutionPort not in ParallelForecastingExecutionService.__mro__
    assert not any(
        base.__name__ in {"ForecastingExecutionPort", "Protocol"}
        for base in ParallelForecastingExecutionService.__bases__
    )


def test_executor_public_surface_is_async_keyword_only_execute() -> None:
    defined_methods = {
        name
        for name, value in vars(ParallelForecastingExecutionService).items()
        if callable(value) and not name.startswith("_")
    }
    assert defined_methods == {"execute"}
    assert inspect.iscoroutinefunction(ParallelForecastingExecutionService.execute)
    parameters = inspect.signature(ParallelForecastingExecutionService.execute).parameters
    assert tuple(parameters) == ("self", "plan")
    assert parameters["plan"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["plan"].annotation is ForecastingPlan
    constructor = inspect.signature(ParallelForecastingExecutionService.__init__).parameters
    assert tuple(constructor) == ("self", "consumer_load_forecast", "dam_price_forecast")


def test_executor_constructor_does_not_accept_context_or_selection() -> None:
    constructor = inspect.signature(ParallelForecastingExecutionService.__init__).parameters
    forbidden = {
        "context",
        "forecasting_workflow_context_port",
        "state",
        "failure_policy",
        "retry",
        "fallback",
        "graph",
        "registry",
        "factory",
        "model",
        "champion",
    }
    assert forbidden.isdisjoint(constructor)


async def test_executor_structurally_satisfies_port_and_preserves_payloads() -> None:
    first_load = _load_point()
    second_load = _load_point(target_timestamp=utc(hour=17), value_mw=4.5)
    first_price = _price_point()
    second_price = _price_point(target_timestamp=utc(hour=17), price=amd_price("46.00"))
    load_points = (first_load, second_load)
    price_points = (first_price, second_price)
    consumer_model = _ImmediateModel(load_points)
    dam_model = _ImmediateModel(price_points)
    executor, _consumer_agent, _dam_agent = _executor(consumer_model, dam_model)
    plan = _plan()
    result = await _as_execution_port(executor).execute(plan=plan)
    assert isinstance(result, ForecastingSuccess)
    assert len(consumer_model.calls) == 1
    assert len(dam_model.calls) == 1
    assert consumer_model.calls[0] is plan.consumer_load_request
    assert dam_model.calls[0] is plan.dam_price_request
    assert result.consumer_load_forecast is load_points
    assert result.dam_price_forecast is price_points
    assert result.consumer_load_forecast[0] is first_load
    assert result.consumer_load_forecast[1] is second_load
    assert result.dam_price_forecast[0] is first_price
    assert result.dam_price_forecast[1] is second_price


async def test_empty_consumer_load_tuple_is_valid_success() -> None:
    price_points = (_price_point(),)
    executor, _consumer_agent, _dam_agent = _executor(
        _ImmediateModel(),
        _ImmediateModel(price_points),
    )
    result = await executor.execute(plan=_plan())
    assert result.consumer_load_forecast == ()
    assert result.dam_price_forecast is price_points


async def test_empty_dam_tuple_is_valid_success() -> None:
    load_points = (_load_point(),)
    executor, _consumer_agent, _dam_agent = _executor(
        _ImmediateModel(load_points),
        _ImmediateModel(),
    )
    result = await executor.execute(plan=_plan())
    assert result.consumer_load_forecast is load_points
    assert result.dam_price_forecast == ()


async def test_both_empty_tuples_are_valid_success() -> None:
    executor, _consumer_agent, _dam_agent = _executor(_ImmediateModel(), _ImmediateModel())
    result = await executor.execute(plan=_plan())
    assert result.consumer_load_forecast == ()
    assert result.dam_price_forecast == ()
    assert isinstance(result, ForecastingSuccess)


async def test_executor_starts_both_branches_before_either_is_released() -> None:
    consumer_started = asyncio.Event()
    dam_started = asyncio.Event()
    proceed = asyncio.Event()
    load_points = (_load_point(),)
    price_points = (_price_point(),)
    consumer_model = _GatedModel(consumer_started, proceed, load_points)
    dam_model = _GatedModel(dam_started, proceed, price_points)
    executor, _consumer_agent, _dam_agent = _executor(consumer_model, dam_model)
    plan = _plan()
    execute_task = asyncio.create_task(executor.execute(plan=plan))
    await consumer_started.wait()
    await dam_started.wait()
    assert len(consumer_model.calls) == 1
    assert len(dam_model.calls) == 1
    assert consumer_model.calls[0] is plan.consumer_load_request
    assert dam_model.calls[0] is plan.dam_price_request
    assert not execute_task.done()
    proceed.set()
    result = await execute_task
    assert isinstance(result, ForecastingSuccess)
    assert result.consumer_load_forecast is load_points
    assert result.dam_price_forecast is price_points
    assert consumer_model.completed
    assert dam_model.completed


async def test_consumer_load_failure_does_not_return_success_and_cancels_dam() -> None:
    consumer_started = asyncio.Event()
    dam_started = asyncio.Event()
    fail_now = asyncio.Event()
    hold = asyncio.Event()
    error = DependencyUnavailableError("consumer load unavailable")
    consumer_model = _GatedModel(consumer_started, fail_now, error=error)
    dam_model = _GatedModel(dam_started, hold, (_price_point(),))
    executor, _consumer_agent, _dam_agent = _executor(consumer_model, dam_model)
    execute_task = asyncio.create_task(executor.execute(plan=_plan()))
    await consumer_started.wait()
    await dam_started.wait()
    assert not execute_task.done()
    fail_now.set()
    with pytest.raises(ExceptionGroup) as exc_info:
        await execute_task
    assert type(exc_info.value) is ExceptionGroup
    assert error in exc_info.value.exceptions
    assert len(consumer_model.calls) == 1
    assert len(dam_model.calls) == 1
    assert dam_model.cancelled
    assert not dam_model.completed
    assert not isinstance(exc_info.value, ForecastingSuccess)


async def test_dam_failure_does_not_return_success_and_cancels_consumer_load() -> None:
    consumer_started = asyncio.Event()
    dam_started = asyncio.Event()
    fail_now = asyncio.Event()
    hold = asyncio.Event()
    error = DependencyUnavailableError("dam price unavailable")
    consumer_model = _GatedModel(consumer_started, hold, (_load_point(),))
    dam_model = _GatedModel(dam_started, fail_now, error=error)
    executor, _consumer_agent, _dam_agent = _executor(consumer_model, dam_model)
    execute_task = asyncio.create_task(executor.execute(plan=_plan()))
    await consumer_started.wait()
    await dam_started.wait()
    assert not execute_task.done()
    fail_now.set()
    with pytest.raises(ExceptionGroup) as exc_info:
        await execute_task
    assert type(exc_info.value) is ExceptionGroup
    assert error in exc_info.value.exceptions
    assert len(consumer_model.calls) == 1
    assert len(dam_model.calls) == 1
    assert consumer_model.cancelled
    assert not consumer_model.completed
    assert not isinstance(exc_info.value, ForecastingSuccess)


async def test_dual_failure_does_not_invent_precedence_or_partial_success() -> None:
    consumer_error = DependencyUnavailableError("consumer load unavailable")
    dam_error = DependencyUnavailableError("dam price unavailable")
    consumer_started = asyncio.Event()
    dam_started = asyncio.Event()
    proceed = asyncio.Event()
    consumer_model = _GatedModel(consumer_started, proceed, error=consumer_error)
    dam_model = _GatedModel(dam_started, proceed, error=dam_error)
    executor, _consumer_agent, _dam_agent = _executor(consumer_model, dam_model)
    execute_task = asyncio.create_task(executor.execute(plan=_plan()))
    await consumer_started.wait()
    await dam_started.wait()
    proceed.set()
    with pytest.raises(ExceptionGroup) as exc_info:
        await execute_task
    assert type(exc_info.value) is ExceptionGroup
    assert not isinstance(exc_info.value, ForecastingSuccess)
    assert not hasattr(exc_info.value, "consumer_load_forecast")
    assert not hasattr(exc_info.value, "dam_price_forecast")
    assert {consumer_error, dam_error} & set(exc_info.value.exceptions)


async def test_executor_does_not_mutate_plan_requests_or_result_items() -> None:
    first_load = _load_point()
    first_price = _price_point()
    load_points = (first_load,)
    price_points = (first_price,)
    consumer_model = _ImmediateModel(load_points)
    dam_model = _ImmediateModel(price_points)
    executor, _consumer_agent, _dam_agent = _executor(consumer_model, dam_model)
    load_request = _load_request()
    dam_request = _dam_request()
    plan = _plan(consumer_load_request=load_request, dam_price_request=dam_request)
    original_load_history = plan.consumer_load_request.history
    original_dam_history = plan.dam_price_request.history
    result = await executor.execute(plan=plan)
    assert plan.consumer_load_request is load_request
    assert plan.dam_price_request is dam_request
    assert plan.consumer_load_request.history is original_load_history
    assert plan.dam_price_request.history is original_dam_history
    assert result.consumer_load_forecast is load_points
    assert result.dam_price_forecast is price_points
    assert result.consumer_load_forecast[0] is first_load
    assert result.dam_price_forecast[0] is first_price
    second = await executor.execute(plan=plan)
    assert second.consumer_load_forecast is load_points
    assert second.dam_price_forecast is price_points
    assert len(consumer_model.calls) == 2
    assert len(dam_model.calls) == 2
