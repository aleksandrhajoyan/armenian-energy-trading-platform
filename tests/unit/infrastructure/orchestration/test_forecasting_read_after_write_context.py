"""Process-local in-memory read-after-write forecasting context adapter."""

from __future__ import annotations

import asyncio
import inspect
from datetime import date

import pytest

from energy_trading.application.errors import ConflictError, ResourceNotFoundError
from energy_trading.application.orchestration import (
    ForecastingPlan,
    ForecastingSuccess,
    ForecastingWorkflowContextPort,
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
)
from energy_trading.application.orchestration.forecasting_success_read import (
    ForecastingSuccessReadPort,
)
from energy_trading.application.orchestration.forecasting_workflow import ForecastingWorkflowStep
from energy_trading.application.ports.consumer_load_forecast_model import (
    ConsumerLoadForecastModelRequest,
)
from energy_trading.application.ports.dam_price_forecast_model import (
    DAMPriceForecastModelRequest,
)
from energy_trading.domain.models.forecasting import LoadForecastPoint, PriceForecastPoint
from energy_trading.domain.models.observations import MarketPriceRecord
from energy_trading.infrastructure.orchestration.forecasting_context import (
    InMemoryForecastingWorkflowContext,
)
from energy_trading.infrastructure.orchestration.forecasting_read_after_write_context import (
    InMemoryForecastingReadAfterWriteContext,
)
from energy_trading.infrastructure.orchestration.forecasting_success_reader import (
    InMemoryForecastingSuccessReader,
)
from tests.unit.domain._factories import amd_price, consumption, utc

_WORKFLOW_ID = "workflow-forecasting-1"
_OTHER_WORKFLOW_ID = "workflow-forecasting-2"
_MISSING_WORKFLOW_ID = "workflow-id-sentinel-MUST-NOT-LEAK"
_MSG_SUCCESS_NOT_FOUND = "Forecasting success was not found."


def _load_request(*, consumer_id: str = "consumer-1") -> ConsumerLoadForecastModelRequest:
    return ConsumerLoadForecastModelRequest(
        forecast_run_id="run-1",
        generated_at=utc(),
        consumer_id=consumer_id,
        history=(consumption(consumer_id=consumer_id),),
        target_timestamps=(utc(hour=16),),
    )


def _dam_request(*, market_id: str = "market-1") -> DAMPriceForecastModelRequest:
    market = MarketPriceRecord.model_validate(
        {
            "market_id": market_id,
            "timestamp": utc(),
            "price": amd_price(),
        }
    )
    return DAMPriceForecastModelRequest(
        forecast_run_id="forecast-run-1",
        generated_at=utc(hour=9),
        market_id=market_id,
        currency="AMD",
        history=(market,),
        target_timestamps=(utc(hour=16),),
    )


def _plan(*, consumer_id: str = "consumer-1", market_id: str = "market-1") -> ForecastingPlan:
    return ForecastingPlan(
        consumer_load_request=_load_request(consumer_id=consumer_id),
        dam_price_request=_dam_request(market_id=market_id),
    )


def _load_point(*, value_mw: float = 3.25, consumer_id: str = "consumer-1") -> LoadForecastPoint:
    return LoadForecastPoint.model_validate(
        {
            "forecast_run_id": "run-1",
            "consumer_id": consumer_id,
            "generated_at": utc(),
            "target_timestamp": utc(hour=16),
            "value_mw": value_mw,
        }
    )


def _price_point(*, amount: str = "45.00", market_id: str = "market-1") -> PriceForecastPoint:
    return PriceForecastPoint.model_validate(
        {
            "forecast_run_id": "run-1",
            "market_id": market_id,
            "generated_at": utc(),
            "target_timestamp": utc(hour=16),
            "price": amd_price(amount),
        }
    )


def _success() -> ForecastingSuccess:
    return ForecastingSuccess(
        consumer_load_forecast=(_load_point(),),
        dam_price_forecast=(_price_point(),),
    )


def _other_success() -> ForecastingSuccess:
    return ForecastingSuccess(
        consumer_load_forecast=(_load_point(value_mw=7.5, consumer_id="consumer-2"),),
        dam_price_forecast=(_price_point(amount="-12.00", market_id="market-2"),),
    )


def _state(*, workflow_id: str = _WORKFLOW_ID) -> WorkflowState:
    return WorkflowState(
        workflow_id=workflow_id,
        portfolio_id="portfolio-1",
        delivery_date=date(2026, 10, 1),
        correlation_id="corr-1",
        phase=WorkflowPhase.FORECASTING,
        status=WorkflowStatus.RUNNING,
    )


def _wrapper(
    plans: dict[str, ForecastingPlan] | None = None,
) -> tuple[InMemoryForecastingReadAfterWriteContext, InMemoryForecastingWorkflowContext]:
    context = InMemoryForecastingWorkflowContext({} if plans is None else plans)
    return InMemoryForecastingReadAfterWriteContext(context=context), context


def _as_context_port(
    wrapper: InMemoryForecastingReadAfterWriteContext,
) -> ForecastingWorkflowContextPort:
    """Application-shaped call site: only the context port type is accepted."""

    return wrapper


def _as_read_port(wrapper: InMemoryForecastingReadAfterWriteContext) -> ForecastingSuccessReadPort:
    """Application-shaped call site: only the read port type is accepted."""

    return wrapper


class _RecordingSpyContext(InMemoryForecastingWorkflowContext):
    """Test-only delegate that counts calls and forwards exact arguments."""

    def __init__(self, plans: dict[str, ForecastingPlan]) -> None:
        super().__init__(plans)
        self.resolve_calls: list[WorkflowState] = []
        self.record_calls: list[tuple[WorkflowState, ForecastingSuccess]] = []

    async def resolve_plan(self, *, state: WorkflowState) -> ForecastingPlan:
        self.resolve_calls.append(state)
        return await super().resolve_plan(state=state)

    async def record_success(
        self,
        *,
        state: WorkflowState,
        success: ForecastingSuccess,
    ) -> None:
        self.record_calls.append((state, success))
        await super().record_success(state=state, success=success)


class _FailingRecordContext(InMemoryForecastingWorkflowContext):
    """Test-only delegate whose record operation fails before accepting."""

    def __init__(self, error: Exception) -> None:
        super().__init__({})
        self.error = error

    async def record_success(
        self,
        *,
        state: WorkflowState,
        success: ForecastingSuccess,
    ) -> None:
        raise self.error


class _GatedRecordContext(InMemoryForecastingWorkflowContext):
    """Test-only delegate that pauses inside record until released."""

    def __init__(self, *, fail_with: Exception | None = None) -> None:
        super().__init__({})
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.fail_with = fail_with

    async def record_success(
        self,
        *,
        state: WorkflowState,
        success: ForecastingSuccess,
    ) -> None:
        self.entered.set()
        await self.release.wait()
        if self.fail_with is not None:
            raise self.fail_with
        await super().record_success(state=state, success=success)


class _FixedSuccessExecutor:
    """Test-only structural ``ForecastingExecutionPort`` returning one object."""

    def __init__(self, success: ForecastingSuccess) -> None:
        self.success = success
        self.plans: list[ForecastingPlan] = []

    async def execute(self, *, plan: ForecastingPlan) -> ForecastingSuccess:
        self.plans.append(plan)
        return self.success


def test_wrapper_structurally_satisfies_both_application_ports() -> None:
    wrapper, _ = _wrapper()
    assert _as_context_port(wrapper) is wrapper
    assert _as_read_port(wrapper) is wrapper
    assert InMemoryForecastingReadAfterWriteContext.__bases__ == (object,)
    mro = InMemoryForecastingReadAfterWriteContext.__mro__
    assert ForecastingWorkflowContextPort not in mro
    assert ForecastingSuccessReadPort not in mro
    expected = {
        "resolve_plan": ("self", "state"),
        "record_success": ("self", "state", "success"),
        "get_success": ("self", "workflow_id"),
    }
    for name, parameters in expected.items():
        method = getattr(InMemoryForecastingReadAfterWriteContext, name)
        assert inspect.iscoroutinefunction(method)
        signature = inspect.signature(method)
        assert tuple(signature.parameters) == parameters
        for parameter in list(signature.parameters.values())[1:]:
            assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
            assert parameter.default is inspect.Parameter.empty


def test_constructor_requires_keyword_only_context() -> None:
    signature = inspect.signature(InMemoryForecastingReadAfterWriteContext.__init__)
    assert tuple(signature.parameters) == ("self", "context")
    parameter = signature.parameters["context"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is inspect.Parameter.empty
    context = InMemoryForecastingWorkflowContext({})
    with pytest.raises(TypeError):
        InMemoryForecastingReadAfterWriteContext(context)  # type: ignore[misc]
    with pytest.raises(TypeError):
        InMemoryForecastingReadAfterWriteContext()  # type: ignore[call-arg]


async def test_resolve_plan_forwards_exact_state_and_returns_exact_plan() -> None:
    plan = _plan()
    context = _RecordingSpyContext({_WORKFLOW_ID: plan})
    wrapper = InMemoryForecastingReadAfterWriteContext(context=context)
    state = _state()
    resolved = await _as_context_port(wrapper).resolve_plan(state=state)
    assert resolved is plan
    assert len(context.resolve_calls) == 1
    assert context.resolve_calls[0] is state


async def test_resolve_plan_preserves_underlying_missing_plan_error() -> None:
    wrapper, _ = _wrapper()
    with pytest.raises(ResourceNotFoundError) as exc_info:
        await wrapper.resolve_plan(state=_state(workflow_id=_MISSING_WORKFLOW_ID))
    assert exc_info.value.message == "Forecasting plan was not found."
    assert _MISSING_WORKFLOW_ID not in f"{exc_info.value!s} {exc_info.value!r}"


async def test_get_success_before_any_record_fails_closed() -> None:
    wrapper, _ = _wrapper()
    with pytest.raises(ResourceNotFoundError) as exc_info:
        await _as_read_port(wrapper).get_success(workflow_id=_WORKFLOW_ID)
    assert exc_info.value.message == _MSG_SUCCESS_NOT_FOUND


async def test_record_delegates_once_with_exact_arguments() -> None:
    context = _RecordingSpyContext({})
    wrapper = InMemoryForecastingReadAfterWriteContext(context=context)
    state = _state()
    success = _success()
    await wrapper.record_success(state=state, success=success)
    assert len(context.record_calls) == 1
    recorded_state, recorded_success = context.record_calls[0]
    assert recorded_state is state
    assert recorded_success is success


async def test_successful_record_is_readable_as_the_exact_same_object() -> None:
    wrapper, _ = _wrapper()
    success = _success()
    await _as_context_port(wrapper).record_success(state=_state(), success=success)
    resolved = await _as_read_port(wrapper).get_success(workflow_id=_WORKFLOW_ID)
    assert resolved is success


async def test_forecast_tuples_and_points_keep_identity_and_values() -> None:
    wrapper, _ = _wrapper()
    success = _success()
    load_forecast = success.consumer_load_forecast
    dam_forecast = success.dam_price_forecast
    await wrapper.record_success(state=_state(), success=success)
    resolved = await wrapper.get_success(workflow_id=_WORKFLOW_ID)
    assert resolved.consumer_load_forecast is load_forecast
    assert resolved.dam_price_forecast is dam_forecast
    assert resolved.consumer_load_forecast[0] is load_forecast[0]
    assert resolved.dam_price_forecast[0] is dam_forecast[0]
    assert resolved.consumer_load_forecast == (_load_point(),)
    assert resolved.dam_price_forecast == (_price_point(),)
    assert resolved == _success()


async def test_equal_retry_succeeds_without_replacing_the_exposed_object() -> None:
    wrapper, _ = _wrapper()
    original = _success()
    retry = _success()
    assert retry == original
    assert retry is not original
    await wrapper.record_success(state=_state(), success=original)
    await wrapper.record_success(state=_state(), success=retry)
    assert await wrapper.get_success(workflow_id=_WORKFLOW_ID) is original


async def test_conflicting_retry_propagates_conflict_and_keeps_original() -> None:
    wrapper, _ = _wrapper()
    original = _success()
    await wrapper.record_success(state=_state(), success=original)
    with pytest.raises(ConflictError) as exc_info:
        await wrapper.record_success(state=_state(), success=_other_success())
    assert exc_info.value.message == "Forecasting success conflicts with the recorded result."
    assert await wrapper.get_success(workflow_id=_WORKFLOW_ID) is original


async def test_independent_workflow_ids_remain_isolated() -> None:
    wrapper, _ = _wrapper()
    first = _success()
    second = _other_success()
    await wrapper.record_success(state=_state(), success=first)
    await wrapper.record_success(state=_state(workflow_id=_OTHER_WORKFLOW_ID), success=second)
    assert await wrapper.get_success(workflow_id=_WORKFLOW_ID) is first
    assert await wrapper.get_success(workflow_id=_OTHER_WORKFLOW_ID) is second


async def test_unknown_and_near_miss_ids_fail_closed_without_leaking_data() -> None:
    wrapper, _ = _wrapper()
    await wrapper.record_success(state=_state(), success=_success())
    for missing in (
        _MISSING_WORKFLOW_ID,
        f" {_WORKFLOW_ID}",
        f"{_WORKFLOW_ID} ",
        _WORKFLOW_ID.upper(),
        "workflow-forecasting",
        f"{_WORKFLOW_ID}-x",
    ):
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await wrapper.get_success(workflow_id=missing)
        error = exc_info.value
        assert error.message == _MSG_SUCCESS_NOT_FOUND
        assert error.__cause__ is None
        assert error.__suppress_context__ is True
        rendered = f"{error!s} {error!r} {error.args!r}"
        assert missing.strip() not in rendered
        assert _WORKFLOW_ID not in rendered
        assert "portfolio-1" not in rendered
        assert "consumer-1" not in rendered
        assert "market-1" not in rendered
        assert "45" not in rendered
        assert "3.25" not in rendered


async def test_separately_constructed_wrappers_do_not_share_records() -> None:
    first, _ = _wrapper()
    second, _ = _wrapper()
    success = _success()
    await first.record_success(state=_state(), success=success)
    assert await first.get_success(workflow_id=_WORKFLOW_ID) is success
    with pytest.raises(ResourceNotFoundError):
        await second.get_success(workflow_id=_WORKFLOW_ID)


async def test_failed_record_publishes_nothing_and_keeps_original_exception() -> None:
    error = ConflictError("Forecasting success conflicts with the recorded result.")
    wrapper = InMemoryForecastingReadAfterWriteContext(context=_FailingRecordContext(error))
    with pytest.raises(ConflictError) as exc_info:
        await wrapper.record_success(state=_state(), success=_success())
    assert exc_info.value is error
    with pytest.raises(ResourceNotFoundError):
        await wrapper.get_success(workflow_id=_WORKFLOW_ID)


async def test_direct_writes_on_wrapped_context_are_not_visible_through_wrapper() -> None:
    wrapper, context = _wrapper()
    success = _success()
    await context.record_success(state=_state(), success=success)
    with pytest.raises(ResourceNotFoundError):
        await wrapper.get_success(workflow_id=_WORKFLOW_ID)
    retry = _success()
    await wrapper.record_success(state=_state(), success=retry)
    assert await wrapper.get_success(workflow_id=_WORKFLOW_ID) is retry
    with pytest.raises(ConflictError):
        await wrapper.record_success(state=_state(), success=_other_success())
    assert await wrapper.get_success(workflow_id=_WORKFLOW_ID) is retry


async def test_snapshot_reader_does_not_observe_wrapper_writes() -> None:
    wrapper, _ = _wrapper()
    supplied: dict[str, ForecastingSuccess] = {}
    reader = InMemoryForecastingSuccessReader(successes=supplied)
    success = _success()
    await wrapper.record_success(state=_state(), success=success)
    assert await wrapper.get_success(workflow_id=_WORKFLOW_ID) is success
    with pytest.raises(ResourceNotFoundError):
        await reader.get_success(workflow_id=_WORKFLOW_ID)
    assert supplied == {}


async def test_record_and_read_leave_workflow_state_unchanged() -> None:
    wrapper, _ = _wrapper({_WORKFLOW_ID: _plan()})
    state = _state()
    original_phase = state.phase
    original_status = state.status
    original_diagnostics = state.diagnostics
    await wrapper.resolve_plan(state=state)
    await wrapper.record_success(state=state, success=_success())
    await wrapper.get_success(workflow_id=state.workflow_id)
    assert state.workflow_id == _WORKFLOW_ID
    assert state.phase is original_phase
    assert state.status is original_status
    assert state.diagnostics is original_diagnostics
    assert "forecasting_success" not in state.__slots__


async def _start_gated_read(
    wrapper: InMemoryForecastingReadAfterWriteContext,
) -> asyncio.Task[ForecastingSuccess]:
    """Start a read and return once it is blocked on the wrapper's lock."""

    read_started = asyncio.Event()

    async def _read() -> ForecastingSuccess:
        read_started.set()
        return await wrapper.get_success(workflow_id=_WORKFLOW_ID)

    task = asyncio.create_task(_read())
    await read_started.wait()
    return task


async def test_read_cannot_observe_success_before_delegated_record_finishes() -> None:
    context = _GatedRecordContext()
    wrapper = InMemoryForecastingReadAfterWriteContext(context=context)
    success = _success()
    record_task = asyncio.create_task(wrapper.record_success(state=_state(), success=success))
    read_task: asyncio.Task[ForecastingSuccess] | None = None
    try:
        await context.entered.wait()
        read_task = await _start_gated_read(wrapper)
        assert not read_task.done()
        assert not record_task.done()
        context.release.set()
        await record_task
        assert await read_task is success
    finally:
        context.release.set()
        for task in (record_task, read_task):
            if task is not None and not task.done():
                task.cancel()
        await asyncio.gather(
            *(task for task in (record_task, read_task) if task is not None),
            return_exceptions=True,
        )


async def test_read_waiting_on_failed_record_fails_closed() -> None:
    error = ConflictError("Forecasting success conflicts with the recorded result.")
    context = _GatedRecordContext(fail_with=error)
    wrapper = InMemoryForecastingReadAfterWriteContext(context=context)
    record_task = asyncio.create_task(wrapper.record_success(state=_state(), success=_success()))
    read_task: asyncio.Task[ForecastingSuccess] | None = None
    try:
        await context.entered.wait()
        read_task = await _start_gated_read(wrapper)
        assert not read_task.done()
        context.release.set()
        with pytest.raises(ConflictError) as record_info:
            await record_task
        assert record_info.value is error
        with pytest.raises(ResourceNotFoundError):
            await read_task
    finally:
        context.release.set()
        for task in (record_task, read_task):
            if task is not None and not task.done():
                task.cancel()
        await asyncio.gather(
            *(task for task in (record_task, read_task) if task is not None),
            return_exceptions=True,
        )


async def test_real_workflow_step_round_trip_preserves_success_and_state() -> None:
    plan = _plan()
    success = _success()
    wrapper, _ = _wrapper({_WORKFLOW_ID: plan})
    executor = _FixedSuccessExecutor(success)
    step = ForecastingWorkflowStep(context=wrapper, executor=executor)
    state = _state()
    snapshot = (
        state.workflow_id,
        state.portfolio_id,
        state.delivery_date,
        state.correlation_id,
        state.phase,
        state.status,
        state.diagnostics,
    )
    returned = await step.run(state)
    assert returned is state
    assert (
        returned.workflow_id,
        returned.portfolio_id,
        returned.delivery_date,
        returned.correlation_id,
        returned.phase,
        returned.status,
        returned.diagnostics,
    ) == snapshot
    assert len(executor.plans) == 1
    assert executor.plans[0] is plan
    reader = _as_read_port(wrapper)
    assert await reader.get_success(workflow_id=state.workflow_id) is success
