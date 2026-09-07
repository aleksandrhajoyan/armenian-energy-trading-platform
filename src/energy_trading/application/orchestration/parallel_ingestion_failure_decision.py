"""Application-owned Phase 2 failure-policy decision boundary.

This module delegates an already-prepared ``FailurePolicyContext`` to the
published ``FailurePolicyPort`` and returns the resulting ``FailureAction``.

Ownership:

* Application: owns ``ParallelIngestionFailureDecisionService``.
* Injected port: ``FailurePolicyPort``.
* Context construction, action execution, retry, fallback, terminal
  failure transition, diagnostics, and graph routing remain deferred.

The service does not construct policy context, does not interpret the
returned action, and does not execute it.
"""

from energy_trading.application.orchestration.failure_policy import (
    FailureAction,
    FailurePolicyContext,
    FailurePolicyPort,
)


class ParallelIngestionFailureDecisionService:
    """Phase-2-specific failure-policy decision composition.

    Constructor dependency is the published ``FailurePolicyPort``.
    ``decide`` forwards the supplied context exactly once and returns the
    policy action unchanged.
    """

    def __init__(self, policy: FailurePolicyPort) -> None:
        self._policy = policy

    async def decide(self, context: FailurePolicyContext) -> FailureAction:
        """Return the policy decision for one already-prepared context.

        The injected port is awaited exactly once. The returned
        ``FailureAction`` is not interpreted or executed.
        """

        return await self._policy.decide(context)
