"""Application-owned document vector-search query preparation.

This module composes already-normalized query text through the published
query-embedding port into an existing ``DocumentVectorSearchQuery``.

Ownership:

* Application: owns ``DocumentVectorSearchQueryPreparationService``.
* Injected: ``DocumentQueryEmbeddingPort``.
* Existing ``DocumentQueryEmbedding``: embedding result reused unchanged.
* Existing ``DocumentVectorSearchQuery``: search-request construction reused
  unchanged, including limit validation.
* Vector search, Regulatory Intelligence, embedding providers,
  vector-database adapters, graph routing, and API composition remain deferred.

The service does not search, rewrite query text, clamp limits, or invoke
Regulatory Intelligence.
"""

from energy_trading.application.ports.document_query_embedding import DocumentQueryEmbeddingPort
from energy_trading.application.ports.document_vector_search import DocumentVectorSearchQuery


class DocumentVectorSearchQueryPreparationService:
    """Compose query text plus an explicit limit into a search query.

    Constructor dependency is the published query-embedding port.
    ``prepare`` awaits that port exactly once, then constructs
    ``DocumentVectorSearchQuery`` from the returned vector and the
    caller-supplied limit.
    """

    def __init__(self, document_query_embedding_port: DocumentQueryEmbeddingPort) -> None:
        self._document_query_embedding_port = document_query_embedding_port

    async def prepare(self, *, query_text: str, limit: int) -> DocumentVectorSearchQuery:
        """Return a published search query from query text and a result limit.

        Query text is forwarded unchanged to ``embed_query``. Limit validation
        remains owned by ``DocumentVectorSearchQuery``.
        """

        embedding = await self._document_query_embedding_port.embed_query(query_text)
        return DocumentVectorSearchQuery(vector=embedding.vector, limit=limit)
