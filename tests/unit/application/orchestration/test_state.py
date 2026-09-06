"""Application-owned orchestration workflow snapshot contract."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime
from enum import StrEnum

import pytest

from energy_trading.application.orchestration import (
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
)
from energy_trading.domain.models.ingestion import AdapterDiagnostic, DiagnosticSeverity
from tests.unit.domain._factories import diagnostic


def _state(**overrides: object) -> WorkflowState:
    values: dict[str, object] = {
        "workflow_id": "workflow-1",
        "portfolio_id": "portfolio-1",
        "delivery_date": date(2026, 9, 7),
        "correlation_id": "corr-1",
        "phase": WorkflowPhase.CONTRACT,
        "status": WorkflowStatus.PENDING,
        "diagnostics": (),
    }
    values.update(overrides)
    return WorkflowState(**values)  # type: ignore[arg-type]


def test_workflow_phase_is_strenum() -> None:
    assert issubclass(WorkflowPhase, StrEnum)
    assert issubclass(WorkflowPhase, str)


def test_workflow_phase_has_exactly_five_canonical_members() -> None:
    assert len(WorkflowPhase) == 5
    assert tuple(member.name for member in WorkflowPhase) == (
        "CONTRACT",
        "INGESTION",
        "FORECASTING",
        "RISK_AND_BID",
        "SETTLEMENT",
    )
    assert tuple(member.value for member in WorkflowPhase) == (
        "contract",
        "ingestion",
        "forecasting",
        "risk_and_bid",
        "settlement",
    )


def test_workflow_status_is_strenum() -> None:
    assert issubclass(WorkflowStatus, StrEnum)
    assert issubclass(WorkflowStatus, str)


def test_workflow_status_has_exactly_four_canonical_members() -> None:
    assert len(WorkflowStatus) == 4
    assert tuple(member.name for member in WorkflowStatus) == (
        "PENDING",
        "RUNNING",
        "SUCCEEDED",
        "FAILED",
    )
    assert tuple(member.value for member in WorkflowStatus) == (
        "pending",
        "running",
        "succeeded",
        "failed",
    )


def test_workflow_state_can_be_constructed() -> None:
    state = _state()
    assert state.workflow_id == "workflow-1"
    assert state.portfolio_id == "portfolio-1"
    assert state.delivery_date == date(2026, 9, 7)
    assert state.correlation_id == "corr-1"
    assert state.phase is WorkflowPhase.CONTRACT
    assert state.status is WorkflowStatus.PENDING
    assert state.diagnostics == ()


def test_workflow_state_strips_identifier_whitespace() -> None:
    state = _state(
        workflow_id="  workflow-1  ",
        portfolio_id="  portfolio-1  ",
        correlation_id="  corr-1  ",
    )
    assert state.workflow_id == "workflow-1"
    assert state.portfolio_id == "portfolio-1"
    assert state.correlation_id == "corr-1"


@pytest.mark.parametrize("workflow_id", ["", "   "])
def test_workflow_state_rejects_blank_workflow_id(workflow_id: str) -> None:
    with pytest.raises(ValueError, match="workflow_id"):
        _state(workflow_id=workflow_id)


@pytest.mark.parametrize("portfolio_id", ["", "   "])
def test_workflow_state_rejects_blank_portfolio_id(portfolio_id: str) -> None:
    with pytest.raises(ValueError, match="portfolio_id"):
        _state(portfolio_id=portfolio_id)


@pytest.mark.parametrize("correlation_id", ["", "   "])
def test_workflow_state_rejects_blank_correlation_id(correlation_id: str) -> None:
    with pytest.raises(ValueError, match="correlation_id"):
        _state(correlation_id=correlation_id)


@pytest.mark.parametrize("field_name", ["workflow_id", "portfolio_id", "correlation_id"])
@pytest.mark.parametrize("value", [None, 1, b"opaque"])
def test_workflow_state_rejects_non_string_identifiers(field_name: str, value: object) -> None:
    with pytest.raises(TypeError, match=field_name):
        _state(**{field_name: value})


def test_workflow_state_accepts_a_real_date() -> None:
    delivery_date = date(2026, 10, 1)
    state = _state(delivery_date=delivery_date)
    assert state.delivery_date == delivery_date
    assert type(state.delivery_date) is date


def test_workflow_state_rejects_datetime_for_delivery_date() -> None:
    with pytest.raises(TypeError, match="delivery_date"):
        _state(delivery_date=datetime(2026, 9, 7, 12, 0, tzinfo=UTC))
    with pytest.raises(TypeError, match="delivery_date"):
        _state(delivery_date=datetime(2026, 9, 7, 12, 0))


def test_workflow_state_rejects_wrong_phase_type() -> None:
    with pytest.raises(TypeError, match="phase"):
        _state(phase="contract")
    with pytest.raises(TypeError, match="phase"):
        _state(phase=WorkflowStatus.PENDING)


def test_workflow_state_rejects_wrong_status_type() -> None:
    with pytest.raises(TypeError, match="status"):
        _state(status="pending")
    with pytest.raises(TypeError, match="status"):
        _state(status=WorkflowPhase.CONTRACT)


def test_workflow_state_allows_empty_diagnostics() -> None:
    state = _state(diagnostics=())
    assert state.diagnostics == ()
    assert isinstance(state.diagnostics, tuple)


def test_workflow_state_accepts_one_or_many_adapter_diagnostics() -> None:
    first = diagnostic()
    second = AdapterDiagnostic(
        code="SCHEMA_AMBIGUOUS",
        message="header mapping was ambiguous",
        severity=DiagnosticSeverity.WARNING,
        field_name="timestamp",
    )
    one = _state(diagnostics=(first,))
    many = _state(diagnostics=(first, second))
    assert one.diagnostics == (first,)
    assert many.diagnostics == (first, second)
    assert all(isinstance(item, AdapterDiagnostic) for item in many.diagnostics)


def test_workflow_state_rejects_diagnostics_list() -> None:
    with pytest.raises(TypeError, match="diagnostics must be an immutable tuple"):
        _state(diagnostics=[diagnostic()])  # type: ignore[arg-type]


def test_workflow_state_rejects_wrong_diagnostic_type() -> None:
    with pytest.raises(TypeError, match="AdapterDiagnostic"):
        _state(diagnostics=("not-a-diagnostic",))  # type: ignore[arg-type]


def test_workflow_state_is_frozen() -> None:
    state = _state()
    with pytest.raises(FrozenInstanceError):
        state.status = WorkflowStatus.RUNNING  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        state.workflow_id = "mutated"  # type: ignore[misc]


def test_workflow_state_diagnostics_tuple_cannot_be_mutated() -> None:
    state = _state(diagnostics=(diagnostic(),))
    with pytest.raises(FrozenInstanceError):
        state.diagnostics = ()  # type: ignore[misc]
    with pytest.raises(TypeError):
        state.diagnostics[0] = diagnostic(code="OTHER")  # type: ignore[index]


def test_identical_workflow_states_compare_equal() -> None:
    first = _state()
    second = _state()
    assert first == second
    assert hash(first) == hash(second)
    different = _state(status=WorkflowStatus.RUNNING)
    assert first != different


def test_workflow_state_has_no_transition_or_execution_methods() -> None:
    forbidden = {
        "advance",
        "transition",
        "mark_running",
        "mark_failed",
        "mark_succeeded",
        "add_diagnostic",
        "with_phase",
        "with_status",
        "copy_with",
        "next_phase",
    }
    defined_methods = {
        name
        for name, value in vars(WorkflowState).items()
        if callable(value) and not name.startswith("_")
    }
    assert defined_methods == set()
    assert forbidden.isdisjoint(dir(WorkflowState))
    assert not hasattr(WorkflowState, "advance")
    assert not hasattr(WorkflowState, "transition")
