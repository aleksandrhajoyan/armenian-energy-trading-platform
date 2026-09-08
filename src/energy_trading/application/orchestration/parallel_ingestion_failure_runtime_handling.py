"""Application-owned Phase 2 runtime failure-handling composition.

This module sequences an already-observed ``BaseExceptionGroup`` through
the published failure-context preparation service and the published
prepared failure-handling service.

Ownership:

* Application: owns ``ParallelIngestionFailureRuntimeHandlingService``.
* Injected: ``ParallelIngestionFailureContextPreparationService``.
* Injected: ``ParallelIngestionFailureHandlingService``.
* Existing preparation, decision, action, and transition modules remain
  the owners of their respective semantics.
* Graph routing remains deferred.

The service does not inspect exception groups, does not decide a
policy action, and does not reimplement terminal transitions.
"""

from energy_trading.application.orchestration.parallel_ingestion_failure_context_preparation import (  # noqa: E501
    ParallelIngestionFailureContextPreparationService,
)
from energy_trading.application.orchestration.parallel_ingestion_failure_handling import (
    ParallelIngestionFailureHandlingService,
)
from energy_trading.application.orchestration.state import WorkflowState


class ParallelIngestionFailureRuntimeHandlingService:
    """Phase-2-specific composition of failure-context preparation then handling.

    Constructor dependencies are the published preparation and handling
    services. ``handle`` prepares context from the current snapshot and
    failure group, then forwards that context plus the original state.
    """

    def __init__(
        self,
        context_preparation_service: ParallelIngestionFailureContextPreparationService,
        failure_handling_service: ParallelIngestionFailureHandlingService,
    ) -> None:
        self._context_preparation_service = context_preparation_service
        self._failure_handling_service = failure_handling_service

    async def handle(
        self,
        *,
        state: WorkflowState,
        failure_group: BaseExceptionGroup,
    ) -> WorkflowState:
        """Prepare then handle one Phase 2 exception group against ``state``.

        Context preparation is awaited exactly once with ``state.workflow_id``,
        ``state.phase``, and the supplied group. The returned context and the
        original ``state`` are forwarded unchanged to the handling service.
        """

        context = await self._context_preparation_service.prepare(
            workflow_id=state.workflow_id,
            phase=state.phase,
            failure_group=failure_group,
        )
        return await self._failure_handling_service.handle(state=state, context=context)
