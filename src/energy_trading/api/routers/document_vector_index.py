"""Document Vector Index HTTP indexing route.

This module is a thin transport boundary. It binds the published request DTO,
resolves the published index-execution service through FastAPI ``Depends``,
projects already-normalized chunk fields into ``ExtractedDocumentChunk``, and
invokes ``execute`` once. Success is HTTP 204 with no body. Production
``create_app()`` installs this router under the existing API prefix.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from energy_trading.api.dependencies.document_vector_index import (
    get_document_vector_index_execution_service,
)
from energy_trading.api.schemas.document_vector_index import DocumentVectorIndexRequest
from energy_trading.application.orchestration.document_vector_index_execution import (
    DocumentVectorIndexExecutionService,
)
from energy_trading.application.ports.document_extraction import ExtractedDocumentChunk

router = APIRouter(prefix="/document-vector-index", tags=["document-vector-index"])


@router.post("/index", status_code=204)
async def index_document_vectors(
    request: DocumentVectorIndexRequest,
    service: Annotated[
        DocumentVectorIndexExecutionService,
        Depends(get_document_vector_index_execution_service),
    ],
) -> None:
    """Index already-normalized document chunks and return no content."""

    chunks = tuple(
        ExtractedDocumentChunk(
            document_id=chunk.document_id,
            chunk_id=chunk.chunk_id,
            text=chunk.text,
            ordinal=chunk.ordinal,
            page_number=chunk.page_number,
        )
        for chunk in request.chunks
    )
    await service.execute(chunks=chunks)
