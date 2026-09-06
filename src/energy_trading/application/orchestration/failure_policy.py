"""Application-owned orchestration failure-policy decision seam.

This module defines how future orchestration may ask whether a sanitized
application failure should be retried, diverted to a separately defined
fallback path, or failed. It does not execute retries or fallbacks.

Ownership:

* Application: owns ``FailureAction``, ``FailurePolicyContext``, and
  ``FailurePolicyPort``.
* Future graph orchestration: may consume this protocol. The contract itself
  does not import or expose a graph runtime.
* Concrete policy rules, retry execution, fallback targets, delays, and
  backoff remain deferred.

``FailurePolicyContext`` is a frozen sanitized DTO. It does not carry
exception objects, messages, or tracebacks. Callers must translate an
observed failure into a stable ``error_code`` before evaluation.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from energy_trading.application.agents.base import AgentName
from energy_trading.application.orchestration.state import WorkflowPhase


class FailureAction(StrEnum):
    """Closed initial decision set for a sanitized orchestration failure.

    ``RETRY`` and ``FALLBACK`` are policy decisions only. They do not execute
    a retry, identify a fallback path, or mutate workflow state.
    """

    RETRY = "retry"
    FALLBACK = "fallback"
    FAIL = "fail"


@dataclass(frozen=True, slots=True)
class FailurePolicyContext:
    """Immutable sanitized context for one failure-policy decision.

    This is not workflow state, not an exception envelope, and not a graph
    runtime object. ``attempt_number`` is the 1-based failed attempt being
    evaluated; it is not stored on ``WorkflowState``.
    """

    phase: WorkflowPhase
    error_code: str
    attempt_number: int
    agent_name: AgentName | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "phase", _require_phase(self.phase))
        object.__setattr__(self, "error_code", _require_error_code(self.error_code))
        object.__setattr__(self, "attempt_number", _require_attempt_number(self.attempt_number))
        object.__setattr__(self, "agent_name", _require_optional_agent_name(self.agent_name))


class FailurePolicyPort(Protocol):
    """Framework-neutral failure-policy decision contract.

    Implementations satisfy this protocol structurally. There is no
    application base class and no concrete production policy.

    ``decide`` accepts only sanitized ``FailurePolicyContext``. It must not
    accept ``WorkflowState``, exception objects, graph runtime, or
    retry/fallback callbacks.
    """

    async def decide(self, context: FailurePolicyContext) -> FailureAction:
        """Return ``RETRY``, ``FALLBACK``, or ``FAIL`` for one failure context."""
        ...


def _require_phase(value: object) -> WorkflowPhase:
    if not isinstance(value, WorkflowPhase):
        msg = "phase must be a WorkflowPhase"
        raise TypeError(msg)
    return value


def _require_error_code(value: object) -> str:
    if not isinstance(value, str):
        msg = "error_code must be a string"
        raise TypeError(msg)
    cleaned = value.strip()
    if not cleaned:
        msg = "error_code must be a non-empty string"
        raise ValueError(msg)
    return cleaned


def _require_attempt_number(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = "attempt_number must be an integer"
        raise TypeError(msg)
    if value < 1:
        msg = "attempt_number must be greater than 0"
        raise ValueError(msg)
    return value


def _require_optional_agent_name(value: object) -> AgentName | None:
    if value is None:
        return None
    if not isinstance(value, AgentName):
        msg = "agent_name must be an AgentName or None"
        raise TypeError(msg)
    return value
