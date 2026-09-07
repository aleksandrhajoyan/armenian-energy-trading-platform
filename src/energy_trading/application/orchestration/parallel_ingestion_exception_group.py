"""Application-owned Phase 2 ExceptionGroup attributed-leaf extraction.

This module extracts already-attributed ``ParallelIngestionAgentFailure``
leaves from a possibly nested exception group. It does not classify
failures, select a primary failure, or invoke failure policy.

Ownership:

* Application: owns ``extract_parallel_ingestion_agent_failures``.
* Existing ``ParallelIngestionAgentFailure``: reused unchanged.
* Existing ``InvalidRequestError``: used when a leaf is unattributed.
* Error-code mapping, multi-failure selection, attempt tracking,
  policy/context handling, and graph routing remain deferred.

The function does not mutate or rebuild exception groups.
"""

from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.orchestration.parallel_ingestion_agent_failure import (
    ParallelIngestionAgentFailure,
)

_UNATTRIBUTED_FAILURE_MESSAGE = "Parallel-ingestion failure group contains an unattributed failure."


def extract_parallel_ingestion_agent_failures(
    failure: BaseExceptionGroup[BaseException],
) -> tuple[ParallelIngestionAgentFailure, ...]:
    """Return attributed Phase 2 agent failures in depth-first encounter order.

    Nested exception groups are traversed left to right. Exact original
    ``ParallelIngestionAgentFailure`` objects are returned. Unattributed
    leaves fail closed as ``InvalidRequestError``.
    """

    extracted: list[ParallelIngestionAgentFailure] = []
    for item in failure.exceptions:
        if isinstance(item, BaseExceptionGroup):
            extracted.extend(extract_parallel_ingestion_agent_failures(item))
        elif isinstance(item, ParallelIngestionAgentFailure):
            extracted.append(item)
        else:
            raise InvalidRequestError(_UNATTRIBUTED_FAILURE_MESSAGE)
    return tuple(extracted)
