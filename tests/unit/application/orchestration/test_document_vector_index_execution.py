"""Document vector index execution composes preparation with indexing."""

from __future__ import annotations

import inspect
from typing import cast

import pytest

from energy_trading.application.errors import ConflictError, DependencyUnavailableError
from energy_trading.application.orchestration import (
    DocumentVectorIndexEntryPreparationService,
    DocumentVectorIndexExecutionService,
)
from energy_trading.application.ports.document_embedding import DocumentChunkEmbedding
from energy_trading.application.ports.document_extraction import ExtractedDocumentChunk
from energy_trading.application.ports.document_vector_index import (
    DocumentVectorIndexEntry,
    DocumentVectorIndexPort,
)

_SENTINEL_VECTOR: tuple[float, ...] = (1.0, 0.0, -0.25)
_PREPARE_UNAVAILABLE_MESSAGE = "Document vector index entries could not be prepared."
_INDEX_UNAVAILABLE_MESSAGE = "Document vector index is unavailable."
_INDEX_CONFLICT_MESSAGE = "A conflicting document chunk is already indexed."


class _RecordingPreparationService:
    """Test-only recorder. Not a production Protocol or abstraction."""

    def __init__(
        self,
        *,
        entries: tuple[DocumentVectorIndexEntry, ...] | None = None,
        error: BaseException | None = None,
    ) -> None:
        self._entries = entries
        self._error = error
        self.calls: list[tuple[ExtractedDocumentChunk, ...]] = []
        self.embed_calls = 0

    async def prepare(
        self,
        *,
        chunks: tuple[ExtractedDocumentChunk, ...],
    ) -> tuple[DocumentVectorIndexEntry, ...]:
        self.calls.append(chunks)
        if self._error is not None:
            raise self._error
        if self._entries is None:
            msg = "recording preparation double must return entries"
            raise AssertionError(msg)
        return self._entries


class _FakeDocumentVectorIndex:
    """Test-only fake that structurally satisfies ``DocumentVectorIndexPort``.

    Not a production vector index. Not exported from application or
    infrastructure.
    """

    def __init__(self, *, error: BaseException | None = None) -> None:
        self._error = error
        self.calls: list[tuple[DocumentVectorIndexEntry, ...]] = []

    async def index(self, entries: tuple[DocumentVectorIndexEntry, ...]) -> None:
        self.calls.append(entries)
        if self._error is not None:
            raise self._error


def _as_index_port(index: _FakeDocumentVectorIndex) -> DocumentVectorIndexPort:
    """Application-shaped call site: the port type is the only accepted argument."""

    return index


def _execution_service(
    preparation: _RecordingPreparationService,
    index: _FakeDocumentVectorIndex,
) -> DocumentVectorIndexExecutionService:
    return DocumentVectorIndexExecutionService(
        cast(DocumentVectorIndexEntryPreparationService, preparation),
        _as_index_port(index),
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


def _entry(
    *,
    chunk: ExtractedDocumentChunk | None = None,
    embedding: DocumentChunkEmbedding | None = None,
) -> DocumentVectorIndexEntry:
    resolved_chunk = chunk or _chunk()
    resolved_embedding = embedding or _embedding(
        document_id=resolved_chunk.document_id,
        chunk_id=resolved_chunk.chunk_id,
    )
    return DocumentVectorIndexEntry(chunk=resolved_chunk, embedding=resolved_embedding)


def test_fake_index_does_not_inherit_the_port() -> None:
    assert DocumentVectorIndexPort not in _FakeDocumentVectorIndex.__mro__


def test_constructor_accepts_exactly_the_two_published_dependencies() -> None:
    signature = inspect.signature(DocumentVectorIndexExecutionService.__init__)
    assert tuple(signature.parameters) == (
        "self",
        "preparation_service",
        "document_vector_index_port",
    )
    assert (
        signature.parameters["preparation_service"].annotation
        is DocumentVectorIndexEntryPreparationService
    )
    assert signature.parameters["document_vector_index_port"].annotation is DocumentVectorIndexPort
    service = _execution_service(
        _RecordingPreparationService(entries=()),
        _FakeDocumentVectorIndex(),
    )
    assert isinstance(service, DocumentVectorIndexExecutionService)
    assert DocumentVectorIndexPort not in type(_FakeDocumentVectorIndex()).__mro__


def test_execute_signature_is_keyword_only_chunks_returning_none() -> None:
    signature = inspect.signature(DocumentVectorIndexExecutionService.execute)
    assert tuple(signature.parameters) == ("self", "chunks")
    assert signature.parameters["chunks"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["chunks"].annotation == tuple[ExtractedDocumentChunk, ...]
    assert signature.return_annotation is None
    assert inspect.iscoroutinefunction(DocumentVectorIndexExecutionService.execute)


async def test_happy_path_forwards_exact_chunks_and_entries_once() -> None:
    chunk = _chunk()
    chunks = (chunk,)
    entries = (_entry(chunk=chunk),)
    preparation = _RecordingPreparationService(entries=entries)
    index = _FakeDocumentVectorIndex()
    service = _execution_service(preparation, index)

    result = await service.execute(chunks=chunks)

    assert result is None
    assert preparation.calls == [chunks]
    assert preparation.calls[0] is chunks
    assert len(preparation.calls) == 1
    assert index.calls == [entries]
    assert index.calls[0] is entries
    assert len(index.calls) == 1
    assert preparation.embed_calls == 0


async def test_prepared_entry_order_is_forwarded_unchanged() -> None:
    first = _chunk(chunk_id="chunk-a", ordinal=0, text="First normalized chunk.")
    second = _chunk(chunk_id="chunk-b", ordinal=1, text="Second normalized chunk.")
    third = _chunk(
        document_id="doc-2",
        chunk_id="chunk-a",
        ordinal=0,
        text="Same chunk_id under a different document.",
    )
    chunks = (first, second, third)
    entries = (
        _entry(chunk=first),
        _entry(chunk=second),
        _entry(chunk=third),
    )
    preparation = _RecordingPreparationService(entries=entries)
    index = _FakeDocumentVectorIndex()
    service = _execution_service(preparation, index)

    result = await service.execute(chunks=chunks)

    assert result is None
    assert preparation.calls == [chunks]
    assert preparation.calls[0] is chunks
    assert index.calls == [entries]
    assert index.calls[0] is entries
    assert [entry.chunk.chunk_id for entry in index.calls[0]] == [
        "chunk-a",
        "chunk-b",
        "chunk-a",
    ]
    assert [entry.chunk.document_id for entry in index.calls[0]] == [
        "doc-1",
        "doc-1",
        "doc-2",
    ]


async def test_empty_input_prepares_and_indexes_empty_tuple_once() -> None:
    chunks: tuple[ExtractedDocumentChunk, ...] = ()
    entries: tuple[DocumentVectorIndexEntry, ...] = ()
    preparation = _RecordingPreparationService(entries=entries)
    index = _FakeDocumentVectorIndex()
    service = _execution_service(preparation, index)

    result = await service.execute(chunks=chunks)

    assert result is None
    assert preparation.calls == [chunks]
    assert preparation.calls[0] is chunks
    assert index.calls == [entries]
    assert index.calls[0] is entries
    assert len(preparation.calls) == 1
    assert len(index.calls) == 1


async def test_preparation_failure_propagates_without_calling_index() -> None:
    error = DependencyUnavailableError(_PREPARE_UNAVAILABLE_MESSAGE)
    chunks = (_chunk(),)
    preparation = _RecordingPreparationService(error=error)
    index = _FakeDocumentVectorIndex()
    service = _execution_service(preparation, index)

    with pytest.raises(DependencyUnavailableError) as caught:
        await service.execute(chunks=chunks)

    assert caught.value is error
    assert caught.value.message == _PREPARE_UNAVAILABLE_MESSAGE
    assert preparation.calls == [chunks]
    assert index.calls == []


async def test_index_failure_propagates_after_exactly_one_prepare() -> None:
    error = DependencyUnavailableError(_INDEX_UNAVAILABLE_MESSAGE)
    chunks = (_chunk(),)
    entries = (_entry(),)
    preparation = _RecordingPreparationService(entries=entries)
    index = _FakeDocumentVectorIndex(error=error)
    service = _execution_service(preparation, index)

    with pytest.raises(DependencyUnavailableError) as caught:
        await service.execute(chunks=chunks)

    assert caught.value is error
    assert caught.value.message == _INDEX_UNAVAILABLE_MESSAGE
    assert preparation.calls == [chunks]
    assert index.calls == [entries]
    assert len(index.calls) == 1


async def test_index_conflict_propagates_without_retry() -> None:
    error = ConflictError(_INDEX_CONFLICT_MESSAGE)
    chunks = (_chunk(),)
    entries = (_entry(),)
    preparation = _RecordingPreparationService(entries=entries)
    index = _FakeDocumentVectorIndex(error=error)
    service = _execution_service(preparation, index)

    with pytest.raises(ConflictError) as caught:
        await service.execute(chunks=chunks)

    assert caught.value is error
    assert caught.value.message == _INDEX_CONFLICT_MESSAGE
    assert len(preparation.calls) == 1
    assert len(index.calls) == 1
