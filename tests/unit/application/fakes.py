"""Test-only fakes that structurally satisfy application ports.

These types must never be copied into production infrastructure.
"""

from energy_trading.application.ports import (
    DeadLetterQueuePort,
    StructuredIngestionPort,
    StructuredIngestionResult,
)
from energy_trading.domain.models import AdapterDiagnostic, ConsumptionRecord, DLQRecord


class FakeConsumptionAdapter:
    """In-memory structured adapter returning canonical consumption records."""

    def __init__(
        self,
        *,
        source_name: str = "fake-consumption",
        records: tuple[ConsumptionRecord, ...] = (),
        diagnostics: tuple[AdapterDiagnostic, ...] = (),
        dlq_records: tuple[DLQRecord, ...] = (),
    ) -> None:
        self._source_name = source_name
        self._result: StructuredIngestionResult[ConsumptionRecord] = StructuredIngestionResult(
            source_name=source_name,
            records=records,
            diagnostics=diagnostics,
            dlq_records=dlq_records,
        )

    @property
    def source_name(self) -> str:
        return self._source_name

    async def ingest(self) -> StructuredIngestionResult[ConsumptionRecord]:
        return self._result


class InMemoryDeadLetterQueue:
    """In-memory DLQ sink. No Redis, filesystem, or database."""

    def __init__(self) -> None:
        self._records: list[DLQRecord] = []

    async def enqueue(self, record: DLQRecord) -> None:
        self._records.append(record)

    @property
    def records(self) -> tuple[DLQRecord, ...]:
        return tuple(self._records)


def as_consumption_port(
    adapter: FakeConsumptionAdapter,
) -> StructuredIngestionPort[ConsumptionRecord]:
    """Application-shaped call site: the port type is the only accepted argument."""

    return adapter


def as_dlq_port(queue: InMemoryDeadLetterQueue) -> DeadLetterQueuePort:
    return queue
