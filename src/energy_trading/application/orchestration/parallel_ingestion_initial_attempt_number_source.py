"""Application-owned Phase 2 initial attempt-number source.

This module implements the published attempt-number contract for the
current no-retry runtime: the only supported Phase 2 execution is
attempt ``1``.

Ownership:

* Application: owns ``InitialParallelIngestionAttemptNumberSource``.
* Existing ``ParallelIngestionAttemptNumberPort``: satisfied structurally.
* Attempt tracking, increment/reset, durable storage, retry execution, and
  graph routing remain deferred.

The source does not inherit a production Protocol. It is not a tracker.
"""


class InitialParallelIngestionAttemptNumberSource:
    """Stateless Phase 2 attempt source for the current no-retry runtime.

    Every workflow identity resolves to attempt ``1``. The workflow ID is
    accepted to satisfy the published port and does not affect the result.
    """

    async def get_attempt_number(self, workflow_id: str) -> int:
        """Return the currently supported Phase 2 attempt number."""

        return 1
