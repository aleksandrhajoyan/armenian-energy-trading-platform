"""Application-owned Regulatory Intelligence workflow-context boundary.

This module defines the typed seam a future graph node may use to:

* resolve an already-prepared ``RegulatoryIntelligenceWorkflowRequest``
  from a ``WorkflowState`` snapshot
* record an already-produced ``RegulatoryIntelligenceResult`` for that
  snapshot

Ownership:

* Application: owns ``RegulatoryIntelligenceWorkflowContextPort``.
* Existing contracts: ``WorkflowState``,
  ``RegulatoryIntelligenceWorkflowRequest``, and
  ``RegulatoryIntelligenceResult`` are reused unchanged.
* Workflow snapshot: phase-specific Regulatory input and output stay
  outside the published seven-field ``WorkflowState``. This module does
  not embed request or result fields on that snapshot.

The protocol does not choose storage technology, construct query text,
choose a limit, execute the workflow step, or encode missing-request,
retry, fallback, or degraded semantics. There is no concrete production
implementation in this module.
"""

from typing import Protocol

from energy_trading.application.agents.regulatory_intelligence import (
    RegulatoryIntelligenceResult,
)
from energy_trading.application.orchestration.regulatory_intelligence_workflow_step import (
    RegulatoryIntelligenceWorkflowRequest,
)
from energy_trading.application.orchestration.state import WorkflowState


class RegulatoryIntelligenceWorkflowContextPort(Protocol):
    """Framework-neutral Regulatory workflow-context contract.

    Implementations satisfy this protocol structurally. There is no
    application base class and no concrete production context.

    ``resolve_request`` returns the already-prepared typed request for one
    workflow snapshot. ``record_result`` records the existing typed
    result for that snapshot. Neither operation mutates the supplied
    DTOs or exposes persistence, cache, or graph-runtime types.
    """

    async def resolve_request(
        self,
        *,
        state: WorkflowState,
    ) -> RegulatoryIntelligenceWorkflowRequest:
        """Return the already-prepared Regulatory request for ``state``."""
        ...

    async def record_result(
        self,
        *,
        state: WorkflowState,
        result: RegulatoryIntelligenceResult,
    ) -> None:
        """Record the existing Regulatory result for ``state``."""
        ...
