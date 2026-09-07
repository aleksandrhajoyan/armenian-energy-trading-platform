"""Phase 2 failure-action executor supports terminal FAIL only."""

from __future__ import annotations

from dataclasses import fields
from datetime import date

import pytest

from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.orchestration import (
    FailureAction,
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
    execute_parallel_ingestion_failure_action,
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


def test_published_failure_actions_are_exactly_retry_fallback_fail() -> None:
    assert tuple(FailureAction) == (
        FailureAction.RETRY,
        FailureAction.FALLBACK,
        FailureAction.FAIL,
    )


def test_fail_delegates_to_published_terminal_transition() -> None:
    first = diagnostic()
    second = AdapterDiagnostic(
        code="SCHEMA_AMBIGUOUS",
        message="header mapping was ambiguous",
        severity=DiagnosticSeverity.WARNING,
        field_name="timestamp",
    )
    state = _state(diagnostics=(first, second))
    before = _snapshot(state)

    failed = execute_parallel_ingestion_failure_action(state=state, action=FailureAction.FAIL)
    expected = fail_parallel_ingestion(state)

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
    assert tuple(item.name for item in fields(state)) == _WORKFLOW_STATE_FIELDS


def test_fail_propagates_published_invalid_request_from_terminal_transition() -> None:
    state = _state(phase=WorkflowPhase.FORECASTING, status=WorkflowStatus.RUNNING)
    before = _snapshot(state)

    with pytest.raises(InvalidRequestError) as direct:
        fail_parallel_ingestion(state)
    with pytest.raises(InvalidRequestError) as via_action:
        execute_parallel_ingestion_failure_action(state=state, action=FailureAction.FAIL)

    assert via_action.value.code == direct.value.code == "invalid_request"
    assert via_action.value.message == direct.value.message
    assert "workflow-1" not in via_action.value.message
    assert _snapshot(state) == before
    assert state.phase is WorkflowPhase.FORECASTING
    assert state.status is WorkflowStatus.RUNNING


def test_retry_is_not_implemented_and_does_not_mutate_state() -> None:
    state = _state(diagnostics=(diagnostic(),))
    before = _snapshot(state)

    with pytest.raises(InvalidRequestError) as caught:
        execute_parallel_ingestion_failure_action(state=state, action=FailureAction.RETRY)

    assert caught.value.code == "invalid_request"
    assert caught.value.message == _RETRY_NOT_IMPLEMENTED_MESSAGE
    assert _snapshot(state) == before
    assert state.phase is WorkflowPhase.INGESTION
    assert state.status is WorkflowStatus.RUNNING


def test_fallback_is_not_implemented_and_does_not_mutate_state() -> None:
    state = _state(diagnostics=(diagnostic(),))
    before = _snapshot(state)

    with pytest.raises(InvalidRequestError) as caught:
        execute_parallel_ingestion_failure_action(state=state, action=FailureAction.FALLBACK)

    assert caught.value.code == "invalid_request"
    assert caught.value.message == _FALLBACK_NOT_IMPLEMENTED_MESSAGE
    assert _snapshot(state) == before
    assert state.phase is WorkflowPhase.INGESTION
    assert state.status is WorkflowStatus.RUNNING


@pytest.mark.parametrize("action", list(FailureAction))
def test_every_published_failure_action_is_handled_explicitly(action: FailureAction) -> None:
    state = _state()
    before = _snapshot(state)

    if action is FailureAction.FAIL:
        failed = execute_parallel_ingestion_failure_action(state=state, action=action)
        assert failed == fail_parallel_ingestion(state)
        assert failed.phase is WorkflowPhase.INGESTION
        assert failed.status is WorkflowStatus.FAILED
    else:
        with pytest.raises(InvalidRequestError) as caught:
            execute_parallel_ingestion_failure_action(state=state, action=action)
        expected = (
            _RETRY_NOT_IMPLEMENTED_MESSAGE
            if action is FailureAction.RETRY
            else _FALLBACK_NOT_IMPLEMENTED_MESSAGE
        )
        assert caught.value.message == expected
        assert state.status is WorkflowStatus.RUNNING

    assert _snapshot(state) == before
