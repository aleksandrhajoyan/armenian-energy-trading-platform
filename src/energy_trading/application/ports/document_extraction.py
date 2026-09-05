"""Application-facing unstructured document extraction boundary.

Future infrastructure adapters acquire PDF/document bytes, parse or OCR them,
and normalize extracted text. This module defines the only types the
application may see after that work: immutable extracted chunks, adapter
diagnostics, and DLQ metadata. Raw document bytes, filesystem paths, URLs,
OCR-provider schemas, and arbitrary dictionaries never cross this boundary.

Ownership:

* Infrastructure adapter (future): read the document, extract text, emit
  ``AdapterDiagnostic`` values, store or reference failed raw bytes through
  infrastructure mechanisms, and construct ``DLQRecord`` metadata.
* Application / orchestration: receive ``DocumentExtractionResult`` and may
  later pass normalized chunks to embedding/indexing. Extracted text is not
  an authoritative ``RegulatoryConstraint``.
* DLQ infrastructure: persist canonical ``DLQRecord`` metadata independently.

No PDF parser, OCR engine, embedding, Qdrant, or retrieval implementation
lives here.
"""

from dataclasses import dataclass
from typing import Protocol

from energy_trading.domain.models.ingestion import AdapterDiagnostic, DLQRecord


@dataclass(frozen=True, slots=True)
class ExtractedDocumentChunk:
    """Normalized extracted text plus minimal generic provenance.

    This is an application DTO, not a canonical business entity and not a
    regulatory constraint. It carries no embeddings, vendor OCR fields, file
    paths, URLs, or raw bytes.
    """

    document_id: str
    chunk_id: str
    ordinal: int
    text: str
    page_number: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "document_id", _require_non_empty("document_id", self.document_id))
        object.__setattr__(self, "chunk_id", _require_non_empty("chunk_id", self.chunk_id))
        object.__setattr__(self, "text", _require_non_empty("text", self.text))
        object.__setattr__(self, "ordinal", _require_non_negative_int("ordinal", self.ordinal))
        if self.page_number is not None:
            object.__setattr__(
                self,
                "page_number",
                _require_positive_int("page_number", self.page_number),
            )


@dataclass(frozen=True, slots=True)
class DocumentExtractionResult:
    """Immutable application orchestration envelope for one document extraction.

    This is not a persisted domain entity. It references normalized chunks,
    ``AdapterDiagnostic`` values, and ``DLQRecord`` metadata. It never embeds
    raw document payloads; ``DLQRecord.payload_reference`` is the only handle
    to failed raw data.

    All of the following are valid:

    * complete success: one or more chunks, optional diagnostics, no DLQ
    * partial extraction: some chunks, diagnostics, and one or more DLQ records
    * complete extraction/normalization failure: no chunks, diagnostics, DLQ
    * document that yields no normalized text: empty chunks, optional diagnostics
    """

    source_name: str
    document_id: str
    chunks: tuple[ExtractedDocumentChunk, ...]
    diagnostics: tuple[AdapterDiagnostic, ...]
    dlq_records: tuple[DLQRecord, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_name", _require_non_empty("source_name", self.source_name))
        object.__setattr__(self, "document_id", _require_non_empty("document_id", self.document_id))
        _require_tuple("chunks", self.chunks)
        _require_tuple("diagnostics", self.diagnostics)
        _require_tuple("dlq_records", self.dlq_records)
        if not all(isinstance(item, ExtractedDocumentChunk) for item in self.chunks):
            msg = "chunks must contain ExtractedDocumentChunk values"
            raise TypeError(msg)
        if not all(isinstance(item, AdapterDiagnostic) for item in self.diagnostics):
            msg = "diagnostics must contain AdapterDiagnostic values"
            raise TypeError(msg)
        if not all(isinstance(item, DLQRecord) for item in self.dlq_records):
            msg = "dlq_records must contain DLQRecord values"
            raise TypeError(msg)
        mismatched = [item.chunk_id for item in self.chunks if item.document_id != self.document_id]
        if mismatched:
            msg = "chunk document_id must match the result document_id"
            raise ValueError(msg)
        chunk_ids = [item.chunk_id for item in self.chunks]
        if len(chunk_ids) != len(set(chunk_ids)):
            msg = "chunk_id values must be unique within one result"
            raise ValueError(msg)


class DocumentExtractionPort(Protocol):
    """Application-owned port for unstructured document extraction.

    Infrastructure implementations satisfy this protocol structurally. The
    application depends on the protocol, never on a concrete adapter.

    The port exposes a stable source/adapter identity. It must not expose file
    paths, URLs, API tokens, OCR credentials, or vendor parser objects.

    ``extract`` accepts no raw document. Acquisition, parsing, and OCR belong
    to the infrastructure implementation.
    """

    @property
    def source_name(self) -> str:
        """Canonical non-empty source/adapter identity."""
        ...

    async def extract(self) -> DocumentExtractionResult:
        """Collect a normalized document extraction result.

        Partial success and complete extraction failure are first-class
        results. Implementations must not raise merely because the result
        contains DLQ entries or because the document yielded no text.
        """
        ...


def _require_non_empty(field_name: str, value: object) -> str:
    if not isinstance(value, str):
        msg = f"{field_name} must be a string"
        raise TypeError(msg)
    cleaned = value.strip()
    if not cleaned:
        msg = f"{field_name} must be a non-empty string"
        raise ValueError(msg)
    return cleaned


def _require_non_negative_int(field_name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{field_name} must be an integer"
        raise TypeError(msg)
    if value < 0:
        msg = f"{field_name} must be greater than or equal to 0"
        raise ValueError(msg)
    return value


def _require_positive_int(field_name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{field_name} must be an integer"
        raise TypeError(msg)
    if value < 1:
        msg = f"{field_name} must be greater than or equal to 1"
        raise ValueError(msg)
    return value


def _require_tuple(field_name: str, value: object) -> None:
    if not isinstance(value, tuple):
        msg = f"{field_name} must be an immutable tuple"
        raise TypeError(msg)
