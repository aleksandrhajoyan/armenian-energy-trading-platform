"""Application-owned document query-text embedding boundary.

This port sits before vector retrieval. A caller supplies already-normalized
application query text. A future outer-layer implementation will turn that
text into a finite numeric vector. Query-text embedding is not document-chunk
embedding and is not vector search.

Ownership:

* Application: owns ``DocumentQueryEmbeddingPort`` and
  ``DocumentQueryEmbedding``.
* Outer implementation (future): structurally implements the protocol.
  Provider identity, model names, credentials, HTTP clients, and token
  limits remain infrastructure concerns. There is no infrastructure base
  class and no generic ``EmbeddingPort`` or ``LLMPort``.
* Document-chunk embedding remains ``DocumentEmbeddingPort``. This port does
  not accept ``ExtractedDocumentChunk`` values and does not copy document or
  chunk identity.
* Vector search remains ``DocumentVectorSearchPort``. This port does not
  construct ``DocumentVectorSearchQuery``, search, or know Qdrant.
* Regulatory Intelligence remains unwired. This port does not import or
  invoke that agent.

Privacy: the port accepts only a query-text string. Document bytes, paths,
URLs, prompts, chat messages, credentials, and Qdrant types must never cross
this boundary. Query text and vectors are not operationally logged by this
module.
"""

from dataclasses import dataclass
from math import isfinite
from typing import Protocol


@dataclass(frozen=True, slots=True)
class DocumentQueryEmbedding:
    """Numeric embedding for one already-normalized query string.

    This is an application orchestration DTO, not a canonical domain entity
    and not a ``RegulatoryConstraint``. It carries no query text, provider,
    model, dimension, distance, collection, score, or metadata fields.
    Dimension is ``len(vector)`` when a caller needs it.
    """

    vector: tuple[float, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "vector", _require_embedding_vector(self.vector))


class DocumentQueryEmbeddingPort(Protocol):
    """Application-owned port for embedding normalized query text.

    Infrastructure or ML implementations satisfy this protocol structurally.
    The application depends on the protocol, never on a concrete embedding
    provider, model class, or vector database.

    ``embed_query`` accepts only ``query_text: str``. It must not accept
    document chunks, bytes, paths, URLs, token IDs, prompt objects, chat
    messages, provider request objects, or Qdrant types.

    Conforming implementations:

    * return one finite embedding vector for one query string
    * must not search, index, or persist
    * must not construct ``DocumentVectorSearchQuery``
    * must not produce ``RegulatoryConstraint`` values
    * treat empty or whitespace-only ``query_text`` as
      ``InvalidRequestError`` without exposing the query text

    Unavailable or unusable embedding backends, malformed responses,
    invalid vectors, and timeouts become sanitized
    ``DependencyUnavailableError``. Retries and fallback belong to later
    orchestration or a specifically designed outer implementation policy.
    """

    async def embed_query(self, query_text: str) -> DocumentQueryEmbedding:
        """Return a finite embedding vector for already-normalized query text."""
        ...


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
