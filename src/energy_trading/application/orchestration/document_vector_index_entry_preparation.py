"""Application-owned document vector index-entry preparation.

This module composes already-normalized extracted chunks through the published
document-embedding port into existing ``DocumentVectorIndexEntry`` values.

Ownership:

* Application: owns ``DocumentVectorIndexEntryPreparationService``.
* Injected: ``DocumentEmbeddingPort``.
* Existing ``DocumentChunkEmbedding``: embedding result reused unchanged.
* Existing ``DocumentVectorIndexEntry``: pairing DTO reused unchanged,
  including identity-match invariants.
* Vector indexing, extraction, embedding providers, vector-database adapters,
  graph routing, and API composition remain deferred.

The service does not index, search, or extract documents.
"""

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.ports.document_embedding import (
    DocumentChunkEmbedding,
    DocumentEmbeddingPort,
)
from energy_trading.application.ports.document_extraction import ExtractedDocumentChunk
from energy_trading.application.ports.document_vector_index import DocumentVectorIndexEntry

_MSG_UNAVAILABLE = "Document vector index entries could not be prepared."


class DocumentVectorIndexEntryPreparationService:
    """Compose extracted chunks through embedding into index entries.

    Constructor dependency is the published document-embedding port.
    ``prepare`` awaits that port exactly once, then pairs each input chunk
    with the corresponding embedding into ``DocumentVectorIndexEntry``.
    """

    def __init__(self, document_embedding_port: DocumentEmbeddingPort) -> None:
        self._document_embedding_port = document_embedding_port

    async def prepare(
        self,
        *,
        chunks: tuple[ExtractedDocumentChunk, ...],
    ) -> tuple[DocumentVectorIndexEntry, ...]:
        """Return published index entries for already-normalized chunks.

        Chunks are forwarded unchanged to ``embed``. Empty input remains a
        valid empty result. Cardinality or identity mismatches fail closed.
        """

        embeddings = await self._document_embedding_port.embed(chunks)
        return _to_index_entries(chunks, embeddings)


def _to_index_entries(
    chunks: tuple[ExtractedDocumentChunk, ...],
    embeddings: object,
) -> tuple[DocumentVectorIndexEntry, ...]:
    if not isinstance(embeddings, tuple) or len(embeddings) != len(chunks):
        raise DependencyUnavailableError(_MSG_UNAVAILABLE)
    entries: list[DocumentVectorIndexEntry] = []
    for chunk, embedding in zip(chunks, embeddings, strict=True):
        if (
            not isinstance(embedding, DocumentChunkEmbedding)
            or embedding.document_id != chunk.document_id
            or embedding.chunk_id != chunk.chunk_id
        ):
            raise DependencyUnavailableError(_MSG_UNAVAILABLE)
        entries.append(DocumentVectorIndexEntry(chunk=chunk, embedding=embedding))
    return tuple(entries)
