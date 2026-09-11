"""Application-owned document extraction-to-index execution.

This module composes already-published document extraction with the existing
document vector index execution service. Callers supply no runtime source.
The service does not parse documents, embed, or construct index entries.

Ownership:

* Application: owns ``DocumentExtractionIndexExecutionService``.
* Injected: ``DocumentExtractionPort``.
* Injected: ``DocumentVectorIndexExecutionService``.
* Existing ``DocumentExtractionResult``: returned unchanged.
* PDF adapters, embedding providers, vector-database adapters, graph routing,
  and API composition remain deferred.

The service does not rewrite chunks, synthesize diagnostics, or persist DLQ
records. Empty extraction does not invoke indexing.
"""

from energy_trading.application.orchestration.document_vector_index_execution import (
    DocumentVectorIndexExecutionService,
)
from energy_trading.application.ports.document_extraction import (
    DocumentExtractionPort,
    DocumentExtractionResult,
)


class DocumentExtractionIndexExecutionService:
    """Compose one extraction into optional vector-index execution.

    Constructor dependencies are the published extraction port and the
    published document vector index execution service. ``execute`` awaits
    extraction exactly once, then awaits index execution only when chunks
    exist.
    """

    def __init__(
        self,
        document_extraction_port: DocumentExtractionPort,
        index_execution_service: DocumentVectorIndexExecutionService,
    ) -> None:
        self._document_extraction_port = document_extraction_port
        self._index_execution_service = index_execution_service

    async def execute(self) -> DocumentExtractionResult:
        """Extract once, then index non-empty chunks through published execution.

        The returned result is the exact object produced by extraction.
        Empty ``chunks`` skips index execution.
        """

        result = await self._document_extraction_port.extract()
        if result.chunks:
            await self._index_execution_service.execute(chunks=result.chunks)
        return result
