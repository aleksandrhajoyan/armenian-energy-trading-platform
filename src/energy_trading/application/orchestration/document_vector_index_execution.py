"""Application-owned document vector index execution.

This module composes already-published index-entry preparation with the
existing document vector index port. Callers supply already-normalized
extracted chunks. The service does not embed, pair identities, or construct
index entries.

Ownership:

* Application: owns ``DocumentVectorIndexExecutionService``.
* Injected: ``DocumentVectorIndexEntryPreparationService``.
* Injected: ``DocumentVectorIndexPort``.
* Existing ``DocumentVectorIndexEntry``: preparation result reused unchanged.
* Embedding providers, vector-database adapters, graph routing, and API
  composition remain deferred.

The service does not rewrite chunks, reconstruct entries, or search.
"""

from energy_trading.application.orchestration.document_vector_index_entry_preparation import (
    DocumentVectorIndexEntryPreparationService,
)
from energy_trading.application.ports.document_extraction import ExtractedDocumentChunk
from energy_trading.application.ports.document_vector_index import DocumentVectorIndexPort


class DocumentVectorIndexExecutionService:
    """Compose extracted chunks through preparation into vector indexing.

    Constructor dependencies are the published index-entry preparation
    service and the published document vector index port. ``execute`` awaits
    preparation exactly once, then awaits ``index`` exactly once.
    """

    def __init__(
        self,
        preparation_service: DocumentVectorIndexEntryPreparationService,
        document_vector_index_port: DocumentVectorIndexPort,
    ) -> None:
        self._preparation_service = preparation_service
        self._document_vector_index_port = document_vector_index_port

    async def execute(
        self,
        *,
        chunks: tuple[ExtractedDocumentChunk, ...],
    ) -> None:
        """Index already-normalized chunks through published preparation.

        Chunks are forwarded unchanged to ``prepare``. The returned entries
        are forwarded unchanged to ``index``. Empty input remains valid.
        """

        entries = await self._preparation_service.prepare(chunks=chunks)
        await self._document_vector_index_port.index(entries)
