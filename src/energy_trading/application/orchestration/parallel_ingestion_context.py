"""Application-owned parallel Phase 2 workflow-context boundary.

This module defines the typed seam a future graph node may use to:

* resolve an already-prepared ``ParallelIngestionPlan`` by workflow identity
* record an already-produced ``ParallelIngestionSuccess`` for that identity

Ownership:

* Application: owns ``ParallelIngestionWorkflowContextPort``.
* Existing contracts: ``ParallelIngestionPlan`` and
  ``ParallelIngestionSuccess`` are reused unchanged.
* Workflow identity: the parameter type is the published
  ``WorkflowState.workflow_id`` type. This module does not redefine
  workflow identity and does not embed plan or success on
  ``WorkflowState``.

The protocol does not choose storage technology, execute agents, or
encode missing-plan, retry, fallback, or degraded semantics. There is no
concrete production implementation in this module.
"""

from typing import Protocol

from energy_trading.application.orchestration.parallel_ingestion import (
    ParallelIngestionPlan,
    ParallelIngestionSuccess,
)


class ParallelIngestionWorkflowContextPort(Protocol):
    """Framework-neutral Phase 2 workflow-context contract.

    Implementations satisfy this protocol structurally. There is no
    application base class and no concrete production context.

    ``resolve_plan`` returns the already-prepared typed plan for one
    workflow identity. ``record_success`` records the all-five-success
    aggregate for that identity. Neither operation mutates the supplied
    DTOs or exposes persistence, cache, or graph-runtime types.
    """

    async def resolve_plan(self, workflow_id: str) -> ParallelIngestionPlan:
        """Return the already-prepared Phase 2 plan for ``workflow_id``."""
        ...

    async def record_success(
        self,
        workflow_id: str,
        success: ParallelIngestionSuccess,
    ) -> None:
        """Record the all-five-success Phase 2 aggregate for ``workflow_id``."""
        ...
