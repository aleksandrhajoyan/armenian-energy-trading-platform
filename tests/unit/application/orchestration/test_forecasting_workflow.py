"""Framework-neutral forecasting workflow step composition."""

from __future__ import annotations

import inspect
from datetime import date

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.orchestration import (
    ForecastingExecutionPort,
    ForecastingPlan,
    ForecastingSuccess,
    ForecastingWorkflowContextPort,
    ForecastingWorkflowStep,
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
)
from energy_trading.application.ports.consumer_load_forecast_model import (
    ConsumerLoadForecastModelRequest,
)
from energy_trading.application.ports.dam_price_forecast_model import (
    DAMPriceForecastModelRequest,
)
from energy_trading.domain.models.forecasting import LoadForecastPoint, PriceForecastPoint
from energy_trading.domain.models.ingestion import AdapterDiagnostic, DiagnosticSeverity
from energy_trading.domain.models.observations import MarketPriceRecord
from tests.unit.domain._factories import amd_price, consumption, diagnostic, utc


class _RecordingContextFake:
    """Test-only fake that structurally satisfies the context Protocol."""

    def __init__(
        self,
        plan: ForecastingPlan,
        calls: list[str],
        resolve_error: Exception | None = None,
        record_error: Exception | None = None,
    ) -> None:
        self._plan = plan
        self.calls = calls
        self.resolve_error = resolve_error
        self.record_error = record_error
        self.resolve_calls = 0
        self.record_calls = 0
        self.received_resolve_state: WorkflowState | None = None
        self.received_record_state: WorkflowState | None = None
        self.received_success: ForecastingSuccess | None = None

    async def resolve_plan(self, *, state: WorkflowState) -> ForecastingPlan:
        self.resolve_calls += 1
        self.received_resolve_state = state
        self.calls.append("resolve_plan")
        if self.resolve_error is not None:
            raise self.resolve_error
        return self._plan

    async def record_success(
        self,
        *,
        state: WorkflowState,
        success: ForecastingSuccess,
    ) -> None:
        self.record_calls += 1
        self.received_record_state = state
        self.received_success = success
        self.calls.append("record_success")
        if self.record_error is not None:
            raise self.record_error


class _RecordingExecutorFake:
    """Test-only fake that structurally satisfies the execution Protocol."""

    def __init__(
        self,
        success: ForecastingSuccess,
        calls: list[str],
        error: Exception | None = None,
    ) -> None:
        self._success = success
        self.calls = calls
        self.error = error
        self.execute_calls = 0
        self.received_plan: ForecastingPlan | None = None

    async def execute(self, *, plan: ForecastingPlan) -> ForecastingSuccess:
        self.execute_calls += 1
        self.received_plan = plan
        self.calls.append("execute")
        if self.error is not None:
            raise self.error
        return self._success


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


def _state(**overrides: object) -> WorkflowState:
    values: dict[str, object] = {
        "workflow_id": "workflow-1",
        "portfolio_id": "portfolio-1",
        "delivery_date": date(2026, 10, 1),
        "correlation_id": "corr-1",
        "phase": WorkflowPhase.FORECASTING,
        "status": WorkflowStatus.RUNNING,
        "diagnostics": (diagnostic(code="existing"),),
    }
    values.update(overrides)
    return WorkflowState(**values)  # type: ignore[arg-type]


def _step(
    context: _RecordingContextFake,
    executor: _RecordingExecutorFake,
) -> ForecastingWorkflowStep:
    return ForecastingWorkflowStep(context=context, executor=executor)


def test_fakes_do_not_inherit_production_bases() -> None:
    assert ForecastingWorkflowContextPort not in _RecordingContextFake.__mro__
    assert ForecastingExecutionPort not in _RecordingExecutorFake.__mro__
    assert not any(
        base.__name__
        in {
            "ForecastingWorkflowContextPort",
            "ForecastingExecutionPort",
            "ForecastingWorkflowStep",
            "Protocol",
        }
        for base in (*_RecordingContextFake.__bases__, *_RecordingExecutorFake.__bases__)
    )


def test_step_can_be_constructed_with_typed_context_and_execution_dependencies() -> None:
    calls: list[str] = []
    context: ForecastingWorkflowContextPort = _RecordingContextFake(_plan(), calls)
    executor: ForecastingExecutionPort = _RecordingExecutorFake(_success(), calls)
    step = ForecastingWorkflowStep(context=context, executor=executor)
    assert isinstance(step, ForecastingWorkflowStep)


def test_step_public_surface_is_async_run_with_two_port_dependencies() -> None:
    defined_methods = {
        name
        for name, value in vars(ForecastingWorkflowStep).items()
        if callable(value) and not name.startswith("_")
    }
    assert defined_methods == {"run"}
    assert inspect.iscoroutinefunction(ForecastingWorkflowStep.run)
    parameters = inspect.signature(ForecastingWorkflowStep.run).parameters
    assert tuple(parameters) == ("self", "state")
    constructor = inspect.signature(ForecastingWorkflowStep.__init__).parameters
    assert tuple(constructor) == ("self", "context", "executor")
    forbidden = {
        "failure_policy",
        "failure_policy_port",
        "graph",
        "consumer_load_forecast",
        "dam_price_forecast",
        "concurrent_executor",
        "plan",
        "success",
    }
    assert forbidden.isdisjoint(constructor)


async def test_successful_run_resolves_executes_and_records_in_order() -> None:
    plan = _plan()
    success = _success()
    calls: list[str] = []
    context = _RecordingContextFake(plan, calls)
    executor = _RecordingExecutorFake(success, calls)
    state = _state()
    returned = await _step(context, executor).run(state)
    assert calls == ["resolve_plan", "execute", "record_success"]
    assert context.resolve_calls == 1
    assert executor.execute_calls == 1
    assert context.record_calls == 1
    assert context.received_resolve_state is state
    assert executor.received_plan is plan
    assert context.received_success is success
    assert context.received_record_state is state
    assert returned is state


async def test_successful_run_preserves_workflow_state_identity_and_values() -> None:
    plan = _plan()
    success = _success()
    calls: list[str] = []
    diagnostics = (diagnostic(code="kept", severity=DiagnosticSeverity.WARNING),)
    state = _state(
        workflow_id="workflow-kept",
        portfolio_id="portfolio-kept",
        delivery_date=date(2026, 11, 2),
        correlation_id="corr-kept",
        phase=WorkflowPhase.FORECASTING,
        status=WorkflowStatus.RUNNING,
        diagnostics=diagnostics,
    )
    returned = await _step(
        _RecordingContextFake(plan, calls),
        _RecordingExecutorFake(success, calls),
    ).run(state)
    assert returned is state
    assert returned.workflow_id == "workflow-kept"
    assert returned.portfolio_id == "portfolio-kept"
    assert returned.delivery_date == date(2026, 11, 2)
    assert returned.correlation_id == "corr-kept"
    assert returned.phase is WorkflowPhase.FORECASTING
    assert returned.status is WorkflowStatus.RUNNING
    assert returned.diagnostics is diagnostics
    assert isinstance(returned.diagnostics[0], AdapterDiagnostic)


async def test_step_depends_on_execution_port_not_a_concrete_executor() -> None:
    plan = _plan()
    success = _success()
    calls: list[str] = []
    executor = _RecordingExecutorFake(success, calls)
    port: ForecastingExecutionPort = executor
    context: ForecastingWorkflowContextPort = _RecordingContextFake(plan, calls)
    step = ForecastingWorkflowStep(context=context, executor=port)
    returned = await step.run(_state())
    assert executor.received_plan is plan
    assert returned.phase is WorkflowPhase.FORECASTING
    assert returned.status is WorkflowStatus.RUNNING


async def test_resolve_failure_propagates_and_prevents_execute_and_record() -> None:
    plan = _plan()
    success = _success()
    calls: list[str] = []
    error = DependencyUnavailableError("plan unavailable")
    context = _RecordingContextFake(plan, calls, resolve_error=error)
    executor = _RecordingExecutorFake(success, calls)
    state = _state()
    try:
        await _step(context, executor).run(state)
    except DependencyUnavailableError as raised:
        assert raised is error
    else:
        raise AssertionError("resolve failure must propagate")
    assert calls == ["resolve_plan"]
    assert context.resolve_calls == 1
    assert executor.execute_calls == 0
    assert context.record_calls == 0
    assert executor.received_plan is None
    assert context.received_success is None


async def test_execution_failure_propagates_and_prevents_record() -> None:
    plan = _plan()
    success = _success()
    calls: list[str] = []
    error = DependencyUnavailableError("execution unavailable")
    context = _RecordingContextFake(plan, calls)
    executor = _RecordingExecutorFake(success, calls, error=error)
    try:
        await _step(context, executor).run(_state())
    except DependencyUnavailableError as raised:
        assert raised is error
    else:
        raise AssertionError("execution failure must propagate")
    assert calls == ["resolve_plan", "execute"]
    assert context.resolve_calls == 1
    assert executor.execute_calls == 1
    assert context.record_calls == 0
    assert executor.received_plan is plan
    assert context.received_success is None


async def test_record_failure_propagates_after_resolve_and_execute() -> None:
    plan = _plan()
    success = _success()
    calls: list[str] = []
    error = DependencyUnavailableError("record unavailable")
    context = _RecordingContextFake(plan, calls, record_error=error)
    executor = _RecordingExecutorFake(success, calls)
    try:
        await _step(context, executor).run(_state())
    except DependencyUnavailableError as raised:
        assert raised is error
    else:
        raise AssertionError("record failure must propagate")
    assert calls == ["resolve_plan", "execute", "record_success"]
    assert context.resolve_calls == 1
    assert executor.execute_calls == 1
    assert context.record_calls == 1
    assert context.received_success is success


async def test_failures_are_not_retried() -> None:
    plan = _plan()
    success = _success()
    resolve_calls: list[str] = []
    execute_calls: list[str] = []
    record_calls: list[str] = []
    resolve_error = DependencyUnavailableError("resolve failed")
    execute_error = DependencyUnavailableError("execute failed")
    record_error = DependencyUnavailableError("record failed")
    resolve_context = _RecordingContextFake(plan, resolve_calls, resolve_error=resolve_error)
    resolve_executor = _RecordingExecutorFake(success, resolve_calls)
    try:
        await _step(resolve_context, resolve_executor).run(_state())
    except DependencyUnavailableError:
        pass
    else:
        raise AssertionError("resolve failure must propagate")
    execute_context = _RecordingContextFake(plan, execute_calls)
    execute_executor = _RecordingExecutorFake(success, execute_calls, error=execute_error)
    try:
        await _step(execute_context, execute_executor).run(_state())
    except DependencyUnavailableError:
        pass
    else:
        raise AssertionError("execution failure must propagate")
    record_context = _RecordingContextFake(plan, record_calls, record_error=record_error)
    record_executor = _RecordingExecutorFake(success, record_calls)
    try:
        await _step(record_context, record_executor).run(_state())
    except DependencyUnavailableError:
        pass
    else:
        raise AssertionError("record failure must propagate")
    assert resolve_context.resolve_calls == 1
    assert resolve_executor.execute_calls == 0
    assert execute_context.resolve_calls == 1
    assert execute_executor.execute_calls == 1
    assert execute_context.record_calls == 0
    assert record_context.resolve_calls == 1
    assert record_executor.execute_calls == 1
    assert record_context.record_calls == 1
