"""Application-owned Phase 2 failure-policy context resolution.

This module composes already-sanitized failure facts, the published
selection boundary, the published attempt-number source, and the
existing context builder into one ``FailurePolicyContext``.

Ownership:

* Application: owns ``ParallelIngestionFailureContextResolutionService``.
* Injected ports: ``ParallelIngestionFailureSelectionPort`` and
  ``ParallelIngestionAttemptNumberPort``.
* Existing ``build_parallel_ingestion_failure_policy_context``: owns
  context construction.
* Concrete selection, attempt tracking, policy decision, action
  execution, and graph routing remain deferred.

The service does not implement a selector, does not track attempts,
and does not invoke failure policy.
"""

from energy_trading.application.orchestration.failure_policy import FailurePolicyContext
from energy_trading.application.orchestration.parallel_ingestion_attempt_number import (
    ParallelIngestionAttemptNumberPort,
)
from energy_trading.application.orchestration.parallel_ingestion_failure_context import (
    build_parallel_ingestion_failure_policy_context,
)
from energy_trading.application.orchestration.parallel_ingestion_failure_fact import (
    ParallelIngestionFailureFact,
)
from energy_trading.application.orchestration.parallel_ingestion_failure_selection import (
    ParallelIngestionFailureSelectionPort,
)
from energy_trading.application.orchestration.state import WorkflowPhase


class ParallelIngestionFailureContextResolutionService:
    """Phase-2-specific composition of selection, attempt lookup, and context.

    Constructor dependencies are the published selection and attempt-number
    ports. ``resolve`` selects once, awaits the attempt number once, then
    delegates to the published context builder.
    """

    def __init__(
        self,
        selection_port: ParallelIngestionFailureSelectionPort,
        attempt_number_port: ParallelIngestionAttemptNumberPort,
    ) -> None:
        self._selection_port = selection_port
        self._attempt_number_port = attempt_number_port

    async def resolve(
        self,
        *,
        workflow_id: str,
        phase: WorkflowPhase,
        facts: tuple[ParallelIngestionFailureFact, ...],
    ) -> FailurePolicyContext:
        """Return a published failure-policy context from sanitized facts.

        The injected selection port is called exactly once with the supplied
        facts tuple. The injected attempt-number port is awaited exactly
        once with the supplied workflow identity. Context construction is
        delegated to ``build_parallel_ingestion_failure_policy_context``.
        """

        selected_fact = self._selection_port.select(facts)
        attempt_number = await self._attempt_number_port.get_attempt_number(workflow_id)
        return build_parallel_ingestion_failure_policy_context(
            phase=phase,
            error_code=selected_fact.error_code,
            attempt_number=attempt_number,
            agent_name=selected_fact.agent_name,
        )
