"""Application-owned Dead Letter Queue sink port.

The application/orchestration layer may later pass canonical ``DLQRecord``
metadata from ``StructuredIngestionResult.dlq_records`` to this port, one
record at a time. Infrastructure adapters may store failed raw payloads
behind ``payload_reference``; this port never accepts those payloads.

Persistence, transport, and retries are infrastructure concerns. Each
``enqueue`` call is independent: implementations must not promise
cross-record batch atomicity.
"""

from typing import Protocol

from energy_trading.domain.models.ingestion import DLQRecord


class DeadLetterQueuePort(Protocol):
    """Sink for one canonical DLQ metadata record. No raw payload is accepted."""

    async def enqueue(self, record: DLQRecord) -> None:
        """Accept one canonical ``DLQRecord`` for persistence.

        Implementations must treat ``record_id`` as the idempotency key:

        * enqueueing the same canonical record again is a successful no-op
        * the same ``record_id`` with different canonical metadata is a conflict

        Raw external payloads, filesystem paths, and transport handles are not
        part of this signature.
        """
        ...
