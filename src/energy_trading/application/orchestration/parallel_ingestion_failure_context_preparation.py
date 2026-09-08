"""Application-owned Phase 2 failure-policy context preparation.

This module composes already-published ExceptionGroup extraction,
tuple-level sanitized classification, and failure-context resolution
into one ``FailurePolicyContext``.

Ownership:

* Application: owns ``ParallelIngestionFailureContextPreparationService``.
* Injected: ``ParallelIngestionFailureContextResolutionService``.
* Existing ``extract_parallel_ingestion_agent_failures``: reused unchanged.
* Existing ``classify_parallel_ingestion_agent_failures``: reused unchanged.
* Policy decision, action execution, and graph routing remain deferred.

The service does not interpret exceptions, does not select among facts,
and does not invoke failure policy.
"""

from energy_trading.application.orchestration.failure_policy import FailurePolicyContext
from energy_trading.application.orchestration.parallel_ingestion_exception_group import (
    extract_parallel_ingestion_agent_failures,
)
from energy_trading.application.orchestration.parallel_ingestion_failure_classification import (
    classify_parallel_ingestion_agent_failures,
)
from energy_trading.application.orchestration.parallel_ingestion_failure_context_resolution import (
    ParallelIngestionFailureContextResolutionService,
)
from energy_trading.application.orchestration.state import WorkflowPhase


class ParallelIngestionFailureContextPreparationService:
    """Phase-2-specific composition of extraction, classification, and context.

    Constructor dependency is the published context-resolution service.
    ``prepare`` extracts attributed leaves, classifies them, then awaits
    context resolution.
    """

    def __init__(
        self,
        context_resolution_service: ParallelIngestionFailureContextResolutionService,
    ) -> None:
        self._context_resolution_service = context_resolution_service

    async def prepare(
        self,
        *,
        workflow_id: str,
        phase: WorkflowPhase,
        failure_group: BaseExceptionGroup,
    ) -> FailurePolicyContext:
        """Return a published failure-policy context from one exception group.

        Extraction and tuple classification are delegated to the published
        helpers. Context resolution is awaited exactly once with the
        supplied workflow identity, phase, and classified facts.
        """

        attributed_failures = extract_parallel_ingestion_agent_failures(failure_group)
        classified_facts = classify_parallel_ingestion_agent_failures(attributed_failures)
        return await self._context_resolution_service.resolve(
            workflow_id=workflow_id,
            phase=phase,
            facts=classified_facts,
        )
