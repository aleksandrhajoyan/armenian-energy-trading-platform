"""Application-owned orchestration workflow snapshot.

This module defines the minimum typed state a future graph runtime may
carry. It answers identity, delivery context, current business phase,
coarse lifecycle status, and accumulated canonical diagnostics.

Ownership:

* Application: owns ``WorkflowPhase``, ``WorkflowStatus``, and
  ``WorkflowState``.
* Future graph orchestration: consumes this snapshot. The contract itself
  does not import or expose a graph runtime.
* Persistence, routing, retries, and fallback remain deferred.

``WorkflowState`` is a frozen snapshot. It has no transition, mutation, or
execution helpers. Phase-specific canonical outputs are not pre-created
slots on this type.
"""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from energy_trading.domain.models.ingestion import AdapterDiagnostic


class WorkflowPhase(StrEnum):
    """Canonical business phase of one DAM workflow.

    Values match the five already-documented business phases. This is not a
    graph node catalog and is not a lifecycle status.
    """

    CONTRACT = "contract"
    INGESTION = "ingestion"
    FORECASTING = "forecasting"
    RISK_AND_BID = "risk_and_bid"
    SETTLEMENT = "settlement"


class WorkflowStatus(StrEnum):
    """Coarse workflow lifecycle vocabulary.

    These values describe snapshot status only. Retry, fallback, pause, and
    cancellation policies are not encoded here.
    """

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class WorkflowState:
    """Immutable application snapshot of one orchestration workflow.

    This is not LangGraph state, not a persistence record, and not a
    generic payload envelope. Identifiers are opaque non-empty strings.
    ``delivery_date`` is a calendar date without timezone or DAM interval
    inference. ``diagnostics`` reuses canonical ``AdapterDiagnostic`` values.
    """

    workflow_id: str
    portfolio_id: str
    delivery_date: date
    correlation_id: str
    phase: WorkflowPhase
    status: WorkflowStatus
    diagnostics: tuple[AdapterDiagnostic, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "workflow_id", _require_non_empty("workflow_id", self.workflow_id))
        object.__setattr__(
            self, "portfolio_id", _require_non_empty("portfolio_id", self.portfolio_id)
        )
        object.__setattr__(
            self,
            "correlation_id",
            _require_non_empty("correlation_id", self.correlation_id),
        )
        object.__setattr__(
            self, "delivery_date", _require_date("delivery_date", self.delivery_date)
        )
        object.__setattr__(self, "phase", _require_phase(self.phase))
        object.__setattr__(self, "status", _require_status(self.status))
        object.__setattr__(self, "diagnostics", _require_diagnostics(self.diagnostics))


def _require_non_empty(field_name: str, value: object) -> str:
    if not isinstance(value, str):
        msg = f"{field_name} must be a string"
        raise TypeError(msg)
    cleaned = value.strip()
    if not cleaned:
        msg = f"{field_name} must be a non-empty string"
        raise ValueError(msg)
    return cleaned


def _require_date(field_name: str, value: object) -> date:
    if type(value) is not date:
        msg = f"{field_name} must be a date"
        raise TypeError(msg)
    return value


def _require_phase(value: object) -> WorkflowPhase:
    if not isinstance(value, WorkflowPhase):
        msg = "phase must be a WorkflowPhase"
        raise TypeError(msg)
    return value


def _require_status(value: object) -> WorkflowStatus:
    if not isinstance(value, WorkflowStatus):
        msg = "status must be a WorkflowStatus"
        raise TypeError(msg)
    return value


def _require_diagnostics(value: object) -> tuple[AdapterDiagnostic, ...]:
    if not isinstance(value, tuple):
        msg = "diagnostics must be an immutable tuple"
        raise TypeError(msg)
    if not all(isinstance(item, AdapterDiagnostic) for item in value):
        msg = "diagnostics must contain AdapterDiagnostic values"
        raise TypeError(msg)
    return value
