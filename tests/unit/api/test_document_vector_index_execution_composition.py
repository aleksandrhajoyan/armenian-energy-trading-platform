"""Document vector index execution composition wires published application objects."""

from __future__ import annotations

import inspect

import pytest

from energy_trading.api.composition import build_document_vector_index_execution
from energy_trading.application.errors import ConflictError, DependencyUnavailableError
from energy_trading.application.orchestration import (
    DocumentVectorIndexEntryPreparationService,
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

_SENTINEL_VECTOR: tuple[float, ...] = (1.0, 0.0, -0.25)
_EMBEDDING_UNAVAILABLE_MESSAGE = "Document embedding is unavailable."
_INDEX_CONFLICT_MESSAGE = "A conflicting document chunk is already indexed."


class _FakeDocumentEmbedder:
    """Test-only fake that structurally satisfies ``DocumentEmbeddingPort``."""

    def __init__(
        self,
        *,
        embeddings: tuple[DocumentChunkEmbedding, ...] | None = None,
        error: BaseException | None = None,
    ) -> None:
        self._embeddings = embeddings
        self._error = error
        self.calls: list[tuple[ExtractedDocumentChunk, ...]] = []

    async def embed(
        self,
        chunks: tuple[ExtractedDocumentChunk, ...],
    ) -> tuple[DocumentChunkEmbedding, ...]:
        self.calls.append(chunks)
        if self._error is not None:
            raise self._error
        if self._embeddings is not None:
            return self._embeddings
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

    def __init__(self, *, error: BaseException | None = None) -> None:
        self._error = error
        self.calls: list[tuple[DocumentVectorIndexEntry, ...]] = []

    async def index(self, entries: tuple[DocumentVectorIndexEntry, ...]) -> None:
        self.calls.append(entries)
        if self._error is not None:
            raise self._error


def _as_embedding_port(embedder: _FakeDocumentEmbedder) -> DocumentEmbeddingPort:
    return embedder


def _as_index_port(index: _FakeDocumentVectorIndex) -> DocumentVectorIndexPort:
    return index


def _build(
    embedder: _FakeDocumentEmbedder,
    index: _FakeDocumentVectorIndex,
) -> DocumentVectorIndexExecutionService:
    return build_document_vector_index_execution(
        document_embedding_port=_as_embedding_port(embedder),
        document_vector_index_port=_as_index_port(index),
    )


def _chunk(**overrides: object) -> ExtractedDocumentChunk:
    values: dict[str, object] = {
        "document_id": "doc-1",
        "chunk_id": "chunk-1",
        "ordinal": 0,
        "text": "Normalized extracted text.",
        "page_number": 1,
    }
    values.update(overrides)
    return ExtractedDocumentChunk(**values)  # type: ignore[arg-type]


def _embedding(**overrides: object) -> DocumentChunkEmbedding:
    values: dict[str, object] = {
        "document_id": "doc-1",
        "chunk_id": "chunk-1",
        "vector": _SENTINEL_VECTOR,
    }
    values.update(overrides)
    return DocumentChunkEmbedding(**values)  # type: ignore[arg-type]


def test_builder_signature_is_keyword_only_two_application_ports() -> None:
    signature = inspect.signature(build_document_vector_index_execution)
    assert tuple(signature.parameters) == (
        "document_embedding_port",
        "document_vector_index_port",
    )
    for name in signature.parameters:
        parameter = signature.parameters[name]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["document_embedding_port"].annotation is DocumentEmbeddingPort
    assert signature.parameters["document_vector_index_port"].annotation is DocumentVectorIndexPort
    assert signature.return_annotation is DocumentVectorIndexExecutionService
    assert not inspect.iscoroutinefunction(build_document_vector_index_execution)


def test_builder_accepts_structural_port_fakes_and_returns_execution_service() -> None:
    service = _build(_FakeDocumentEmbedder(), _FakeDocumentVectorIndex())
    assert isinstance(service, DocumentVectorIndexExecutionService)
    assert DocumentEmbeddingPort not in _FakeDocumentEmbedder.__mro__
    assert DocumentVectorIndexPort not in _FakeDocumentVectorIndex.__mro__


def test_builder_wires_real_application_objects_to_the_supplied_ports() -> None:
    embedder = _FakeDocumentEmbedder()
    index = _FakeDocumentVectorIndex()
    service = _build(embedder, index)

    preparation = service._preparation_service
    assert isinstance(preparation, DocumentVectorIndexEntryPreparationService)
    assert isinstance(service, DocumentVectorIndexExecutionService)
    assert preparation._document_embedding_port is embedder
    assert service._document_vector_index_port is index


def test_builder_does_not_invoke_ports_or_application_runtime() -> None:
    embedder = _FakeDocumentEmbedder()
    index = _FakeDocumentVectorIndex()

    _build(embedder, index)

    assert embedder.calls == []
    assert index.calls == []


async def test_built_service_runs_chunks_through_real_application_stack() -> None:
    first = _chunk(chunk_id="chunk-a", ordinal=0, text="First normalized chunk.")
    second = _chunk(chunk_id="chunk-b", ordinal=1, text="Second normalized chunk.")
    third = _chunk(
        document_id="doc-2",
        chunk_id="chunk-a",
        ordinal=0,
        text="Same chunk_id under a different document.",
    )
    chunks = (first, second, third)
    embeddings = (
        _embedding(document_id="doc-1", chunk_id="chunk-a", vector=(0.5, -1.0)),
        _embedding(document_id="doc-1", chunk_id="chunk-b", vector=(1.25, 0.0)),
        _embedding(document_id="doc-2", chunk_id="chunk-a", vector=(-0.25, 2.0)),
    )
    embedder = _FakeDocumentEmbedder(embeddings=embeddings)
    index = _FakeDocumentVectorIndex()
    service = _build(embedder, index)

    result = await service.execute(chunks=chunks)

    assert result is None
    assert embedder.calls == [chunks]
    assert embedder.calls[0] is chunks
    assert len(embedder.calls) == 1
    assert len(index.calls) == 1
    entries = index.calls[0]
    assert len(entries) == 3
    assert [entry.chunk for entry in entries] == [first, second, third]
    assert entries[0].chunk is first
    assert entries[1].chunk is second
    assert entries[2].chunk is third
    assert [entry.embedding for entry in entries] == list(embeddings)
    assert entries[0].embedding is embeddings[0]
    assert [entry.chunk.chunk_id for entry in entries] == ["chunk-a", "chunk-b", "chunk-a"]
    assert [entry.chunk.document_id for entry in entries] == ["doc-1", "doc-1", "doc-2"]


async def test_built_service_empty_input_embeds_and_indexes_empty_tuple() -> None:
    chunks: tuple[ExtractedDocumentChunk, ...] = ()
    embedder = _FakeDocumentEmbedder(embeddings=())
    index = _FakeDocumentVectorIndex()
    service = _build(embedder, index)

    result = await service.execute(chunks=chunks)

    assert result is None
    assert embedder.calls == [chunks]
    assert embedder.calls[0] is chunks
    assert index.calls == [()]
    assert len(embedder.calls) == 1
    assert len(index.calls) == 1


async def test_built_service_propagates_embedding_failure_unchanged() -> None:
    error = DependencyUnavailableError(_EMBEDDING_UNAVAILABLE_MESSAGE)
    chunks = (_chunk(),)
    embedder = _FakeDocumentEmbedder(error=error)
    index = _FakeDocumentVectorIndex()
    service = _build(embedder, index)

    with pytest.raises(DependencyUnavailableError) as caught:
        await service.execute(chunks=chunks)

    assert caught.value is error
    assert caught.value.message == _EMBEDDING_UNAVAILABLE_MESSAGE
    assert embedder.calls == [chunks]
    assert index.calls == []


async def test_built_service_propagates_index_failure_unchanged() -> None:
    error = ConflictError(_INDEX_CONFLICT_MESSAGE)
    chunks = (_chunk(),)
    embedder = _FakeDocumentEmbedder()
    index = _FakeDocumentVectorIndex(error=error)
    service = _build(embedder, index)

    with pytest.raises(ConflictError) as caught:
        await service.execute(chunks=chunks)

    assert caught.value is error
    assert caught.value.message == _INDEX_CONFLICT_MESSAGE
    assert len(embedder.calls) == 1
    assert len(index.calls) == 1
