"""Application-owned terminal Phase 2 failure control-state transition.

This module defines the one Phase-2-specific replacement from a valid
``ingestion`` / ``running`` snapshot to ``ingestion`` / ``failed``.

Ownership:

* Application: owns ``fail_parallel_ingestion``.
* Existing ``WorkflowState``: reused unchanged. Transition policy does not
  live on the snapshot type.
* Graph runtime, failure-policy execution, retry, fallback, degraded mode,
  exception mapping, diagnostics mutation, and API composition remain
  deferred.

The function does not mutate the input snapshot and does not append or
clear diagnostics. It does not accept an exception or error argument.
"""

from dataclasses import replace

from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.orchestration.state import (
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
)

_INVALID_TRANSITION_MESSAGE = (
    "Parallel-ingestion failure transition requires ingestion phase and running status."
)


def fail_parallel_ingestion(state: WorkflowState) -> WorkflowState:
    """Return an ingestion/failed snapshot after terminal Phase 2 failure.

    Valid only when ``state.phase is WorkflowPhase.INGESTION`` and
    ``state.status is WorkflowStatus.RUNNING``. The input snapshot is not
    mutated. Identity, delivery date, correlation ID, and diagnostics are
    preserved. This replacement is terminal for the current workflow
    attempt and does not continue into Phase 3.
    """

    if state.phase is not WorkflowPhase.INGESTION or state.status is not WorkflowStatus.RUNNING:
        raise InvalidRequestError(_INVALID_TRANSITION_MESSAGE)
    return replace(
        state,
        phase=WorkflowPhase.INGESTION,
        status=WorkflowStatus.FAILED,
    )
