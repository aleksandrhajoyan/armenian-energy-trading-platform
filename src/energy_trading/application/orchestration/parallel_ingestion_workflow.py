"""Application-owned Phase 2 parallel-ingestion workflow step.

This module composes the already-published context and execution
boundaries into one framework-neutral application service.

Ownership:

* Application: owns ``ParallelIngestionWorkflowStep``.
* Injected ports: ``ParallelIngestionWorkflowContextPort`` and
  ``ParallelIngestionExecutionPort``.
* Graph runtime, failure-policy execution, retry, fallback, degraded
  mode, phase/status transition, concrete context storage, and API
  composition remain deferred.

The step does not inherit a base class. It does not implement storage
and does not change ``WorkflowState``.
"""

from energy_trading.application.orchestration.parallel_ingestion import (
    ParallelIngestionExecutionPort,
)
from energy_trading.application.orchestration.parallel_ingestion_context import (
    ParallelIngestionWorkflowContextPort,
)
from energy_trading.application.orchestration.state import WorkflowState


class ParallelIngestionWorkflowStep:
    """Framework-neutral Phase 2 ingestion workflow composition.

    Constructor dependencies are the published context and execution
    ports. ``run`` resolves a prepared plan, executes it, records the
    all-five-success aggregate, and returns the original workflow state
    unchanged.
    """

    def __init__(
        self,
        context: ParallelIngestionWorkflowContextPort,
        executor: ParallelIngestionExecutionPort,
    ) -> None:
        self._context = context
        self._executor = executor

    async def run(self, state: WorkflowState) -> WorkflowState:
        """Resolve, execute, and record Phase 2 ingestion for ``state``.

        Uses only ``state.workflow_id``. Failures propagate naturally.
        The original ``WorkflowState`` object is returned unchanged.
        """

        plan = await self._context.resolve_plan(state.workflow_id)
        success = await self._executor.execute(plan)
        await self._context.record_success(state.workflow_id, success)
        return state
