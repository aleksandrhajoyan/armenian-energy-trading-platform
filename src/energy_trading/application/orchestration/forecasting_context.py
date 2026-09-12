"""Application-owned forecasting-phase workflow-context boundary.

This module defines the typed seam a future workflow step may use to:

* resolve an already-prepared ``ForecastingPlan`` from a ``WorkflowState``
  snapshot
* record an already-produced ``ForecastingSuccess`` for that snapshot

Ownership:

* Application: owns ``ForecastingWorkflowContextPort``.
* Existing contracts: ``WorkflowState``, ``ForecastingPlan``, and
  ``ForecastingSuccess`` are reused unchanged.
* Workflow snapshot: phase-specific forecasting input and output stay
  outside the published seven-field ``WorkflowState``. This module does
  not embed plan or success fields on that snapshot.

The protocol does not choose storage technology, execute agents, choose
concurrency or Consumer → DAM ordering, or encode missing-plan, retry,
fallback, or degraded semantics. There is no concrete production
implementation in this module.
"""

from typing import Protocol

from energy_trading.application.orchestration.forecasting_plan import ForecastingPlan
from energy_trading.application.orchestration.forecasting_success import ForecastingSuccess
from energy_trading.application.orchestration.state import WorkflowState


class ForecastingWorkflowContextPort(Protocol):
    """Framework-neutral Phase 3 workflow-context contract.

    Implementations satisfy this protocol structurally. There is no
    application base class and no concrete production context.

    ``resolve_plan`` returns the already-prepared typed plan for one
    workflow snapshot. ``record_success`` records the all-two-success
    aggregate for that snapshot. Neither operation mutates the supplied
    DTOs or exposes persistence, cache, or graph-runtime types.
    """

    async def resolve_plan(self, *, state: WorkflowState) -> ForecastingPlan:
        """Return the already-prepared forecasting plan for ``state``."""
        ...

    async def record_success(
        self,
        *,
        state: WorkflowState,
        success: ForecastingSuccess,
    ) -> None:
        """Record the all-two-success forecasting aggregate for ``state``."""
        ...
