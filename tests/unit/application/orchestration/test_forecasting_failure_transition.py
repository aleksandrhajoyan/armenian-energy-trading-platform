"""Framework-neutral terminal Phase 3 failure control-state transition."""

from __future__ import annotations

import inspect
from dataclasses import fields
from datetime import date

import pytest

from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.orchestration import (
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
    advance_after_forecasting,
    fail_after_forecasting,
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

_NON_FORECASTING_PHASES = tuple(
    phase for phase in WorkflowPhase if phase is not WorkflowPhase.FORECASTING
)
_NON_RUNNING_STATUSES = tuple(
    status for status in WorkflowStatus if status is not WorkflowStatus.RUNNING
)
_FAILURE_TRANSITION_MESSAGE = (
    "Forecasting failure transition requires forecasting phase and running status."
)


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


def test_transition_is_synchronous_and_has_no_collaborators() -> None:
    assert not inspect.iscoroutinefunction(fail_after_forecasting)
    parameters = inspect.signature(fail_after_forecasting).parameters
    assert tuple(parameters) == ("state",)
    assert parameters["state"].annotation is WorkflowState
    assert inspect.signature(fail_after_forecasting).return_annotation is WorkflowState


def test_valid_forecasting_running_fails_to_forecasting_failed() -> None:
    first = diagnostic()
    second = AdapterDiagnostic(
        code="SCHEMA_AMBIGUOUS",
        message="header mapping was ambiguous",
        severity=DiagnosticSeverity.WARNING,
        field_name="timestamp",
    )
    state = _state(diagnostics=(first, second))
    before = _snapshot(state)

    failed = fail_after_forecasting(state)

    assert failed is not state
    assert _snapshot(state) == before
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


def test_empty_prior_diagnostics_remain_empty() -> None:
    state = _state(diagnostics=())
    failed = fail_after_forecasting(state)
    assert failed.diagnostics == ()
    assert failed.diagnostics is state.diagnostics
    assert failed.phase is WorkflowPhase.FORECASTING
    assert failed.status is WorkflowStatus.FAILED


def test_transition_does_not_require_forecasting_payload_or_failure_input() -> None:
    state = _state()
    failed = fail_after_forecasting(state)
    assert not hasattr(state, "forecasting_plan")
    assert not hasattr(state, "forecasting_success")
    assert not hasattr(failed, "forecasting_plan")
    assert not hasattr(failed, "forecasting_success")
    assert not hasattr(failed, "exception")
    assert not hasattr(failed, "error")
    assert not hasattr(failed, "failed_agent")
    assert not hasattr(failed, "retry_count")
    assert failed.phase is WorkflowPhase.FORECASTING
    assert failed.status is WorkflowStatus.FAILED


def test_output_does_not_expose_raw_failure_objects() -> None:
    state = _state(diagnostics=(diagnostic(),))
    failed = fail_after_forecasting(state)
    rendered = repr(failed)
    assert "ExceptionGroup" not in rendered
    assert "TaskGroup" not in rendered
    assert "Traceback" not in rendered
    assert "Lag24h168hOLSConsumerLoadForecastModel" not in rendered
    assert "PreviousDayPersistenceConsumerLoadForecastModel" not in rendered
    assert "ConsumerLoadForecastModelRequest" not in rendered
    for item in failed.diagnostics:
        assert isinstance(item, AdapterDiagnostic)
        assert not isinstance(item, BaseException)


@pytest.mark.parametrize("phase", _NON_FORECASTING_PHASES)
def test_rejects_non_forecasting_phase(phase: WorkflowPhase) -> None:
    state = _state(phase=phase, status=WorkflowStatus.RUNNING, diagnostics=(diagnostic(),))
    before = _snapshot(state)

    with pytest.raises(InvalidRequestError) as caught:
        fail_after_forecasting(state)

    assert caught.value.code == "invalid_request"
    assert caught.value.message == _FAILURE_TRANSITION_MESSAGE
    assert "workflow-1" not in caught.value.message
    assert "portfolio-1" not in caught.value.message
    assert "corr-1" not in caught.value.message
    assert phase.value not in caught.value.message
    assert "VALIDATION_FAILED" not in caught.value.message
    assert _snapshot(state) == before


@pytest.mark.parametrize("status", _NON_RUNNING_STATUSES)
def test_rejects_non_running_status_in_forecasting_phase(status: WorkflowStatus) -> None:
    state = _state(phase=WorkflowPhase.FORECASTING, status=status, diagnostics=(diagnostic(),))
    before = _snapshot(state)

    with pytest.raises(InvalidRequestError) as caught:
        fail_after_forecasting(state)

    assert caught.value.code == "invalid_request"
    assert caught.value.message == _FAILURE_TRANSITION_MESSAGE
    assert "workflow-1" not in caught.value.message
    assert "portfolio-1" not in caught.value.message
    assert "corr-1" not in caught.value.message
    assert status.value not in caught.value.message
    assert "VALIDATION_FAILED" not in caught.value.message
    assert _snapshot(state) == before


def test_previously_failed_forecasting_state_cannot_be_failed_again() -> None:
    state = _state(phase=WorkflowPhase.FORECASTING, status=WorkflowStatus.FAILED)
    before = _snapshot(state)

    with pytest.raises(InvalidRequestError) as caught:
        fail_after_forecasting(state)

    assert caught.value.code == "invalid_request"
    assert caught.value.message == _FAILURE_TRANSITION_MESSAGE
    assert _snapshot(state) == before


def test_equivalent_valid_states_produce_equivalent_output() -> None:
    first = fail_after_forecasting(_state(diagnostics=(diagnostic(),)))
    second = fail_after_forecasting(_state(diagnostics=(diagnostic(),)))

    assert first == second
    assert first is not second
    assert first.phase is WorkflowPhase.FORECASTING
    assert first.status is WorkflowStatus.FAILED


def test_success_and_failure_transitions_remain_distinct_policies() -> None:
    diagnostics = (diagnostic(),)
    source = _state(diagnostics=diagnostics)
    before = _snapshot(source)

    advanced = advance_after_forecasting(source)
    failed = fail_after_forecasting(source)

    assert _snapshot(source) == before
    assert advanced is not source
    assert failed is not source
    assert advanced is not failed
    assert advanced.phase is WorkflowPhase.RISK_AND_BID
    assert advanced.status is WorkflowStatus.RUNNING
    assert failed.phase is WorkflowPhase.FORECASTING
    assert failed.status is WorkflowStatus.FAILED
    assert advanced.diagnostics is source.diagnostics
    assert failed.diagnostics is source.diagnostics
    assert advanced.workflow_id == failed.workflow_id == "workflow-1"
    assert advanced.portfolio_id == failed.portfolio_id == "portfolio-1"
    assert advanced.delivery_date == failed.delivery_date == date(2026, 9, 7)
    assert advanced.correlation_id == failed.correlation_id == "corr-1"
