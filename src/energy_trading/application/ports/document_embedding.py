"""Application-owned document embedding boundary.

This port sits after unstructured extraction. Input chunks have already
crossed the extraction ACL and contain normalized application text. A future
outer-layer implementation will turn that text into numeric vectors.

Ownership:

* Application: owns ``DocumentEmbeddingPort`` and ``DocumentChunkEmbedding``.
* Outer implementation (future): structurally implements the protocol. There
  is no infrastructure base class and no provider/model selection here.
* Vector indexing/storage and retrieval/search are separate future
  application boundaries. Embedding generation is not a Qdrant
  responsibility.

This boundary does not persist vectors, search, retrieve, interpret
regulatory text, or produce ``RegulatoryConstraint`` values. Query embedding
is deferred until retrieval requirements are designed.

Privacy: the port accepts only ``ExtractedDocumentChunk`` values. Document
bytes, OCR payloads, paths, URLs, credentials, vendor dictionaries, and
Qdrant payload objects must never cross this boundary.
``DocumentChunkEmbedding`` carries opaque identity plus a numeric vector.
Chunk text and vectors are not operationally logged by this module.
"""

from dataclasses import dataclass
from math import isfinite
from typing import Protocol

from energy_trading.application.ports.document_extraction import ExtractedDocumentChunk


@dataclass(frozen=True, slots=True)
class DocumentChunkEmbedding:
    """Numeric embedding for one already-normalized extracted chunk.

    This is an application orchestration DTO, not a canonical domain entity
    and not a ``RegulatoryConstraint``. It carries no provider, model,
    dimension, distance, collection, or metadata fields. Dimension is
    ``len(vector)`` when a caller needs it.
    """

    document_id: str
    chunk_id: str
    vector: tuple[float, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "document_id", _require_non_empty("document_id", self.document_id))
        object.__setattr__(self, "chunk_id", _require_non_empty("chunk_id", self.chunk_id))
        object.__setattr__(self, "vector", _require_embedding_vector(self.vector))


class DocumentEmbeddingPort(Protocol):
    """Application-owned port for embedding normalized document chunks.

    Infrastructure or ML implementations satisfy this protocol structurally.
    The application depends on the protocol, never on a concrete embedding
    provider, model class, or vector database.

    ``embed`` accepts only already-normalized ``ExtractedDocumentChunk``
    values. It must not accept document bytes, paths, URLs, token IDs,
    provider request objects, or Qdrant types.

    Conforming implementations:

    * treat an empty input tuple as a valid empty output tuple
    * emit exactly one embedding per input chunk, in input order
    * copy ``document_id`` and ``chunk_id`` without reinterpretation
    * must not silently omit or fabricate chunks
    * produce a single positive dimensionality for every vector in one
      successful batch
    * persist nothing and search nothing
    * do not produce ``RegulatoryConstraint`` values

    Invalid caller input that did not satisfy this contract becomes
    ``InvalidRequestError`` without exposing chunk text. Unavailable or
    unusable embedding backends, malformed responses, count mismatches,
    invalid vectors, inconsistent dimensions, and timeouts become sanitized
    ``DependencyUnavailableError``. Retries and fallback belong to later
    orchestration or a specifically designed outer implementation policy.
    """

    async def embed(
        self,
        chunks: tuple[ExtractedDocumentChunk, ...],
    ) -> tuple[DocumentChunkEmbedding, ...]:
        """Return one embedding per input chunk, preserving order and identity."""
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


def _require_embedding_vector(value: object) -> tuple[float, ...]:
    if not isinstance(value, tuple):
        msg = "vector must be a tuple"
        raise TypeError(msg)
    if len(value) < 1:
        msg = "vector must contain at least one element"
        raise ValueError(msg)
    validated: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, float):
            msg = "vector elements must be finite floating-point values"
            raise TypeError(msg)
        if not isfinite(item):
            msg = "vector elements must be finite floating-point values"
            raise ValueError(msg)
        validated.append(item)
    return tuple(validated)
