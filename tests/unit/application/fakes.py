"""Test-only fakes that structurally satisfy application ports.

These types must never be copied into production infrastructure.
"""

from datetime import datetime

from energy_trading.application.errors import ConflictError
from energy_trading.application.ports import (
    ConsumptionRepositoryPort,
    DeadLetterQueuePort,
    DocumentExtractionPort,
    DocumentExtractionResult,
    ExtractedDocumentChunk,
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


class FakeDocumentExtractor:
    """In-memory document extractor returning normalized chunks only."""

    def __init__(
        self,
        *,
        source_name: str = "fake-document",
        document_id: str = "doc-1",
        chunks: tuple[ExtractedDocumentChunk, ...] = (),
        diagnostics: tuple[AdapterDiagnostic, ...] = (),
        dlq_records: tuple[DLQRecord, ...] = (),
    ) -> None:
        self._source_name = source_name
        self._result = DocumentExtractionResult(
            source_name=source_name,
            document_id=document_id,
            chunks=chunks,
            diagnostics=diagnostics,
            dlq_records=dlq_records,
        )

    @property
    def source_name(self) -> str:
        return self._source_name

    async def extract(self) -> DocumentExtractionResult:
        return self._result


def as_document_extraction_port(adapter: FakeDocumentExtractor) -> DocumentExtractionPort:
    return adapter


class FakeConsumptionRepository:
    """In-memory Consumption writer. No PostgreSQL or SQLAlchemy."""

    def __init__(self) -> None:
        self._stored: dict[tuple[str, datetime], ConsumptionRecord] = {}
        self.raise_conflict = False

    async def save_many(self, records: tuple[ConsumptionRecord, ...]) -> None:
        if self.raise_conflict:
            raise ConflictError("A conflicting consumption observation already exists")
        for record in records:
            identity = (record.consumer_id, record.timestamp)
            existing = self._stored.get(identity)
            if existing is not None and existing != record:
                raise ConflictError("A conflicting consumption observation already exists")
            self._stored[identity] = record

    @property
    def records(self) -> tuple[ConsumptionRecord, ...]:
        return tuple(self._stored.values())


def as_consumption_repository_port(
    repository: FakeConsumptionRepository,
) -> ConsumptionRepositoryPort:
    return repository
