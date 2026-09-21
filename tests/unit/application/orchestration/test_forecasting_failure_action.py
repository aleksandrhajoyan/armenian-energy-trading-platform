"""Phase 3 failure-action executor supports terminal FAIL only."""

from __future__ import annotations

import inspect
from dataclasses import fields
from datetime import date

import pytest

from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.orchestration import (
    FailureAction,
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
    fail_after_forecasting,
)
from energy_trading.application.orchestration.forecasting_failure_action import (
    execute_forecasting_failure_action,
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


def test_public_surface_is_exactly_the_synchronous_keyword_only_function() -> None:
    assert inspect.isfunction(execute_forecasting_failure_action)
    assert not inspect.iscoroutinefunction(execute_forecasting_failure_action)
    parameters = inspect.signature(execute_forecasting_failure_action).parameters
    assert tuple(parameters) == ("state", "action")
    assert parameters["state"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["action"].kind is inspect.Parameter.KEYWORD_ONLY
    hints = inspect.get_annotations(execute_forecasting_failure_action)
    assert hints["state"] is WorkflowState
    assert hints["action"] is FailureAction
    assert hints["return"] is WorkflowState
    module = inspect.getmodule(execute_forecasting_failure_action)
    assert module is not None
    classes = [
        name
        for name, obj in inspect.getmembers(module, inspect.isclass)
        if obj.__module__ == module.__name__
    ]
    assert classes == []


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

    failed = execute_forecasting_failure_action(state=state, action=FailureAction.FAIL)
    expected = fail_after_forecasting(state)

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
    assert tuple(item.name for item in fields(state)) == _WORKFLOW_STATE_FIELDS


def test_fail_propagates_published_invalid_request_from_terminal_transition() -> None:
    state = _state(phase=WorkflowPhase.INGESTION, status=WorkflowStatus.RUNNING)
    before = _snapshot(state)

    with pytest.raises(InvalidRequestError) as direct:
        fail_after_forecasting(state)
    with pytest.raises(InvalidRequestError) as via_action:
        execute_forecasting_failure_action(state=state, action=FailureAction.FAIL)

    assert via_action.value.code == direct.value.code == "invalid_request"
    assert via_action.value.message == direct.value.message
    assert "workflow-1" not in via_action.value.message
    assert _snapshot(state) == before
    assert state.phase is WorkflowPhase.INGESTION
    assert state.status is WorkflowStatus.RUNNING


def test_retry_is_not_implemented_and_does_not_mutate_state() -> None:
    state = _state(diagnostics=(diagnostic(),))
    before = _snapshot(state)

    with pytest.raises(InvalidRequestError) as caught:
        execute_forecasting_failure_action(state=state, action=FailureAction.RETRY)

    assert caught.value.code == "invalid_request"
    assert caught.value.message == _RETRY_NOT_IMPLEMENTED_MESSAGE
    assert _snapshot(state) == before
    assert state.phase is WorkflowPhase.FORECASTING
    assert state.status is WorkflowStatus.RUNNING


def test_fallback_is_not_implemented_and_does_not_mutate_state() -> None:
    state = _state(diagnostics=(diagnostic(),))
    before = _snapshot(state)

    with pytest.raises(InvalidRequestError) as caught:
        execute_forecasting_failure_action(state=state, action=FailureAction.FALLBACK)

    assert caught.value.code == "invalid_request"
    assert caught.value.message == _FALLBACK_NOT_IMPLEMENTED_MESSAGE
    assert _snapshot(state) == before
    assert state.phase is WorkflowPhase.FORECASTING
    assert state.status is WorkflowStatus.RUNNING


@pytest.mark.parametrize("action", list(FailureAction))
def test_every_published_failure_action_is_handled_explicitly(action: FailureAction) -> None:
    state = _state()
    before = _snapshot(state)

    if action is FailureAction.FAIL:
        failed = execute_forecasting_failure_action(state=state, action=action)
        assert failed == fail_after_forecasting(state)
        assert failed.phase is WorkflowPhase.FORECASTING
        assert failed.status is WorkflowStatus.FAILED
    else:
        with pytest.raises(InvalidRequestError) as caught:
            execute_forecasting_failure_action(state=state, action=action)
        expected = (
            _RETRY_NOT_IMPLEMENTED_MESSAGE
            if action is FailureAction.RETRY
            else _FALLBACK_NOT_IMPLEMENTED_MESSAGE
        )
        assert caught.value.message == expected
        assert state.status is WorkflowStatus.RUNNING

    assert _snapshot(state) == before
