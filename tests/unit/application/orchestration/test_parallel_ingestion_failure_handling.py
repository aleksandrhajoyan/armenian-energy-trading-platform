"""Prepared Phase 2 failure handling composes decision then action execution."""

from __future__ import annotations

from dataclasses import fields
from datetime import date

import pytest

from energy_trading.application.agents import AgentName
from energy_trading.application.errors import DependencyUnavailableError, InvalidRequestError
from energy_trading.application.orchestration import (
    FailureAction,
    FailurePolicyContext,
    FailurePolicyPort,
    ParallelIngestionFailureDecisionService,
    ParallelIngestionFailureHandlingService,
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
    fail_parallel_ingestion,
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

_RETRY_NOT_IMPLEMENTED_MESSAGE = "Parallel-ingestion retry action is not implemented."
_FALLBACK_NOT_IMPLEMENTED_MESSAGE = "Parallel-ingestion fallback action is not implemented."
_FAILURE_TRANSITION_MESSAGE = (
    "Parallel-ingestion failure transition requires ingestion phase and running status."
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


def _state(**overrides: object) -> WorkflowState:
    values: dict[str, object] = {
        "workflow_id": "workflow-1",
        "portfolio_id": "portfolio-1",
        "delivery_date": date(2026, 9, 7),
        "correlation_id": "corr-1",
        "phase": WorkflowPhase.INGESTION,
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
        phase=WorkflowPhase.INGESTION,
        error_code="dependency_unavailable",
        attempt_number=1,
        agent_name=AgentName.MARKET_MONITORING,
    )


def _handling_service(
    fake: _RecordingFailurePolicyFake,
) -> ParallelIngestionFailureHandlingService:
    return ParallelIngestionFailureHandlingService(ParallelIngestionFailureDecisionService(fake))


def test_recording_fake_does_not_inherit_failure_policy_port() -> None:
    assert FailurePolicyPort not in _RecordingFailurePolicyFake.__mro__
    assert not any(
        base.__name__ in {"FailurePolicyPort", "Protocol"}
        for base in _RecordingFailurePolicyFake.__bases__
    )


def test_handling_service_does_not_inherit_decision_service_or_policy_port() -> None:
    handling_mro = ParallelIngestionFailureHandlingService.__mro__
    assert ParallelIngestionFailureDecisionService not in handling_mro
    assert FailurePolicyPort not in handling_mro


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
    expected = fail_parallel_ingestion(state)

    assert fake.calls == 1
    assert fake.received is context
    assert failed is not state
    assert _snapshot(state) == before
    assert failed == expected
    assert failed.phase is WorkflowPhase.INGESTION
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


async def test_policy_exception_propagates_without_reaching_action_executor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state()
    context = _context()
    error = DependencyUnavailableError("policy unavailable")
    fake = _RecordingFailurePolicyFake(error=error)
    service = _handling_service(fake)
    before = _snapshot(state)
    action_calls: list[FailureAction] = []

    def _tracking_execute(*, state: WorkflowState, action: FailureAction) -> WorkflowState:
        action_calls.append(action)
        return state

    monkeypatch.setattr(
        "energy_trading.application.orchestration.parallel_ingestion_failure_handling"
        ".execute_parallel_ingestion_failure_action",
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


async def test_fail_preserves_published_terminal_transition_validation() -> None:
    state = _state(phase=WorkflowPhase.FORECASTING, status=WorkflowStatus.RUNNING)
    context = _context()
    fake = _RecordingFailurePolicyFake(FailureAction.FAIL)
    service = _handling_service(fake)
    before = _snapshot(state)

    with pytest.raises(InvalidRequestError) as direct:
        fail_parallel_ingestion(state)
    with pytest.raises(InvalidRequestError) as via_handle:
        await service.handle(state=state, context=context)

    assert fake.calls == 1
    assert fake.received is context
    assert via_handle.value.code == direct.value.code == "invalid_request"
    assert via_handle.value.message == direct.value.message == _FAILURE_TRANSITION_MESSAGE
    assert _snapshot(state) == before
    assert state.phase is WorkflowPhase.FORECASTING
    assert state.status is WorkflowStatus.RUNNING
