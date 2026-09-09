"""Outer document vector index object composition.

This module wires already-published application ports into already-published
index-entry preparation and index execution services. It does not load
configuration, construct providers, or invoke embedding or indexing.

Ownership:

* API composition root: owns ``build_document_vector_index_execution``.
* Injected: ``DocumentEmbeddingPort``.
* Injected: ``DocumentVectorIndexPort``.
* Application: owns index-entry preparation and index execution.
* Provider adapters, graph routing, and HTTP routes remain deferred.

The builder constructs objects only. It does not call application runtime
methods.
"""

from energy_trading.application.orchestration.document_vector_index_entry_preparation import (
    DocumentVectorIndexEntryPreparationService,
)
from energy_trading.application.orchestration.document_vector_index_execution import (
    DocumentVectorIndexExecutionService,
)
from energy_trading.application.ports.document_embedding import DocumentEmbeddingPort
from energy_trading.application.ports.document_vector_index import DocumentVectorIndexPort


def build_document_vector_index_execution(
    *,
    document_embedding_port: DocumentEmbeddingPort,
    document_vector_index_port: DocumentVectorIndexPort,
) -> DocumentVectorIndexExecutionService:
    """Return a wired document vector index execution service.

    The two arguments are already-constructed application port
    implementations. This function does not discover, configure, or invoke
    them.
    """

    preparation_service = DocumentVectorIndexEntryPreparationService(document_embedding_port)
    return DocumentVectorIndexExecutionService(
        preparation_service,
        document_vector_index_port,
    )
