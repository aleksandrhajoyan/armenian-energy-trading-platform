"""Application-owned Phase 3 ExceptionGroup attributed-leaf extraction.

This module extracts already-attributed ``ForecastingAgentFailure`` leaves
from a possibly nested exception group. It does not classify failures,
select a primary failure, or invoke failure policy.

Ownership:

* Application: owns ``extract_forecasting_agent_failures``.
* Existing ``ForecastingAgentFailure``: reused unchanged.
* Existing ``InvalidRequestError``: used when a leaf is unattributed.
* Error-code mapping, multi-failure selection, attempt tracking,
  policy/context handling, and graph routing remain deferred.

The function does not mutate or rebuild exception groups.
"""

from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.orchestration.forecasting_agent_failure import (
    ForecastingAgentFailure,
)

_UNATTRIBUTED_FAILURE_MESSAGE = "Forecasting failure group contains an unattributed failure."


def extract_forecasting_agent_failures(
    failure: BaseExceptionGroup[BaseException],
) -> tuple[ForecastingAgentFailure, ...]:
    """Return attributed Phase 3 agent failures in depth-first encounter order.

    Nested exception groups are traversed left to right. Exact original
    ``ForecastingAgentFailure`` objects are returned. Unattributed leaves
    fail closed as ``InvalidRequestError``.
    """

    extracted: list[ForecastingAgentFailure] = []
    for item in failure.exceptions:
        if isinstance(item, BaseExceptionGroup):
            extracted.extend(extract_forecasting_agent_failures(item))
        elif isinstance(item, ForecastingAgentFailure):
            extracted.append(item)
        else:
            raise InvalidRequestError(_UNATTRIBUTED_FAILURE_MESSAGE)
    return tuple(extracted)
