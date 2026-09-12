"""Framework-neutral successful Phase 3 control-state transition."""

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
_INVALID_MESSAGE = "Forecasting success transition requires forecasting phase and running status."


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
    assert not inspect.iscoroutinefunction(advance_after_forecasting)
    parameters = inspect.signature(advance_after_forecasting).parameters
    assert tuple(parameters) == ("state",)
    assert parameters["state"].annotation is WorkflowState
    assert inspect.signature(advance_after_forecasting).return_annotation is WorkflowState


def test_valid_forecasting_running_advances_to_risk_and_bid_running() -> None:
    first = diagnostic()
    second = AdapterDiagnostic(
        code="SCHEMA_AMBIGUOUS",
        message="header mapping was ambiguous",
        severity=DiagnosticSeverity.WARNING,
        field_name="timestamp",
    )
    state = _state(diagnostics=(first, second))
    before = _snapshot(state)

    advanced = advance_after_forecasting(state)

    assert advanced is not state
    assert _snapshot(state) == before
    assert advanced.phase is WorkflowPhase.RISK_AND_BID
    assert advanced.status is WorkflowStatus.RUNNING
    assert advanced.workflow_id == "workflow-1"
    assert advanced.portfolio_id == "portfolio-1"
    assert advanced.delivery_date == date(2026, 9, 7)
    assert advanced.correlation_id == "corr-1"
    assert advanced.diagnostics == (first, second)
    assert advanced.diagnostics is state.diagnostics
    assert advanced.diagnostics[0] is first
    assert advanced.diagnostics[1] is second
    assert tuple(item.name for item in fields(advanced)) == _WORKFLOW_STATE_FIELDS
    assert tuple(item.name for item in fields(state)) == _WORKFLOW_STATE_FIELDS


def test_transition_does_not_require_forecasting_payload() -> None:
    state = _state()
    advanced = advance_after_forecasting(state)
    assert not hasattr(state, "forecasting_plan")
    assert not hasattr(state, "forecasting_success")
    assert not hasattr(advanced, "forecasting_plan")
    assert not hasattr(advanced, "forecasting_success")
    assert advanced.phase is WorkflowPhase.RISK_AND_BID
    assert advanced.status is WorkflowStatus.RUNNING


@pytest.mark.parametrize("phase", _NON_FORECASTING_PHASES)
def test_rejects_non_forecasting_phase(phase: WorkflowPhase) -> None:
    state = _state(phase=phase, status=WorkflowStatus.RUNNING, diagnostics=(diagnostic(),))
    before = _snapshot(state)

    with pytest.raises(InvalidRequestError) as caught:
        advance_after_forecasting(state)

    assert caught.value.code == "invalid_request"
    assert caught.value.message == _INVALID_MESSAGE
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
        advance_after_forecasting(state)

    assert caught.value.code == "invalid_request"
    assert caught.value.message == _INVALID_MESSAGE
    assert "workflow-1" not in caught.value.message
    assert "portfolio-1" not in caught.value.message
    assert "corr-1" not in caught.value.message
    assert status.value not in caught.value.message
    assert "VALIDATION_FAILED" not in caught.value.message
    assert _snapshot(state) == before


def test_rejects_failed_forecasting_source() -> None:
    state = _state(status=WorkflowStatus.FAILED, diagnostics=(diagnostic(),))
    before = _snapshot(state)

    with pytest.raises(InvalidRequestError) as caught:
        advance_after_forecasting(state)

    assert caught.value is not None
    assert caught.value.code == "invalid_request"
    assert caught.value.message == _INVALID_MESSAGE
    assert _snapshot(state) == before


def test_equivalent_valid_states_produce_equivalent_output() -> None:
    first = advance_after_forecasting(_state(diagnostics=(diagnostic(),)))
    second = advance_after_forecasting(_state(diagnostics=(diagnostic(),)))

    assert first == second
    assert first is not second
    assert first.phase is WorkflowPhase.RISK_AND_BID
    assert first.status is WorkflowStatus.RUNNING
