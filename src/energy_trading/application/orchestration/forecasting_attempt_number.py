"""Application-owned Phase 3 attempt-number source boundary.

This module defines the typed seam that returns the current 1-based
forecasting execution attempt for one workflow identity.

Ownership:

* Application: owns ``ForecastingAttemptNumberPort``.
* Concrete tracking, mutation, policy-context construction, and graph
  routing remain deferred.

This is a Phase-3-specific Protocol only. There is no production
implementation in this module. The contract is read-only.
"""

from typing import Protocol


class ForecastingAttemptNumberPort(Protocol):
    """Framework-neutral Phase 3 attempt-number source contract.

    Implementations satisfy this protocol structurally. There is no
    application base class and no concrete production source.

    ``get_attempt_number`` accepts only a workflow identity string and
    returns the current 1-based attempt as ``int``. It must not accept
    snapshots, failure facts, policy types, or exception objects.
    """

    async def get_attempt_number(self, workflow_id: str) -> int:
        """Return the current 1-based Phase 3 forecasting attempt for ``workflow_id``."""
        ...
