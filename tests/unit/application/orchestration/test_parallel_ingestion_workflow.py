"""Framework-neutral parallel-ingestion workflow step composition."""

from __future__ import annotations

import inspect
from datetime import UTC, date, datetime
from decimal import Decimal

from energy_trading.application.agents.generation_availability import (
    GenerationAvailabilityRequest,
    GenerationAvailabilityResult,
)
from energy_trading.application.agents.hydro_resources import (
    HydroResourcesRequest,
    HydroResourcesResult,
)
from energy_trading.application.agents.market_monitoring import (
    MarketMonitoringRequest,
    MarketMonitoringResult,
)
from energy_trading.application.agents.news_intelligence import (
    NewsIntelligenceRequest,
    NewsIntelligenceResult,
)
from energy_trading.application.agents.weather_and_renewable_forecast import (
    WeatherAndRenewableForecastRequest,
    WeatherAndRenewableForecastResult,
)
from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.orchestration import (
    ConcurrentParallelIngestionExecutor,
    ParallelIngestionExecutionPort,
    ParallelIngestionPlan,
    ParallelIngestionSuccess,
    ParallelIngestionWorkflowContextPort,
    ParallelIngestionWorkflowStep,
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
)
from energy_trading.domain.models.ingestion import AdapterDiagnostic, DiagnosticSeverity
from energy_trading.domain.models.observations import (
    GenerationAvailabilityRecord,
    GenerationStatus,
    HydroRecord,
    MarketPriceRecord,
    NewsEvent,
    WeatherRecord,
)
from energy_trading.domain.value_objects.money import EnergyPrice
from tests.unit.domain._factories import diagnostic


class _RecordingContextFake:
    """Test-only fake that structurally satisfies the context Protocol."""

    def __init__(
        self,
        plan: ParallelIngestionPlan,
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
        self.received_resolve_workflow_id: str | None = None
        self.received_record_workflow_id: str | None = None
        self.received_success: ParallelIngestionSuccess | None = None

    async def resolve_plan(self, workflow_id: str) -> ParallelIngestionPlan:
        self.resolve_calls += 1
        self.received_resolve_workflow_id = workflow_id
        self.calls.append("resolve_plan")
        if self.resolve_error is not None:
            raise self.resolve_error
        return self._plan

    async def record_success(self, workflow_id: str, success: ParallelIngestionSuccess) -> None:
        self.record_calls += 1
        self.received_record_workflow_id = workflow_id
        self.received_success = success
        self.calls.append("record_success")
        if self.record_error is not None:
            raise self.record_error


class _RecordingExecutorFake:
    """Test-only fake that structurally satisfies the execution Protocol."""

    def __init__(
        self,
        success: ParallelIngestionSuccess,
        calls: list[str],
        error: Exception | None = None,
    ) -> None:
        self._success = success
        self.calls = calls
        self.error = error
        self.execute_calls = 0
        self.received_plan: ParallelIngestionPlan | None = None

    async def execute(self, plan: ParallelIngestionPlan) -> ParallelIngestionSuccess:
        self.execute_calls += 1
        self.received_plan = plan
        self.calls.append("execute")
        if self.error is not None:
            raise self.error
        return self._success


def _weather_request() -> WeatherAndRenewableForecastRequest:
    return WeatherAndRenewableForecastRequest(
        location_id="loc-1",
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )


def _hydro_request() -> HydroResourcesRequest:
    return HydroResourcesRequest(
        resource_id="hydro-1",
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )


def _generation_request() -> GenerationAvailabilityRequest:
    return GenerationAvailabilityRequest(
        asset_id="asset-1",
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )


def _news_request() -> NewsIntelligenceRequest:
    return NewsIntelligenceRequest(
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )


def _market_request() -> MarketMonitoringRequest:
    return MarketMonitoringRequest(
        market_id="market-1",
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )


def _plan() -> ParallelIngestionPlan:
    return ParallelIngestionPlan(
        weather_and_renewable_forecast=_weather_request(),
        hydro_resources=_hydro_request(),
        generation_availability=_generation_request(),
        news_intelligence=_news_request(),
        market_monitoring=_market_request(),
    )


def _success() -> ParallelIngestionSuccess:
    return ParallelIngestionSuccess(
        weather_and_renewable_forecast=WeatherAndRenewableForecastResult(
            records=(
                WeatherRecord.model_validate(
                    {
                        "location_id": "loc-1",
                        "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
                        "temperature_c": 12.5,
                    }
                ),
            )
        ),
        hydro_resources=HydroResourcesResult(
            records=(
                HydroRecord.model_validate(
                    {
                        "resource_id": "hydro-1",
                        "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
                    }
                ),
            )
        ),
        generation_availability=GenerationAvailabilityResult(
            records=(
                GenerationAvailabilityRecord.model_validate(
                    {
                        "asset_id": "asset-1",
                        "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
                        "status": GenerationStatus.AVAILABLE,
                        "available_capacity_mw": 100.0,
                    }
                ),
            )
        ),
        news_intelligence=NewsIntelligenceResult(
            records=(
                NewsEvent.model_validate(
                    {
                        "event_id": "evt-1",
                        "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
                        "headline": "Unit outage announced",
                        "summary": "A generating unit is scheduled offline.",
                    }
                ),
            )
        ),
        market_monitoring=MarketMonitoringResult(
            records=(
                MarketPriceRecord.model_validate(
                    {
                        "market_id": "market-1",
                        "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
                        "price": EnergyPrice(amount_per_mwh=Decimal("45.00"), currency="EUR"),
                    }
                ),
            )
        ),
    )


def _state(**overrides: object) -> WorkflowState:
    values: dict[str, object] = {
        "workflow_id": "workflow-1",
        "portfolio_id": "portfolio-1",
        "delivery_date": date(2026, 10, 1),
        "correlation_id": "corr-1",
        "phase": WorkflowPhase.INGESTION,
        "status": WorkflowStatus.RUNNING,
        "diagnostics": (diagnostic(code="existing"),),
    }
    values.update(overrides)
    return WorkflowState(**values)  # type: ignore[arg-type]


def _step(
    context: _RecordingContextFake,
    executor: _RecordingExecutorFake,
) -> ParallelIngestionWorkflowStep:
    return ParallelIngestionWorkflowStep(context=context, executor=executor)


def test_fakes_do_not_inherit_production_bases() -> None:
    assert ParallelIngestionWorkflowContextPort not in _RecordingContextFake.__mro__
    assert ParallelIngestionExecutionPort not in _RecordingExecutorFake.__mro__
    assert ConcurrentParallelIngestionExecutor not in _RecordingExecutorFake.__mro__
    assert not any(
        base.__name__
        in {
            "ParallelIngestionWorkflowContextPort",
            "ParallelIngestionExecutionPort",
            "ConcurrentParallelIngestionExecutor",
            "Protocol",
        }
        for base in (*_RecordingContextFake.__bases__, *_RecordingExecutorFake.__bases__)
    )


def test_step_public_surface_is_async_run_with_two_port_dependencies() -> None:
    defined_methods = {
        name
        for name, value in vars(ParallelIngestionWorkflowStep).items()
        if callable(value) and not name.startswith("_")
    }
    assert defined_methods == {"run"}
    assert inspect.iscoroutinefunction(ParallelIngestionWorkflowStep.run)
    parameters = inspect.signature(ParallelIngestionWorkflowStep.run).parameters
    assert tuple(parameters) == ("self", "state")
    constructor = inspect.signature(ParallelIngestionWorkflowStep.__init__).parameters
    assert tuple(constructor) == ("self", "context", "executor")
    forbidden = {
        "failure_policy",
        "failure_policy_port",
        "graph",
        "weather_and_renewable_forecast",
        "hydro_resources",
        "generation_availability",
        "news_intelligence",
        "market_monitoring",
        "concurrent_executor",
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
    assert context.received_resolve_workflow_id is state.workflow_id
    assert executor.received_plan is plan
    assert context.received_success is success
    assert context.received_record_workflow_id is state.workflow_id
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
        phase=WorkflowPhase.INGESTION,
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
    assert returned.phase is WorkflowPhase.INGESTION
    assert returned.status is WorkflowStatus.RUNNING
    assert returned.diagnostics is diagnostics
    assert isinstance(returned.diagnostics[0], AdapterDiagnostic)


async def test_step_depends_on_execution_port_not_concrete_executor() -> None:
    plan = _plan()
    success = _success()
    calls: list[str] = []
    executor = _RecordingExecutorFake(success, calls)
    assert not isinstance(executor, ConcurrentParallelIngestionExecutor)
    port: ParallelIngestionExecutionPort = executor
    context: ParallelIngestionWorkflowContextPort = _RecordingContextFake(plan, calls)
    step = ParallelIngestionWorkflowStep(context=context, executor=port)
    returned = await step.run(_state())
    assert executor.received_plan is plan
    assert returned.phase is WorkflowPhase.INGESTION
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
