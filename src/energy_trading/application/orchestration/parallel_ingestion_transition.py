"""Application-owned successful Phase 2 control-state transition.

This module defines the one Phase-2-specific replacement from a valid
``ingestion`` / ``running`` snapshot to ``forecasting`` / ``running``.

Ownership:

* Application: owns ``advance_after_parallel_ingestion``.
* Existing ``WorkflowState``: reused unchanged. Transition policy does not
  live on the snapshot type.
* Graph runtime, Phase 3 execution, retry, fallback, degraded mode, and
  API composition remain deferred.

The function does not mutate the input snapshot and does not append or
clear diagnostics.
"""

from dataclasses import replace

from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.orchestration.state import (
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
)

_INVALID_TRANSITION_MESSAGE = (
    "Parallel-ingestion success transition requires ingestion phase and running status."
)


def advance_after_parallel_ingestion(state: WorkflowState) -> WorkflowState:
    """Return a forecasting/running snapshot after successful Phase 2 ingestion.

    Valid only when ``state.phase is WorkflowPhase.INGESTION`` and
    ``state.status is WorkflowStatus.RUNNING``. The input snapshot is not
    mutated. Identity, delivery date, correlation ID, and diagnostics are
    preserved.
    """

    if state.phase is not WorkflowPhase.INGESTION or state.status is not WorkflowStatus.RUNNING:
        raise InvalidRequestError(_INVALID_TRANSITION_MESSAGE)
    return replace(
        state,
        phase=WorkflowPhase.FORECASTING,
        status=WorkflowStatus.RUNNING,
    )
