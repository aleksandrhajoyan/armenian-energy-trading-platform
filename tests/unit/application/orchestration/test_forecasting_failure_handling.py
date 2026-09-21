"""Prepared Phase 3 failure handling composes decision then action execution."""

from __future__ import annotations

import inspect
from dataclasses import fields
from datetime import date
from typing import get_type_hints

import pytest

from energy_trading.application.agents.base import AgentName
from energy_trading.application.errors import DependencyUnavailableError, InvalidRequestError
from energy_trading.application.orchestration.failure_policy import (
    FailureAction,
    FailurePolicyContext,
    FailurePolicyPort,
)
from energy_trading.application.orchestration.forecasting_failure_decision import (
    ForecastingFailureDecisionService,
)
from energy_trading.application.orchestration.forecasting_failure_handling import (
    ForecastingFailureHandlingService,
)
from energy_trading.application.orchestration.forecasting_failure_transition import (
    fail_after_forecasting,
)
from energy_trading.application.orchestration.state import (
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
)
from energy_trading.domain.models.ingestion import AdapterDiagnostic, DiagnosticSeverity
from tests.unit.domain._factories import diagnostic

_WORKFLOW_STATE_FIELDS = (
    "workflow_id",
    "portfolio_id",
    "delivery_date",
    "correlation_id",
    "phase",
    "status",
    "diagnostics",
)

_RETRY_NOT_IMPLEMENTED_MESSAGE = "Forecasting retry action is not implemented."
_FALLBACK_NOT_IMPLEMENTED_MESSAGE = "Forecasting fallback action is not implemented."
_FAILURE_TRANSITION_MESSAGE = (
    "Forecasting failure transition requires forecasting phase and running status."
)


class _RecordingFailurePolicyFake:
    """Test-only fake that structurally satisfies ``FailurePolicyPort``.

    Not a production policy. Does not inherit a production base class.
    """

    def __init__(
        self,
        action: FailureAction | None = None,
        error: BaseException | None = None,
    ) -> None:
        self._action = action
        self._error = error
        self.calls = 0
        self.received: FailurePolicyContext | None = None

    async def decide(self, context: FailurePolicyContext) -> FailureAction:
        self.calls += 1
        self.received = context
        if self._error is not None:
            raise self._error
        if self._action is None:
            msg = "recording fake requires an action or an error"
            raise AssertionError(msg)
        return self._action


class _RecordingDecisionServiceFake:
    """Test-only fake for the decision-service seam.

    Not a production decision service. Does not inherit a production class.
    """

    def __init__(
        self,
        action: FailureAction | None = None,
        error: BaseException | None = None,
    ) -> None:
        self._action = action
        self._error = error
        self.calls = 0
        self.received: FailurePolicyContext | None = None

    async def decide(self, context: FailurePolicyContext) -> FailureAction:
        self.calls += 1
        self.received = context
        if self._error is not None:
            raise self._error
        if self._action is None:
            msg = "recording fake requires an action or an error"
            raise AssertionError(msg)
        return self._action


def _state(**overrides: object) -> WorkflowState:
    values: dict[str, object] = {
        "workflow_id": "workflow-1",
        "portfolio_id": "portfolio-1",
        "delivery_date": date(2026, 9, 7),
        "correlation_id": "corr-1",
        "phase": WorkflowPhase.FORECASTING,
        "status": WorkflowStatus.RUNNING,
        "diagnostics": (),
    }
    values.update(overrides)
    return WorkflowState(**values)  # type: ignore[arg-type]


def _snapshot(state: WorkflowState) -> tuple[object, ...]:
    return (
        state.workflow_id,
        state.portfolio_id,
        state.delivery_date,
        state.correlation_id,
        state.phase,
        state.status,
        state.diagnostics,
    )


def _context() -> FailurePolicyContext:
    return FailurePolicyContext(
        phase=WorkflowPhase.FORECASTING,
        error_code="dependency_unavailable",
        attempt_number=1,
        agent_name=AgentName.CONSUMER_LOAD_FORECAST,
    )


def _handling_service(
    fake: _RecordingFailurePolicyFake,
) -> ForecastingFailureHandlingService:
    return ForecastingFailureHandlingService(ForecastingFailureDecisionService(fake))


def test_recording_fakes_do_not_inherit_production_bases() -> None:
    production_bases = {"FailurePolicyPort", "Protocol", "ForecastingFailureDecisionService"}
    assert FailurePolicyPort not in _RecordingFailurePolicyFake.__mro__
    assert ForecastingFailureDecisionService not in _RecordingDecisionServiceFake.__mro__
    policy_bases = {base.__name__ for base in _RecordingFailurePolicyFake.__bases__}
    decision_bases = {base.__name__ for base in _RecordingDecisionServiceFake.__bases__}
    assert policy_bases.isdisjoint(production_bases)
    assert decision_bases.isdisjoint(production_bases)


def test_handling_service_does_not_inherit_decision_service_or_policy_port() -> None:
    handling_mro = ForecastingFailureHandlingService.__mro__
    assert ForecastingFailureDecisionService not in handling_mro
    assert FailurePolicyPort not in handling_mro


def test_constructor_owns_exactly_one_decision_service_dependency() -> None:
    init = inspect.signature(ForecastingFailureHandlingService.__init__)
    assert tuple(init.parameters) == ("self", "decision_service")
    annotation = init.parameters["decision_service"].annotation
    assert annotation == "ForecastingFailureDecisionService" or (
        annotation is ForecastingFailureDecisionService
    )


def test_public_surface_is_only_async_keyword_only_handle() -> None:
    public = [name for name in dir(ForecastingFailureHandlingService) if not name.startswith("_")]
    assert public == ["handle"]
    handle = inspect.signature(ForecastingFailureHandlingService.handle)
    assert tuple(handle.parameters) == ("self", "state", "context")
    assert handle.parameters["state"].kind is inspect.Parameter.KEYWORD_ONLY
    assert handle.parameters["context"].kind is inspect.Parameter.KEYWORD_ONLY
    hints = get_type_hints(ForecastingFailureHandlingService.handle)
    assert hints["state"] is WorkflowState
    assert hints["context"] is FailurePolicyContext
    assert hints["return"] is WorkflowState
    assert inspect.iscoroutinefunction(ForecastingFailureHandlingService.handle)


async def test_handle_forwards_exact_context_state_and_action_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[object] = []
    state = _state()
    context = _context()
    result_state = _state(status=WorkflowStatus.FAILED)

    class _OrderedDecisionServiceFake:
        def __init__(self) -> None:
            self.calls = 0
            self.received: FailurePolicyContext | None = None

        async def decide(self, received: FailurePolicyContext) -> FailureAction:
            self.calls += 1
            self.received = received
            events.append(("decide", received))
            return FailureAction.FAIL

    def _tracking_execute(*, state: WorkflowState, action: FailureAction) -> WorkflowState:
        events.append(("execute", state, action))
        return result_state

    monkeypatch.setattr(
        "energy_trading.application.orchestration.forecasting_failure_handling"
        ".execute_forecasting_failure_action",
        _tracking_execute,
    )

    fake = _OrderedDecisionServiceFake()
    service = ForecastingFailureHandlingService(fake)  # type: ignore[arg-type]

    returned = await service.handle(state=state, context=context)

    assert events == [("decide", context), ("execute", state, FailureAction.FAIL)]
    assert fake.calls == 1
    assert fake.received is context
    assert returned is result_state


async def test_fail_composes_published_decision_and_terminal_transition() -> None:
    first = diagnostic()
    second = AdapterDiagnostic(
        code="SCHEMA_AMBIGUOUS",
        message="header mapping was ambiguous",
        severity=DiagnosticSeverity.WARNING,
        field_name="timestamp",
    )
    state = _state(diagnostics=(first, second))
    context = _context()
    fake = _RecordingFailurePolicyFake(FailureAction.FAIL)
    service = _handling_service(fake)
    before = _snapshot(state)

    failed = await service.handle(state=state, context=context)
    expected = fail_after_forecasting(state)

    assert fake.calls == 1
    assert fake.received is context
    assert failed is not state
    assert _snapshot(state) == before
    assert failed == expected
    assert failed.phase is WorkflowPhase.FORECASTING
    assert failed.status is WorkflowStatus.FAILED
    assert failed.workflow_id == "workflow-1"
    assert failed.portfolio_id == "portfolio-1"
    assert failed.delivery_date == date(2026, 9, 7)
    assert failed.correlation_id == "corr-1"
    assert failed.diagnostics == (first, second)
    assert failed.diagnostics is state.diagnostics
    assert failed.diagnostics[0] is first
    assert failed.diagnostics[1] is second
    assert tuple(item.name for item in fields(failed)) == _WORKFLOW_STATE_FIELDS


async def test_retry_propagates_published_not_implemented_error() -> None:
    state = _state(diagnostics=(diagnostic(),))
    context = _context()
    fake = _RecordingFailurePolicyFake(FailureAction.RETRY)
    service = _handling_service(fake)
    before = _snapshot(state)

    with pytest.raises(InvalidRequestError) as caught:
        await service.handle(state=state, context=context)

    assert fake.calls == 1
    assert fake.received is context
    assert caught.value.code == "invalid_request"
    assert caught.value.message == _RETRY_NOT_IMPLEMENTED_MESSAGE
    assert _snapshot(state) == before
    assert state.status is WorkflowStatus.RUNNING


async def test_fallback_propagates_published_not_implemented_error() -> None:
    state = _state(diagnostics=(diagnostic(),))
    context = _context()
    fake = _RecordingFailurePolicyFake(FailureAction.FALLBACK)
    service = _handling_service(fake)
    before = _snapshot(state)

    with pytest.raises(InvalidRequestError) as caught:
        await service.handle(state=state, context=context)

    assert fake.calls == 1
    assert fake.received is context
    assert caught.value.code == "invalid_request"
    assert caught.value.message == _FALLBACK_NOT_IMPLEMENTED_MESSAGE
    assert _snapshot(state) == before
    assert state.status is WorkflowStatus.RUNNING


async def test_decision_exception_propagates_without_reaching_action_executor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state()
    context = _context()
    error = DependencyUnavailableError("policy unavailable")
    fake = _RecordingDecisionServiceFake(error=error)
    service = ForecastingFailureHandlingService(fake)  # type: ignore[arg-type]
    before = _snapshot(state)
    action_calls: list[FailureAction] = []

    def _tracking_execute(*, state: WorkflowState, action: FailureAction) -> WorkflowState:
        action_calls.append(action)
        return state

    monkeypatch.setattr(
        "energy_trading.application.orchestration.forecasting_failure_handling"
        ".execute_forecasting_failure_action",
        _tracking_execute,
    )

    with pytest.raises(DependencyUnavailableError) as caught:
        await service.handle(state=state, context=context)

    assert caught.value is error
    assert fake.calls == 1
    assert fake.received is context
    assert action_calls == []
    assert _snapshot(state) == before
    assert state.status is WorkflowStatus.RUNNING


async def test_action_executor_error_propagates_unchanged() -> None:
    state = _state(phase=WorkflowPhase.INGESTION, status=WorkflowStatus.RUNNING)
    context = _context()
    fake = _RecordingFailurePolicyFake(FailureAction.FAIL)
    service = _handling_service(fake)
    before = _snapshot(state)

    with pytest.raises(InvalidRequestError) as direct:
        fail_after_forecasting(state)
    with pytest.raises(InvalidRequestError) as via_handle:
        await service.handle(state=state, context=context)

    assert fake.calls == 1
    assert fake.received is context
    assert via_handle.value.code == direct.value.code == "invalid_request"
    assert via_handle.value.message == direct.value.message == _FAILURE_TRANSITION_MESSAGE
    assert _snapshot(state) == before
    assert state.phase is WorkflowPhase.INGESTION
    assert state.status is WorkflowStatus.RUNNING
