"""Application-owned forecasting-success read boundary.

This module defines the typed read-only seam a future application consumer
may use to retrieve an already-published ``ForecastingSuccess`` by explicit
workflow identity.

Ownership:

* Application: owns ``ForecastingSuccessReadPort``.
* Existing contracts: ``ForecastingSuccess`` is reused unchanged. Workflow
  identity uses the published ``WorkflowState.workflow_id`` type (``str``).
* Writes: recording a success remains the responsibility of
  ``ForecastingWorkflowContextPort.record_success``. This module does not
  record, replace, or delete results.

The protocol does not choose storage technology, select forecasting
models, execute agents, mutate workflow state, or encode retry, fallback,
or degraded semantics. A future concrete implementation must fail closed
when no success is available rather than synthesize one. There is no
concrete production implementation in this module.
"""

from typing import Protocol

from energy_trading.application.orchestration.forecasting_success import ForecastingSuccess


class ForecastingSuccessReadPort(Protocol):
    """Framework-neutral read-only Phase 3 success contract.

    Implementations satisfy this protocol structurally. There is no
    application base class and no concrete production reader.

    ``get_success`` returns the already-published all-two-success
    aggregate for one explicit workflow identity. It never returns a
    fabricated or empty substitute when no success is available.
    """

    async def get_success(self, *, workflow_id: str) -> ForecastingSuccess:
        """Return the published forecasting success for ``workflow_id``."""
        ...
