"""Application-owned successful Phase 3 control-state transition.

This module defines the one Phase-3-specific replacement from a valid
``forecasting`` / ``running`` snapshot to ``risk_and_bid`` / ``running``.

Ownership:

* Application: owns ``advance_after_forecasting``.
* Existing ``WorkflowState``: reused unchanged. Transition policy does not
  live on the snapshot type.
* Graph runtime, Phase 4 execution, retry, fallback, degraded mode, and
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
    "Forecasting success transition requires forecasting phase and running status."
)


def advance_after_forecasting(state: WorkflowState) -> WorkflowState:
    """Return a risk_and_bid/running snapshot after successful Phase 3 forecasting.

    Valid only when ``state.phase is WorkflowPhase.FORECASTING`` and
    ``state.status is WorkflowStatus.RUNNING``. The input snapshot is not
    mutated. Identity, delivery date, correlation ID, and diagnostics are
    preserved.
    """

    if state.phase is not WorkflowPhase.FORECASTING or state.status is not WorkflowStatus.RUNNING:
        raise InvalidRequestError(_INVALID_TRANSITION_MESSAGE)
    return replace(
        state,
        phase=WorkflowPhase.RISK_AND_BID,
        status=WorkflowStatus.RUNNING,
    )
