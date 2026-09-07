"""Application-owned Phase 2 tuple-level failure-fact classification.

This module classifies already-attributed ``ParallelIngestionAgentFailure``
objects into sanitized ``ParallelIngestionFailureFact`` values by delegating
each element to the existing one-leaf classifier. It does not select a
primary failure, inspect causal exceptions, or construct policy context.

Ownership:

* Application: owns ``classify_parallel_ingestion_agent_failures``.
* Existing ``classify_parallel_ingestion_agent_failure``: reused unchanged.
* Existing ``ParallelIngestionAgentFailure``: reused unchanged as input.
* Existing ``ParallelIngestionFailureFact``: reused unchanged as output.
* Multi-failure selection, attempt tracking, policy-context
  construction, policy/action handling, and graph routing remain deferred.

The composer does not duplicate error-code mapping.
"""

from energy_trading.application.orchestration.parallel_ingestion_agent_failure import (
    ParallelIngestionAgentFailure,
)
from energy_trading.application.orchestration.parallel_ingestion_failure_fact import (
    ParallelIngestionFailureFact,
    classify_parallel_ingestion_agent_failure,
)


def classify_parallel_ingestion_agent_failures(
    failures: tuple[ParallelIngestionAgentFailure, ...],
) -> tuple[ParallelIngestionFailureFact, ...]:
    """Return sanitized Phase 2 failure facts for already-attributed leaves.

    Each input element is classified independently by the existing one-leaf
    classifier. Encounter order, cardinality, and duplicate agent identities
    are preserved. An empty input yields an empty output.
    """

    return tuple(classify_parallel_ingestion_agent_failure(failure) for failure in failures)
