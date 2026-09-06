"""Application-owned document vector retrieval/search boundary.

This port sits after indexing. A caller supplies an already-embedded numeric
query vector. A future outer-layer implementation will search a configured
document index and return ranked normalized chunks.

Ownership:

* Application: owns ``DocumentVectorSearchPort`` and
  ``DocumentVectorSearchQuery``, including ranking order, result-limit, and
  identity-uniqueness semantics.
* Outer implementation (future): structurally implements the protocol.
  Distance/similarity configuration, collection names, point IDs, payloads,
  and client objects remain infrastructure concerns. There is no
  infrastructure base class and no generic ``VectorStore``.
* Query-text embedding remains a separate deferred concern. This port does
  not convert query text into a vector and does not extend
  ``DocumentEmbeddingPort``.
* Indexing remains ``DocumentVectorIndexPort``. This port does not index,
  upsert, delete, or manage collections.

Returned chunks are ordered most relevant to least relevant according to the
concrete implementation. The application contract does not expose cosine,
dot-product, Euclidean, or raw backend scores. Zero matches are a valid
empty tuple, not ``ResourceNotFoundError``.

Logical identity ``(document_id, chunk_id)`` appears at most once in one
result. Duplicate backend identities, more hits than ``limit``, or a result
that cannot reconstruct ``ExtractedDocumentChunk`` fail closed as sanitized
``DependencyUnavailableError``.

Privacy: search input is a numeric vector plus a positive result count.
Search output is only normalized ``ExtractedDocumentChunk`` values. Query
vectors and retrieved chunk text are not operationally logged by this
module.
"""

from dataclasses import dataclass
from math import isfinite
from typing import Protocol

from energy_trading.application.ports.document_extraction import ExtractedDocumentChunk


@dataclass(frozen=True, slots=True)
class DocumentVectorSearchQuery:
    """Already-embedded numeric query plus a positive result limit.

    This is an application orchestration DTO, not a canonical domain entity
    and not a ``RegulatoryConstraint``. It carries no query text, provider,
    model, dimension, distance, collection, score, or filter fields.
    """

    vector: tuple[float, ...]
    limit: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "vector", _require_query_vector(self.vector))
        object.__setattr__(self, "limit", _require_positive_limit(self.limit))


class DocumentVectorSearchPort(Protocol):
    """Application-owned retrieval port for already-embedded document queries.

    Infrastructure implementations satisfy this protocol structurally. The
    application depends on the protocol, never on a concrete vector database
    or generic store type.

    ``search`` accepts only ``DocumentVectorSearchQuery``. It must not accept
    query text, paths, URLs, Qdrant types, collection names, filters, or
    score thresholds. Backend configuration belongs to a future concrete
    adapter constructor.

    Conforming implementations:

    * return ``0 <= len(results) <= query.limit``
    * treat an empty result tuple as a valid search outcome
    * must not fabricate results to meet ``limit``
    * order results most relevant to least relevant
    * return existing ``ExtractedDocumentChunk`` values, not embeddings,
      scores, or backend payloads
    * keep ``(document_id, chunk_id)`` unique within one result
    * treat the same ``chunk_id`` under different documents as distinct
    * do not index, embed query text, or manage collections

    A query vector incompatible with the configured index dimension, when
    clearly a request incompatibility, becomes ``InvalidRequestError``
    without exposing vector contents. Unavailable or unusable backends,
    including duplicate logical hits, too many hits, malformed payloads,
    and chunks that cannot be reconstructed, become sanitized
    ``DependencyUnavailableError``. Retries belong to later orchestration
    or a specifically designed outer implementation policy.
    """

    async def search(
        self,
        query: DocumentVectorSearchQuery,
    ) -> tuple[ExtractedDocumentChunk, ...]:
        """Return ranked normalized chunks for an already-embedded query."""
        ...


def _require_query_vector(value: object) -> tuple[float, ...]:
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


def _require_positive_limit(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = "limit must be an integer"
        raise TypeError(msg)
    if value < 1:
        msg = "limit must be greater than 0"
        raise ValueError(msg)
    return value
