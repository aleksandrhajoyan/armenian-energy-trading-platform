"""HTTP transport contracts for Document Vector Index requests.

These models project already-normalized extracted-chunk fields for a future
indexing route. They do not invoke the service, own lifecycle, or install a
route.
"""

from pydantic import BaseModel, ConfigDict


class DocumentVectorIndexChunkRequest(BaseModel):
    """HTTP body for one already-normalized extracted document chunk.

    Field names match application ``ExtractedDocumentChunk``. This is not the
    application DTO and does not accept raw documents, paths, or embeddings.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str
    chunk_id: str
    text: str
    ordinal: int
    page_number: int | None = None


class DocumentVectorIndexRequest(BaseModel):
    """HTTP body for a future Document Vector Index execution request.

    Carries already-normalized chunk transport DTOs only. There is no
    response contract in this module.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    chunks: tuple[DocumentVectorIndexChunkRequest, ...]
