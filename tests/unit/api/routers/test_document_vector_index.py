"""Document Vector Index HTTP route stays a thin unwired transport boundary."""

from __future__ import annotations

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from energy_trading.api.dependencies.document_vector_index import (
    get_document_vector_index_execution_service,
)
from energy_trading.api.exception_handlers import register_exception_handlers
from energy_trading.api.middleware import CorrelationMiddleware
from energy_trading.api.routers.document_vector_index import router
from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.orchestration.document_vector_index_execution import (
    DocumentVectorIndexExecutionService,
)
from energy_trading.application.ports.document_extraction import ExtractedDocumentChunk

_INDEX_PATH = "/api/v1/document-vector-index/index"
_SERVICE_ATTR = "document_vector_index_execution_service"
_UNAVAILABLE_MESSAGE = "Document Vector Index service is unavailable."
_EXECUTION_FAILURE_MESSAGE = "Document vector index execution failed."


class _UnusedDependency:
    async def prepare(self, *, chunks: object) -> None:
        raise AssertionError("overridden execute must not reach preparation")

    async def index(self, entries: object) -> None:
        raise AssertionError("overridden execute must not reach the index port")


class RecordingIndexExecutionService(DocumentVectorIndexExecutionService):
    def __init__(self) -> None:
        super().__init__(_UnusedDependency(), _UnusedDependency())  # type: ignore[arg-type]
        self.calls: list[tuple[ExtractedDocumentChunk, ...]] = []
        self.error: BaseException | None = None

    async def execute(
        self,
        *,
        chunks: tuple[ExtractedDocumentChunk, ...],
    ) -> None:
        self.calls.append(chunks)
        if self.error is not None:
            raise self.error


def _index_app(
    service: DocumentVectorIndexExecutionService | None = None,
) -> FastAPI:
    application = FastAPI()
    application.add_middleware(CorrelationMiddleware)
    register_exception_handlers(application)
    application.include_router(router, prefix="/api/v1")
    if service is not None:
        setattr(application.state, _SERVICE_ATTR, service)
    return application


async def _post_index(application: FastAPI, payload: object) -> object:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post(_INDEX_PATH, json=payload)


def _two_chunk_payload() -> dict[str, object]:
    return {
        "chunks": [
            {
                "document_id": "doc-1",
                "chunk_id": "chunk-1",
                "text": "first already-normalized chunk",
                "ordinal": 0,
                "page_number": 1,
            },
            {
                "document_id": "doc-1",
                "chunk_id": "chunk-2",
                "text": "second already-normalized chunk",
                "ordinal": 1,
                "page_number": 2,
            },
        ]
    }


async def test_successful_index_projects_chunks_and_returns_204() -> None:
    service = RecordingIndexExecutionService()
    response = await _post_index(_index_app(service), _two_chunk_payload())

    assert response.status_code == 204
    assert response.content == b""
    assert len(service.calls) == 1
    chunks = service.calls[0]
    assert tuple(type(chunk) for chunk in chunks) == (
        ExtractedDocumentChunk,
        ExtractedDocumentChunk,
    )
    assert chunks[0] == ExtractedDocumentChunk(
        document_id="doc-1",
        chunk_id="chunk-1",
        text="first already-normalized chunk",
        ordinal=0,
        page_number=1,
    )
    assert chunks[1] == ExtractedDocumentChunk(
        document_id="doc-1",
        chunk_id="chunk-2",
        text="second already-normalized chunk",
        ordinal=1,
        page_number=2,
    )
    assert chunks[0].chunk_id == "chunk-1"
    assert chunks[1].chunk_id == "chunk-2"


async def test_optional_page_number_none_survives_projection() -> None:
    service = RecordingIndexExecutionService()
    response = await _post_index(
        _index_app(service),
        {
            "chunks": [
                {
                    "document_id": "doc-1",
                    "chunk_id": "chunk-1",
                    "text": "chunk without a page",
                    "ordinal": 3,
                }
            ]
        },
    )

    assert response.status_code == 204
    assert response.content == b""
    assert len(service.calls) == 1
    chunk = service.calls[0][0]
    assert isinstance(chunk, ExtractedDocumentChunk)
    assert chunk.page_number is None
    assert chunk.document_id == "doc-1"
    assert chunk.chunk_id == "chunk-1"
    assert chunk.text == "chunk without a page"
    assert chunk.ordinal == 3


async def test_route_uses_published_accessor_via_app_state() -> None:
    service = RecordingIndexExecutionService()
    application = _index_app(service)
    response = await _post_index(application, _two_chunk_payload())

    assert response.status_code == 204
    assert service.calls[0][0].document_id == "doc-1"
    assert getattr(application.state, _SERVICE_ATTR) is service


async def test_dependency_override_supplies_the_service_without_app_state() -> None:
    service = RecordingIndexExecutionService()
    application = _index_app(None)
    application.dependency_overrides[get_document_vector_index_execution_service] = lambda: service
    response = await _post_index(application, _two_chunk_payload())

    assert response.status_code == 204
    assert response.content == b""
    assert len(service.calls) == 1
    assert not hasattr(application.state, _SERVICE_ATTR)


async def test_application_error_from_execute_uses_centralized_mapping() -> None:
    service = RecordingIndexExecutionService()
    service.error = InvalidRequestError(_EXECUTION_FAILURE_MESSAGE)
    response = await _post_index(_index_app(service), _two_chunk_payload())

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "invalid_request"
    assert error["message"] == _EXECUTION_FAILURE_MESSAGE
    assert len(service.calls) == 1
    assert "traceback" not in response.text.lower()


async def test_missing_lifespan_state_uses_published_accessor_and_existing_503() -> None:
    response = await _post_index(_index_app(None), _two_chunk_payload())

    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == "dependency_unavailable"
    assert error["message"] == _UNAVAILABLE_MESSAGE
