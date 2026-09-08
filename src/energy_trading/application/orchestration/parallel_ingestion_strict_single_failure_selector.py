"""Application-owned Phase 2 strict single-failure selection.

This module implements the published selection contract for the
unambiguous case only: exactly one sanitized failure fact.

Ownership:

* Application: owns ``StrictSingleParallelIngestionFailureSelector``.
* Existing ``ParallelIngestionFailureFact``: reused unchanged.
* Existing ``InvalidRequestError``: empty and multi-fact inputs fail closed.
* Multi-failure ranking, attempt tracking, policy/action handling, and
  graph routing remain deferred.

The selector does not inherit a production Protocol. It satisfies
``ParallelIngestionFailureSelectionPort`` structurally.
"""

from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.orchestration.parallel_ingestion_failure_fact import (
    ParallelIngestionFailureFact,
)

_EXACTLY_ONE_FACT_MESSAGE = (
    "Parallel-ingestion failure selection requires exactly one failure fact."
)


class StrictSingleParallelIngestionFailureSelector:
    """Fail-closed Phase 2 selector for an unambiguous single failure fact.

    Exactly one fact is returned unchanged. Zero or multiple facts raise
    ``InvalidRequestError``. There is no first/last, agent, error-code,
    or severity winner rule.
    """

    def select(
        self,
        facts: tuple[ParallelIngestionFailureFact, ...],
    ) -> ParallelIngestionFailureFact:
        """Return the unique sanitized fact, or fail closed."""

        if len(facts) != 1:
            raise InvalidRequestError(_EXACTLY_ONE_FACT_MESSAGE)
        return facts[0]
