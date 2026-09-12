"""Application-owned forecasting-phase execution boundary.

``ForecastingExecutionPort`` is the typed seam between a prepared
``ForecastingPlan`` and a successful ``ForecastingSuccess`` aggregate.

Ownership:

* Application: owns ``ForecastingExecutionPort``.
* Existing contracts: ``ForecastingPlan`` and ``ForecastingSuccess`` are
  reused as-is. This module does not shadow or replace them.
* Future execution: a separately reviewed module may implement the port.
  This module does not execute agents, does not choose concurrency, and
  does not encode Consumer → DAM ordering.

The protocol itself does not encode sequential order, parallelism,
Consumer → DAM dependency, retry, fallback, degraded, partial-success,
timeout, cancellation, provider, or model-selection semantics.
"""

from typing import Protocol

from energy_trading.application.orchestration.forecasting_plan import ForecastingPlan
from energy_trading.application.orchestration.forecasting_success import ForecastingSuccess


class ForecastingExecutionPort(Protocol):
    """Framework-neutral forecasting-phase execution contract.

    Implementations satisfy this protocol structurally. There is no
    application base class. A concrete executor lives in a separately
    reviewed module.

    ``execute`` accepts only a prepared ``ForecastingPlan`` and returns
    only ``ForecastingSuccess``. The protocol itself does not encode how
    execution occurs.
    """

    async def execute(self, *, plan: ForecastingPlan) -> ForecastingSuccess:
        """Execute one prepared plan and return the all-two-success aggregate."""
        ...
