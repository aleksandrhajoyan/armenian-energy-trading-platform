"""Application-owned document vector indexing boundary.

This port sits after extraction and embedding. A caller pairs an already
normalized ``ExtractedDocumentChunk`` with its matching
``DocumentChunkEmbedding``. A future outer-layer implementation will persist
that pair in a vector database.

Ownership:

* Application: owns ``DocumentVectorIndexPort`` and
  ``DocumentVectorIndexEntry``, including identity, idempotency, and
  conflict semantics.
* Outer implementation (future): structurally implements the protocol.
  Collection names, point IDs, payloads, distance metrics, and client
  objects remain infrastructure concerns. There is no infrastructure base
  class and no generic ``VectorStore``.
* Retrieval/search is a separate future application boundary. This port
  does not search, query, retrieve, delete, or manage collections.

Logical identity is ``(document_id, chunk_id)``. Exact retries of the same
application entry are idempotent. The same identity with different chunk
or embedding content fails closed as ``ConflictError``. There is no
last-write-wins, overwrite, or reindex replacement in this contract.

Privacy: only application-normalized chunk text and vectors may be indexed.
Raw PDF bytes, OCR objects, paths, URLs, credentials, vendor dictionaries,
and Qdrant payload objects must never cross this boundary. Chunk text and
full vectors are not operationally logged by this module.
"""

from dataclasses import dataclass
from typing import Protocol

from energy_trading.application.ports.document_embedding import DocumentChunkEmbedding
from energy_trading.application.ports.document_extraction import ExtractedDocumentChunk


@dataclass(frozen=True, slots=True)
class DocumentVectorIndexEntry:
    """Paired normalized chunk and matching embedding for indexing.

    This is an application orchestration/storage-boundary DTO, not a
    canonical domain entity and not a ``RegulatoryConstraint``. It does not
    duplicate nested fields: provenance and text live on ``chunk``; the
    numeric vector lives on ``embedding``.
    """

    chunk: ExtractedDocumentChunk
    embedding: DocumentChunkEmbedding

    def __post_init__(self) -> None:
        _require_extracted_chunk(self.chunk)
        _require_chunk_embedding(self.embedding)
        if self.chunk.document_id != self.embedding.document_id:
            msg = "chunk document_id must match embedding document_id"
            raise ValueError(msg)
        if self.chunk.chunk_id != self.embedding.chunk_id:
            msg = "chunk chunk_id must match embedding chunk_id"
            raise ValueError(msg)


class DocumentVectorIndexPort(Protocol):
    """Application-owned write/indexing port for vectorized document chunks.

    Infrastructure implementations satisfy this protocol structurally. The
    application depends on the protocol, never on a concrete vector database
    or generic store type.

    ``index`` accepts only ``DocumentVectorIndexEntry`` values. It must not
    accept raw documents, paths, URLs, Qdrant types, collection names, or
    search parameters. Backend configuration belongs to a future concrete
    adapter constructor.

    Conforming implementations:

    * treat ``index(())`` as a successful no-op that does not require
      backend I/O
    * identify each entry by ``(document_id, chunk_id)``
    * treat the same ``chunk_id`` under different ``document_id`` values as
      distinct
    * retry an exact same application entry as an idempotent no-op
    * fail closed as ``ConflictError`` when the same identity is supplied
      with different chunk or embedding content, including in-call
      conflicts and previously stored conflicts
    * coalesce exact in-call duplicates for one identity
    * require a single positive vector dimensionality in one non-empty call
    * do not promise cross-entry database transaction atomicity
    * do not search, retrieve, overwrite, or reindex

    Inconsistent vector dimensions in one caller batch become
    ``InvalidRequestError`` without exposing chunk text or vector values.
    Unavailable or unusable backends become sanitized
    ``DependencyUnavailableError``. Retries belong to later orchestration
    or a specifically designed outer implementation policy.
    """

    async def index(
        self,
        entries: tuple[DocumentVectorIndexEntry, ...],
    ) -> None:
        """Index paired document chunks and embeddings.

        Successful return means every logical entry supplied to this call is
        indexed according to the port semantics. Failures must not be
        silently converted to success.
        """
        ...


def _require_extracted_chunk(value: object) -> ExtractedDocumentChunk:
    if not isinstance(value, ExtractedDocumentChunk):
        msg = "chunk must be an ExtractedDocumentChunk"
        raise TypeError(msg)
    return value


def _require_chunk_embedding(value: object) -> DocumentChunkEmbedding:
    if not isinstance(value, DocumentChunkEmbedding):
        msg = "embedding must be a DocumentChunkEmbedding"
        raise TypeError(msg)
    return value
