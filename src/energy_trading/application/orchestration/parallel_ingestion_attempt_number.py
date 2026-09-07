"""Application-owned Phase 2 attempt-number source boundary.

This module defines the typed seam that returns the current 1-based
parallel-ingestion execution attempt for one workflow identity.

Ownership:

* Application: owns ``ParallelIngestionAttemptNumberPort``.
* Concrete tracking, mutation, policy-context construction, and graph
  routing remain deferred.

This is a Phase-2-specific Protocol only. There is no production
implementation in this module. The contract is read-only.
"""

from typing import Protocol


class ParallelIngestionAttemptNumberPort(Protocol):
    """Framework-neutral Phase 2 attempt-number source contract.

    Implementations satisfy this protocol structurally. There is no
    application base class and no concrete production source.

    ``get_attempt_number`` accepts only a workflow identity string and
    returns the current 1-based attempt as ``int``. It must not accept
    snapshots, failure facts, policy types, or exception objects.
    """

    async def get_attempt_number(self, workflow_id: str) -> int:
        """Return the current 1-based Phase 2 attempt for ``workflow_id``."""
        ...
