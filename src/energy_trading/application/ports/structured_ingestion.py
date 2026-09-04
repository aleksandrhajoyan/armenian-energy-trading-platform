"""Application-facing structured ingestion boundary.

Infrastructure adapters acquire and normalize raw external data. This module
defines the only types the application may see after that work: canonical
domain records, adapter diagnostics, and DLQ metadata. Raw payloads never
cross this boundary.

Ownership:

* Infrastructure adapter: read the external payload, interpret the source
  schema, attempt normalization, emit ``AdapterDiagnostic`` values, store or
  reference failed raw data through infrastructure mechanisms, and construct
  ``DLQRecord`` metadata.
* Application / orchestration: receive ``StructuredIngestionResult`` and may
  later pass ``dlq_records`` to ``DeadLetterQueuePort``.
* DLQ infrastructure: persist or forward those metadata records later.

No CSV, Excel, API, HTML, mapping, or persistence implementation lives here.
"""

from dataclasses import dataclass
from typing import Protocol

from energy_trading.domain.models.base import CanonicalModel
from energy_trading.domain.models.ingestion import AdapterDiagnostic, DLQRecord


@dataclass(frozen=True, slots=True)
class StructuredIngestionResult[TRecord: CanonicalModel]:
    """Immutable application orchestration envelope for one ingestion batch.

    This is not a persisted domain entity and does not duplicate canonical
    Pydantic models. It references canonical records, ``AdapterDiagnostic``
    values, and ``DLQRecord`` metadata. It never embeds raw source payloads;
    ``DLQRecord.payload_reference`` is the only handle to failed raw data.

    All of the following are valid:

    * complete success: one or more records, optional diagnostics, no DLQ
    * partial success: some records, diagnostics, and one or more DLQ records
    * complete normalization failure: no records, diagnostics, and DLQ records
    * valid empty source: all three collections empty
    """

    source_name: str
    records: tuple[TRecord, ...]
    diagnostics: tuple[AdapterDiagnostic, ...]
    dlq_records: tuple[DLQRecord, ...]

    def __post_init__(self) -> None:
        source_name = self.source_name.strip()
        if not source_name:
            msg = "source_name must be a non-empty string"
            raise ValueError(msg)
        if source_name != self.source_name:
            object.__setattr__(self, "source_name", source_name)
        _require_tuple("records", self.records)
        _require_tuple("diagnostics", self.diagnostics)
        _require_tuple("dlq_records", self.dlq_records)
        if not all(isinstance(item, CanonicalModel) for item in self.records):
            msg = "records must contain canonical domain models"
            raise TypeError(msg)
        if not all(isinstance(item, AdapterDiagnostic) for item in self.diagnostics):
            msg = "diagnostics must contain AdapterDiagnostic values"
            raise TypeError(msg)
        if not all(isinstance(item, DLQRecord) for item in self.dlq_records):
            msg = "dlq_records must contain DLQRecord values"
            raise TypeError(msg)


class StructuredIngestionPort[TRecord: CanonicalModel](Protocol):
    """Application-owned port for canonical structured ingestion.

    Infrastructure implementations satisfy this protocol structurally. The
    application depends on the protocol, never on a concrete adapter.

    The port exposes a stable source/adapter identity. It must not expose file
    paths, URLs, API tokens, spreadsheet names, or vendor credentials.

    ``ingest`` accepts no raw payload. Acquisition and normalization of source
    data belong to the infrastructure implementation.
    """

    @property
    def source_name(self) -> str:
        """Canonical non-empty source/adapter identity."""
        ...

    async def ingest(self) -> StructuredIngestionResult[TRecord]:
        """Collect a canonical ingestion batch.

        Partial success and complete normalization failure are first-class
        results. Implementations must not raise merely because the batch
        contains DLQ entries or because the source contained no rows.
        """
        ...


def _require_tuple(field_name: str, value: object) -> None:
    if not isinstance(value, tuple):
        msg = f"{field_name} must be an immutable tuple"
        raise TypeError(msg)
