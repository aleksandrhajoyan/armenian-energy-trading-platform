"""Application-owned Phase 2 sanitized one-leaf failure classification.

This module converts one already-attributed ``ParallelIngestionAgentFailure``
into a frozen fact containing only canonical ``AgentName`` and a stable
``error_code``. It does not select among multiple failures or construct
policy context.

Ownership:

* Application: owns ``ParallelIngestionFailureFact`` and
  ``classify_parallel_ingestion_agent_failure``.
* Existing ``ParallelIngestionAgentFailure``: reused unchanged as input.
* Existing ``ApplicationError``: published ``code`` is reused when the
  causal failure is an application error.
* Multi-failure selection, attempt tracking, policy-context
  construction, policy/action handling, and graph routing remain deferred.

The classifier inspects only ``failure.__cause__``. Causal text and class
names never become policy facts.
"""

from dataclasses import dataclass

from energy_trading.application.agents.base import AgentName
from energy_trading.application.errors import ApplicationError
from energy_trading.application.orchestration.parallel_ingestion_agent_failure import (
    ParallelIngestionAgentFailure,
)

_UNEXPECTED_FAILURE_CODE = "parallel_ingestion_unexpected_failure"


def _require_agent_name(value: object) -> AgentName:
    if not isinstance(value, AgentName):
        msg = "agent_name must be an AgentName"
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


@dataclass(frozen=True, slots=True)
class ParallelIngestionFailureFact:
    """Immutable sanitized fact for one already-attributed Phase 2 failure.

    This is not an exception envelope, not policy context, and not a
    workflow snapshot field. It carries only canonical agent identity and a
    stable error code.
    """

    agent_name: AgentName
    error_code: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "agent_name", _require_agent_name(self.agent_name))
        object.__setattr__(self, "error_code", _require_error_code(self.error_code))


def classify_parallel_ingestion_agent_failure(
    failure: ParallelIngestionAgentFailure,
) -> ParallelIngestionFailureFact:
    """Return a sanitized Phase 2 failure fact for one attributed leaf.

    ``ApplicationError`` causes reuse their published application error
    code. Missing or non-application causes collapse to one stable
    unexpected-failure code.
    """

    cause = failure.__cause__
    if isinstance(cause, ApplicationError):
        error_code = cause.code
    else:
        error_code = _UNEXPECTED_FAILURE_CODE
    return ParallelIngestionFailureFact(
        agent_name=failure.agent_name,
        error_code=error_code,
    )
