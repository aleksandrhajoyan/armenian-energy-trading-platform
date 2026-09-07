"""Framework-neutral terminal Phase 2 failure control-state transition."""

from __future__ import annotations

from dataclasses import fields
from datetime import date

import pytest

from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.orchestration import (
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
    advance_after_parallel_ingestion,
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

_NON_INGESTION_PHASES = tuple(
    phase for phase in WorkflowPhase if phase is not WorkflowPhase.INGESTION
)
_NON_RUNNING_STATUSES = tuple(
    status for status in WorkflowStatus if status is not WorkflowStatus.RUNNING
)
_FAILURE_TRANSITION_MESSAGE = (
    "Parallel-ingestion failure transition requires ingestion phase and running status."
)


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


def test_valid_ingestion_running_fails_to_ingestion_failed() -> None:
    first = diagnostic()
    second = AdapterDiagnostic(
        code="SCHEMA_AMBIGUOUS",
        message="header mapping was ambiguous",
        severity=DiagnosticSeverity.WARNING,
        field_name="timestamp",
    )
    state = _state(diagnostics=(first, second))
    before = _snapshot(state)

    failed = fail_parallel_ingestion(state)

    assert failed is not state
    assert _snapshot(state) == before
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


@pytest.mark.parametrize("phase", _NON_INGESTION_PHASES)
def test_rejects_non_ingestion_phase(phase: WorkflowPhase) -> None:
    state = _state(phase=phase, status=WorkflowStatus.RUNNING, diagnostics=(diagnostic(),))
    before = _snapshot(state)

    with pytest.raises(InvalidRequestError) as caught:
        fail_parallel_ingestion(state)

    assert caught.value.code == "invalid_request"
    assert caught.value.message == _FAILURE_TRANSITION_MESSAGE
    assert "workflow-1" not in caught.value.message
    assert "portfolio-1" not in caught.value.message
    assert "corr-1" not in caught.value.message
    assert phase.value not in caught.value.message
    assert "VALIDATION_FAILED" not in caught.value.message
    assert _snapshot(state) == before


@pytest.mark.parametrize("status", _NON_RUNNING_STATUSES)
def test_rejects_non_running_status_in_ingestion_phase(status: WorkflowStatus) -> None:
    state = _state(phase=WorkflowPhase.INGESTION, status=status, diagnostics=(diagnostic(),))
    before = _snapshot(state)

    with pytest.raises(InvalidRequestError) as caught:
        fail_parallel_ingestion(state)

    assert caught.value.code == "invalid_request"
    assert caught.value.message == _FAILURE_TRANSITION_MESSAGE
    assert "workflow-1" not in caught.value.message
    assert "portfolio-1" not in caught.value.message
    assert "corr-1" not in caught.value.message
    assert status.value not in caught.value.message
    assert "VALIDATION_FAILED" not in caught.value.message
    assert _snapshot(state) == before


def test_previously_failed_ingestion_state_cannot_be_failed_again() -> None:
    state = _state(phase=WorkflowPhase.INGESTION, status=WorkflowStatus.FAILED)
    before = _snapshot(state)

    with pytest.raises(InvalidRequestError) as caught:
        fail_parallel_ingestion(state)

    assert caught.value.code == "invalid_request"
    assert caught.value.message == _FAILURE_TRANSITION_MESSAGE
    assert _snapshot(state) == before


def test_equivalent_valid_states_produce_equivalent_output() -> None:
    first = fail_parallel_ingestion(_state(diagnostics=(diagnostic(),)))
    second = fail_parallel_ingestion(_state(diagnostics=(diagnostic(),)))

    assert first == second
    assert first is not second
    assert first.phase is WorkflowPhase.INGESTION
    assert first.status is WorkflowStatus.FAILED


def test_success_and_failure_transitions_remain_distinct_policies() -> None:
    diagnostics = (diagnostic(),)
    source = _state(diagnostics=diagnostics)
    before = _snapshot(source)

    advanced = advance_after_parallel_ingestion(source)
    failed = fail_parallel_ingestion(source)

    assert _snapshot(source) == before
    assert advanced is not source
    assert failed is not source
    assert advanced is not failed
    assert advanced.phase is WorkflowPhase.FORECASTING
    assert advanced.status is WorkflowStatus.RUNNING
    assert failed.phase is WorkflowPhase.INGESTION
    assert failed.status is WorkflowStatus.FAILED
    assert advanced.diagnostics is source.diagnostics
    assert failed.diagnostics is source.diagnostics
    assert advanced.workflow_id == failed.workflow_id == "workflow-1"
    assert advanced.portfolio_id == failed.portfolio_id == "portfolio-1"
    assert advanced.delivery_date == failed.delivery_date == date(2026, 9, 7)
    assert advanced.correlation_id == failed.correlation_id == "corr-1"
