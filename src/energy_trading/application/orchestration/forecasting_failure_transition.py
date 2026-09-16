"""Application-owned terminal Phase 3 failure control-state transition.

This module defines the one Phase-3-specific replacement from a valid
``forecasting`` / ``running`` snapshot to ``forecasting`` / ``failed``.

Ownership:

* Application: owns ``fail_after_forecasting``.
* Existing ``WorkflowState``: reused unchanged. Transition policy does not
  live on the snapshot type.
* Existing ``advance_after_forecasting``: remains the sole success
  replacement in ``forecasting_transition.py``.
* Graph runtime, failure-policy execution, degraded mode, exception
  mapping, diagnostics mutation, context write, and API composition remain
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
    "Forecasting failure transition requires forecasting phase and running status."
)


def fail_after_forecasting(state: WorkflowState) -> WorkflowState:
    """Return a forecasting/failed snapshot after terminal Phase 3 failure.

    Valid only when ``state.phase is WorkflowPhase.FORECASTING`` and
    ``state.status is WorkflowStatus.RUNNING``. The input snapshot is not
    mutated. Identity, delivery date, correlation ID, and diagnostics are
    preserved. This replacement is terminal for the current workflow
    attempt and does not continue into Phase 4.
    """

    if state.phase is not WorkflowPhase.FORECASTING or state.status is not WorkflowStatus.RUNNING:
        raise InvalidRequestError(_INVALID_TRANSITION_MESSAGE)
    return replace(
        state,
        phase=WorkflowPhase.FORECASTING,
        status=WorkflowStatus.FAILED,
    )
