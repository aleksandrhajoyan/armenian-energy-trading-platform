"""Production create_app installs the Document Vector Index router under the API prefix."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from energy_trading.api.app import create_app
from energy_trading.api.composition.document_vector_index_execution import (
    build_document_vector_index_execution,
)
from energy_trading.application.orchestration.document_vector_index_execution import (
    DocumentVectorIndexExecutionService,
)
from energy_trading.application.ports.document_embedding import (
    DocumentChunkEmbedding,
    DocumentEmbeddingPort,
)
from energy_trading.application.ports.document_extraction import ExtractedDocumentChunk
from energy_trading.application.ports.document_vector_index import (
    DocumentVectorIndexEntry,
    DocumentVectorIndexPort,
)
from tests.unit.api.helpers import make_test_settings, noop_lifespan

_INDEX_PATH = "/api/v1/document-vector-index/index"
_QUERY_PATH = "/api/v1/regulatory-intelligence/query"
_HEALTH_PATH = "/api/v1/health"
_SERVICE_ATTR = "document_vector_index_execution_service"
_UNAVAILABLE_MESSAGE = "Document Vector Index service is unavailable."
_REGULATORY_UNAVAILABLE_MESSAGE = "Regulatory Intelligence service is unavailable."
_SENTINEL_VECTOR: tuple[float, ...] = (1.0, 0.0, -0.25)


class _FakeDocumentEmbedder:
    """Test-only fake that structurally satisfies ``DocumentEmbeddingPort``."""

    def __init__(self) -> None:
        self.calls: list[tuple[ExtractedDocumentChunk, ...]] = []

    async def embed(
        self,
        chunks: tuple[ExtractedDocumentChunk, ...],
    ) -> tuple[DocumentChunkEmbedding, ...]:
        self.calls.append(chunks)
        return tuple(
            DocumentChunkEmbedding(
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_id,
                vector=_SENTINEL_VECTOR,
            )
            for chunk in chunks
        )


class _FakeDocumentVectorIndex:
    """Test-only fake that structurally satisfies ``DocumentVectorIndexPort``."""

    def __init__(self) -> None:
        self.calls: list[tuple[DocumentVectorIndexEntry, ...]] = []

    async def index(self, entries: tuple[DocumentVectorIndexEntry, ...]) -> None:
        self.calls.append(entries)


def _as_embedding_port(embedder: _FakeDocumentEmbedder) -> DocumentEmbeddingPort:
    return embedder


def _as_index_port(index: _FakeDocumentVectorIndex) -> DocumentVectorIndexPort:
    return index


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


def _install_service_lifespan(
    service: DocumentVectorIndexExecutionService,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        setattr(app.state, _SERVICE_ATTR, service)
        try:
            yield
        finally:
            if hasattr(app.state, _SERVICE_ATTR):
                delattr(app.state, _SERVICE_ATTR)

    return lifespan


async def test_production_index_route_exists_and_health_regulatory_stay_offline() -> None:
    application = create_app(make_test_settings(), lifespan=noop_lifespan)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        index = await client.post(_INDEX_PATH, json=_two_chunk_payload())
        query = await client.post(
            _QUERY_PATH,
            json={"query_text": "some text", "limit": 3},
        )
        health = await client.get(_HEALTH_PATH)

    assert index.status_code != 404
    assert index.status_code == 503
    error = index.json()["error"]
    assert error["code"] == "dependency_unavailable"
    assert error["message"] == _UNAVAILABLE_MESSAGE
    assert query.status_code != 404
    assert query.status_code == 503
    regulatory_error = query.json()["error"]
    assert regulatory_error["code"] == "dependency_unavailable"
    assert regulatory_error["message"] == _REGULATORY_UNAVAILABLE_MESSAGE
    assert health.status_code == 200
    assert health.json() == {
        "status": "ok",
        "service": "AI Energy Trading Platform",
        "environment": "test",
    }


def test_production_create_app_index_route_forwards_to_the_published_service() -> None:
    embedder = _FakeDocumentEmbedder()
    index = _FakeDocumentVectorIndex()
    service = build_document_vector_index_execution(
        document_embedding_port=_as_embedding_port(embedder),
        document_vector_index_port=_as_index_port(index),
    )
    application = create_app(
        make_test_settings(),
        lifespan=_install_service_lifespan(service),
    )
    assert embedder.calls == []
    assert index.calls == []
    assert hasattr(application.state, _SERVICE_ATTR) is False

    with TestClient(application) as client:
        assert application.state.document_vector_index_execution_service is service
        response = client.post(_INDEX_PATH, json=_two_chunk_payload())
        health = client.get(_HEALTH_PATH)

    assert response.status_code == 204
    assert response.content == b""
    assert health.status_code == 200
    assert len(embedder.calls) == 1
    chunks = embedder.calls[0]
    assert chunks == (
        ExtractedDocumentChunk(
            document_id="doc-1",
            chunk_id="chunk-1",
            text="first already-normalized chunk",
            ordinal=0,
            page_number=1,
        ),
        ExtractedDocumentChunk(
            document_id="doc-1",
            chunk_id="chunk-2",
            text="second already-normalized chunk",
            ordinal=1,
            page_number=2,
        ),
    )
    assert len(index.calls) == 1
    indexed_chunks = tuple(entry.chunk for entry in index.calls[0])
    assert indexed_chunks == chunks
    assert hasattr(application.state, _SERVICE_ATTR) is False
