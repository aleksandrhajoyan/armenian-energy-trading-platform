"""Application-owned Consumption observation persistence port.

The application/orchestration layer may later pass canonical
``ConsumptionRecord`` values from ingestion results to this port. Persistence
identity, conflict behavior, and storage mechanics are defined here as
application semantics; SQL and sessions stay in infrastructure.
"""

from typing import Protocol

from energy_trading.domain.models.observations import ConsumptionRecord


class ConsumptionRepositoryPort(Protocol):
    """Write-focused sink for canonical Consumption observations."""

    async def save_many(self, records: tuple[ConsumptionRecord, ...]) -> None:
        """Persist canonical Consumption observations atomically.

        Persistence identity is ``(consumer_id, canonical UTC timestamp)``.

        * an empty tuple is a successful no-op
        * one call is one atomic unit of work
        * an identical canonical observation may be retried as a no-op
        * the same identity with a different canonical observation is a conflict
        """
        ...
