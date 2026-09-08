"""Application-owned Phase 2 initial terminal-fail failure policy.

This module implements the published failure-policy contract for the
current capability set: every valid context decides ``FailureAction.FAIL``.

Ownership:

* Application: owns ``InitialParallelIngestionFailurePolicy``.
* Existing failure-policy port: satisfied structurally.
* Action execution, attempt tracking, and graph routing remain deferred.

The policy does not inherit a production Protocol. It does not inspect
context fields and does not execute the returned action.
"""

from energy_trading.application.orchestration.failure_policy import (
    FailureAction,
    FailurePolicyContext,
)


class InitialParallelIngestionFailurePolicy:
    """Stateless Phase 2 failure policy for the current capability set.

    Every valid ``FailurePolicyContext`` decides ``FailureAction.FAIL``.
    Context is accepted to satisfy the published port and does not affect
    the result.
    """

    async def decide(self, context: FailurePolicyContext) -> FailureAction:
        """Return the only currently supported Phase 2 failure action."""

        return FailureAction.FAIL
