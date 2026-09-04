"""Application-owned Dead Letter Queue sink port.

Infrastructure adapters construct ``DLQRecord`` metadata and may store failed
raw payloads behind ``payload_reference``. The application/orchestration layer
may later pass those metadata records to this port. Persistence, transport,
and retries are infrastructure concerns and are not defined here.
"""

from typing import Protocol

from energy_trading.domain.models.ingestion import DLQRecord


class DeadLetterQueuePort(Protocol):
    """Sink for canonical DLQ metadata. No raw payload is accepted."""

    async def enqueue(self, record: DLQRecord) -> None:
        """Accept one canonical DLQ metadata record for later persistence."""
        ...
