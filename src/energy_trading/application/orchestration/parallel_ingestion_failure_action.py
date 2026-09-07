"""Application-owned Phase 2 failure-action execution.

This module interprets an already-decided ``FailureAction`` against one
``WorkflowState``. Terminal ``FAIL`` delegates to the published Phase 2
failure transition. ``RETRY`` and ``FALLBACK`` are rejected as not
implemented.

Ownership:

* Application: owns ``execute_parallel_ingestion_failure_action``.
* Existing ``FailureAction``: reused unchanged.
* Existing ``fail_parallel_ingestion``: owns terminal snapshot replacement.
* Policy decision, context construction, retry/fallback mechanics, and
  graph routing remain deferred.

The function does not decide an action, does not construct policy context,
and does not inspect exceptions or diagnostics.
"""

from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.orchestration.failure_policy import FailureAction
from energy_trading.application.orchestration.parallel_ingestion_failure_transition import (
    fail_parallel_ingestion,
)
from energy_trading.application.orchestration.state import WorkflowState

_RETRY_NOT_IMPLEMENTED_MESSAGE = "Parallel-ingestion retry action is not implemented."
_FALLBACK_NOT_IMPLEMENTED_MESSAGE = "Parallel-ingestion fallback action is not implemented."


def execute_parallel_ingestion_failure_action(
    *,
    state: WorkflowState,
    action: FailureAction,
) -> WorkflowState:
    """Execute one already-decided Phase 2 failure action against ``state``.

    ``FAIL`` returns ``fail_parallel_ingestion(state)``. ``RETRY`` and
    ``FALLBACK`` fail closed because those executions are not implemented.
    Invalid ``FAIL`` snapshots keep the published terminal-transition error.
    """

    match action:
        case FailureAction.FAIL:
            return fail_parallel_ingestion(state)
        case FailureAction.RETRY:
            raise InvalidRequestError(_RETRY_NOT_IMPLEMENTED_MESSAGE)
        case FailureAction.FALLBACK:
            raise InvalidRequestError(_FALLBACK_NOT_IMPLEMENTED_MESSAGE)
