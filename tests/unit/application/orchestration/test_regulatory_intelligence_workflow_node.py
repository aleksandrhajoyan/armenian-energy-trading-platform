"""Framework-neutral Regulatory Intelligence workflow-node adapter."""

from __future__ import annotations

import inspect
from datetime import date

from energy_trading.application.agents.regulatory_intelligence import (
    RegulatoryIntelligenceResult,
)
from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.orchestration import (
    RegulatoryIntelligenceWorkflowContextPort,
    RegulatoryIntelligenceWorkflowNodeAdapter,
    RegulatoryIntelligenceWorkflowRequest,
    RegulatoryIntelligenceWorkflowStep,
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
)
from tests.unit.domain._factories import constraint


class _RecordingContextFake:
    """Test-only fake that structurally satisfies the context Protocol."""

    def __init__(
        self,
        request: RegulatoryIntelligenceWorkflowRequest,
        calls: list[str],
        resolve_error: Exception | None = None,
        record_error: Exception | None = None,
    ) -> None:
        self._request = request
        self.calls = calls
        self.resolve_error = resolve_error
        self.record_error = record_error
        self.resolve_calls = 0
        self.record_calls = 0
        self.received_resolve_state: WorkflowState | None = None
        self.received_record_state: WorkflowState | None = None
        self.received_result: RegulatoryIntelligenceResult | None = None

    async def resolve_request(
        self,
        *,
        state: WorkflowState,
    ) -> RegulatoryIntelligenceWorkflowRequest:
        self.resolve_calls += 1
        self.received_resolve_state = state
        self.calls.append("resolve_request")
        if self.resolve_error is not None:
            raise self.resolve_error
        return self._request

    async def record_result(
        self,
        *,
        state: WorkflowState,
        result: RegulatoryIntelligenceResult,
    ) -> None:
        self.record_calls += 1
        self.received_record_state = state
        self.received_result = result
        self.calls.append("record_result")
        if self.record_error is not None:
            raise self.record_error


class _RecordingWorkflowStepFake:
    """Test-only spy with the published workflow-step run shape."""

    def __init__(
        self,
        result: RegulatoryIntelligenceResult,
        calls: list[str],
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self.calls = calls
        self.error = error
        self.run_calls = 0
        self.received_request: RegulatoryIntelligenceWorkflowRequest | None = None

    async def run(
        self,
        request: RegulatoryIntelligenceWorkflowRequest,
    ) -> RegulatoryIntelligenceResult:
        self.run_calls += 1
        self.received_request = request
        self.calls.append("workflow_step.run")
        if self.error is not None:
            raise self.error
        return self._result


def _request() -> RegulatoryIntelligenceWorkflowRequest:
    return RegulatoryIntelligenceWorkflowRequest(query_text="typed regulatory query", limit=4)


def _result() -> RegulatoryIntelligenceResult:
    return RegulatoryIntelligenceResult(constraints=(constraint(),))


def _state() -> WorkflowState:
    return WorkflowState(
        workflow_id="workflow-regulatory-1",
        portfolio_id="portfolio-1",
        delivery_date=date(2026, 10, 1),
        correlation_id="corr-1",
        phase=WorkflowPhase.CONTRACT,
        status=WorkflowStatus.RUNNING,
    )


def _adapter(
    context: _RecordingContextFake,
    workflow_step: _RecordingWorkflowStepFake,
) -> RegulatoryIntelligenceWorkflowNodeAdapter:
    return RegulatoryIntelligenceWorkflowNodeAdapter(
        context=context,
        workflow_step=workflow_step,  # type: ignore[arg-type]
    )


def test_fakes_do_not_inherit_production_bases() -> None:
    assert RegulatoryIntelligenceWorkflowContextPort not in _RecordingContextFake.__mro__
    assert RegulatoryIntelligenceWorkflowStep not in _RecordingWorkflowStepFake.__mro__
    assert RegulatoryIntelligenceWorkflowNodeAdapter not in _RecordingWorkflowStepFake.__mro__
    assert not any(
        base.__name__
        in {
            "RegulatoryIntelligenceWorkflowContextPort",
            "RegulatoryIntelligenceWorkflowStep",
            "RegulatoryIntelligenceWorkflowNodeAdapter",
            "Protocol",
        }
        for base in (*_RecordingContextFake.__bases__, *_RecordingWorkflowStepFake.__bases__)
    )


def test_adapter_public_surface_is_async_run_with_two_dependencies() -> None:
    defined_methods = {
        name
        for name, value in vars(RegulatoryIntelligenceWorkflowNodeAdapter).items()
        if callable(value) and not name.startswith("_")
    }
    assert defined_methods == {"run"}
    assert inspect.iscoroutinefunction(RegulatoryIntelligenceWorkflowNodeAdapter.run)
    parameters = inspect.signature(RegulatoryIntelligenceWorkflowNodeAdapter.run).parameters
    assert tuple(parameters) == ("self", "state")
    constructor = inspect.signature(RegulatoryIntelligenceWorkflowNodeAdapter.__init__).parameters
    assert tuple(constructor) == ("self", "context", "workflow_step")
    assert constructor["context"].annotation is RegulatoryIntelligenceWorkflowContextPort
    assert constructor["workflow_step"].annotation is RegulatoryIntelligenceWorkflowStep
    forbidden = {
        "graph",
        "query_execution_service",
        "failure_policy",
        "failure_policy_port",
        "workflow_context_port",
        "workflow_node_port",
        "workflow_step_port",
    }
    assert forbidden.isdisjoint(constructor)


async def test_successful_run_resolves_runs_and_records_in_order() -> None:
    request = _request()
    result = _result()
    calls: list[str] = []
    context = _RecordingContextFake(request, calls)
    workflow_step = _RecordingWorkflowStepFake(result, calls)
    state = _state()
    returned = await _adapter(context, workflow_step).run(state)
    assert calls == ["resolve_request", "workflow_step.run", "record_result"]
    assert context.resolve_calls == 1
    assert workflow_step.run_calls == 1
    assert context.record_calls == 1
    assert context.received_resolve_state is state
    assert workflow_step.received_request is request
    assert context.received_record_state is state
    assert context.received_result is result
    assert returned is state


async def test_successful_run_preserves_workflow_state_identity() -> None:
    request = _request()
    result = _result()
    calls: list[str] = []
    state = _state()
    returned = await _adapter(
        _RecordingContextFake(request, calls),
        _RecordingWorkflowStepFake(result, calls),
    ).run(state)
    assert returned is state
    assert returned.workflow_id == "workflow-regulatory-1"
    assert returned.portfolio_id == "portfolio-1"
    assert returned.delivery_date == date(2026, 10, 1)
    assert returned.correlation_id == "corr-1"
    assert returned.phase is WorkflowPhase.CONTRACT
    assert returned.status is WorkflowStatus.RUNNING
    assert returned.diagnostics == ()
    assert "regulatory_request" not in returned.__slots__
    assert "regulatory_result" not in returned.__slots__
    assert "payload" not in returned.__slots__


async def test_resolve_failure_propagates_and_prevents_step_and_record() -> None:
    request = _request()
    result = _result()
    calls: list[str] = []
    error = DependencyUnavailableError("request unavailable")
    context = _RecordingContextFake(request, calls, resolve_error=error)
    workflow_step = _RecordingWorkflowStepFake(result, calls)
    try:
        await _adapter(context, workflow_step).run(_state())
    except DependencyUnavailableError as raised:
        assert raised is error
    else:
        raise AssertionError("resolve failure must propagate")
    assert calls == ["resolve_request"]
    assert context.resolve_calls == 1
    assert workflow_step.run_calls == 0
    assert context.record_calls == 0
    assert workflow_step.received_request is None
    assert context.received_result is None


async def test_workflow_step_failure_propagates_and_prevents_record() -> None:
    request = _request()
    result = _result()
    calls: list[str] = []
    error = DependencyUnavailableError("workflow step unavailable")
    context = _RecordingContextFake(request, calls)
    workflow_step = _RecordingWorkflowStepFake(result, calls, error=error)
    try:
        await _adapter(context, workflow_step).run(_state())
    except DependencyUnavailableError as raised:
        assert raised is error
    else:
        raise AssertionError("workflow-step failure must propagate")
    assert calls == ["resolve_request", "workflow_step.run"]
    assert context.resolve_calls == 1
    assert workflow_step.run_calls == 1
    assert context.record_calls == 0
    assert workflow_step.received_request is request
    assert context.received_result is None


async def test_record_failure_propagates_after_resolve_and_step() -> None:
    request = _request()
    result = _result()
    calls: list[str] = []
    error = DependencyUnavailableError("record unavailable")
    context = _RecordingContextFake(request, calls, record_error=error)
    workflow_step = _RecordingWorkflowStepFake(result, calls)
    try:
        await _adapter(context, workflow_step).run(_state())
    except DependencyUnavailableError as raised:
        assert raised is error
    else:
        raise AssertionError("record failure must propagate")
    assert calls == ["resolve_request", "workflow_step.run", "record_result"]
    assert context.resolve_calls == 1
    assert workflow_step.run_calls == 1
    assert context.record_calls == 1
    assert workflow_step.received_request is request
    assert context.received_result is result


async def test_failures_are_not_retried() -> None:
    request = _request()
    result = _result()
    resolve_calls: list[str] = []
    step_calls: list[str] = []
    record_calls: list[str] = []
    resolve_error = DependencyUnavailableError("resolve failed")
    step_error = DependencyUnavailableError("step failed")
    record_error = DependencyUnavailableError("record failed")
    resolve_context = _RecordingContextFake(request, resolve_calls, resolve_error=resolve_error)
    resolve_step = _RecordingWorkflowStepFake(result, resolve_calls)
    try:
        await _adapter(resolve_context, resolve_step).run(_state())
    except DependencyUnavailableError:
        pass
    else:
        raise AssertionError("resolve failure must propagate")
    step_context = _RecordingContextFake(request, step_calls)
    step_step = _RecordingWorkflowStepFake(result, step_calls, error=step_error)
    try:
        await _adapter(step_context, step_step).run(_state())
    except DependencyUnavailableError:
        pass
    else:
        raise AssertionError("workflow-step failure must propagate")
    record_context = _RecordingContextFake(request, record_calls, record_error=record_error)
    record_step = _RecordingWorkflowStepFake(result, record_calls)
    try:
        await _adapter(record_context, record_step).run(_state())
    except DependencyUnavailableError:
        pass
    else:
        raise AssertionError("record failure must propagate")
    assert resolve_context.resolve_calls == 1
    assert resolve_step.run_calls == 0
    assert step_context.resolve_calls == 1
    assert step_step.run_calls == 1
    assert step_context.record_calls == 0
    assert record_context.resolve_calls == 1
    assert record_step.run_calls == 1
    assert record_context.record_calls == 1
