"""Application-owned Regulatory Intelligence workflow-node adapter.

This module coordinates the already-published Regulatory workflow
context and workflow step. It is framework-neutral.

Ownership:

* Application: owns ``RegulatoryIntelligenceWorkflowNodeAdapter``.
* Injected: ``RegulatoryIntelligenceWorkflowContextPort`` and
  ``RegulatoryIntelligenceWorkflowStep``.
* Existing contracts: ``WorkflowState``,
  ``RegulatoryIntelligenceWorkflowRequest``, and
  ``RegulatoryIntelligenceResult`` are reused unchanged.

``run`` resolves a typed request, delegates to the workflow step,
records the existing result, and returns the original
``WorkflowState`` object. It does not mutate or reconstruct that
snapshot. Graph topology, storage, Phase-1 transition, and concrete
context implementation remain deferred.
"""

from energy_trading.application.orchestration.regulatory_intelligence_context import (
    RegulatoryIntelligenceWorkflowContextPort,
)
from energy_trading.application.orchestration.regulatory_intelligence_workflow_step import (
    RegulatoryIntelligenceWorkflowStep,
)
from energy_trading.application.orchestration.state import WorkflowState


class RegulatoryIntelligenceWorkflowNodeAdapter:
    """Framework-neutral Regulatory graph-node coordination.

    Constructor dependencies are the published context port and
    workflow step. ``run`` is resolve → step → record, then return of
    the original workflow state unchanged.
    """

    def __init__(
        self,
        context: RegulatoryIntelligenceWorkflowContextPort,
        workflow_step: RegulatoryIntelligenceWorkflowStep,
    ) -> None:
        self._context = context
        self._workflow_step = workflow_step

    async def run(self, state: WorkflowState) -> WorkflowState:
        """Resolve, execute, and record Regulatory Intelligence for ``state``.

        Failures propagate with their original identity. The original
        ``WorkflowState`` object is returned unchanged.
        """

        request = await self._context.resolve_request(state=state)
        result = await self._workflow_step.run(request)
        await self._context.record_result(state=state, result=result)
        return state
