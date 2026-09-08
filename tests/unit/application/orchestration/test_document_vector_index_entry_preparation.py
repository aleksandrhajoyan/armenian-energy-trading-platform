"""Document vector index-entry preparation composes embedding into index entries."""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError

import pytest

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.orchestration import DocumentVectorIndexEntryPreparationService
from energy_trading.application.ports.document_embedding import (
    DocumentChunkEmbedding,
    DocumentEmbeddingPort,
)
from energy_trading.application.ports.document_extraction import ExtractedDocumentChunk
from energy_trading.application.ports.document_vector_index import DocumentVectorIndexEntry

_SENTINEL_VECTOR: tuple[float, ...] = (1.0, 0.0, -0.25)
_UNAVAILABLE_MESSAGE = "Document vector index entries could not be prepared."
_EMBEDDING_UNAVAILABLE_MESSAGE = "Document embedding is unavailable."
_SENTINEL_TEXT = "Confidential regulatory chunk text that must not leak."


class _FakeDocumentEmbedder:
    """Test-only fake that structurally satisfies ``DocumentEmbeddingPort``.

    Not a production embedding implementation. Not exported from application
    or infrastructure.
    """

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


def _as_embedding_port(embedder: _FakeDocumentEmbedder) -> DocumentEmbeddingPort:
    """Application-shaped call site: the port type is the only accepted argument."""

    return embedder


def _service(
    embedder: _FakeDocumentEmbedder | None = None,
) -> tuple[DocumentVectorIndexEntryPreparationService, _FakeDocumentEmbedder]:
    fake = _FakeDocumentEmbedder() if embedder is None else embedder
    return DocumentVectorIndexEntryPreparationService(_as_embedding_port(fake)), fake


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


def test_fake_does_not_inherit_the_port() -> None:
    assert DocumentEmbeddingPort not in _FakeDocumentEmbedder.__mro__


def test_constructor_accepts_a_structural_document_embedding_port() -> None:
    signature = inspect.signature(DocumentVectorIndexEntryPreparationService.__init__)
    assert tuple(signature.parameters) == ("self", "document_embedding_port")
    assert signature.parameters["document_embedding_port"].annotation is DocumentEmbeddingPort
    service, fake = _service()
    assert isinstance(service, DocumentVectorIndexEntryPreparationService)
    assert DocumentEmbeddingPort not in type(fake).__mro__


def test_prepare_signature_is_keyword_only_chunks() -> None:
    signature = inspect.signature(DocumentVectorIndexEntryPreparationService.prepare)
    assert tuple(signature.parameters) == ("self", "chunks")
    assert signature.parameters["chunks"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["chunks"].annotation == tuple[ExtractedDocumentChunk, ...]
    assert signature.return_annotation == tuple[DocumentVectorIndexEntry, ...]
    assert inspect.iscoroutinefunction(DocumentVectorIndexEntryPreparationService.prepare)


async def test_one_chunk_forwards_exact_tuple_and_returns_one_entry() -> None:
    chunk = _chunk()
    chunks = (chunk,)
    embedding = _embedding()
    service, fake = _service(_FakeDocumentEmbedder(embeddings=(embedding,)))

    result = await service.prepare(chunks=chunks)

    assert fake.calls == [chunks]
    assert fake.calls[0] is chunks
    assert len(result) == 1
    assert isinstance(result[0], DocumentVectorIndexEntry)
    assert result[0].chunk is chunk
    assert result[0].embedding is embedding
    assert result[0].chunk.document_id == "doc-1"
    assert result[0].chunk.chunk_id == "chunk-1"
    assert result[0].embedding.document_id == "doc-1"
    assert result[0].embedding.chunk_id == "chunk-1"
    assert result[0].embedding.vector == _SENTINEL_VECTOR


async def test_embedding_port_is_awaited_exactly_once_for_one_chunk() -> None:
    service, fake = _service()

    await service.prepare(chunks=(_chunk(),))

    assert len(fake.calls) == 1


async def test_multiple_chunks_preserve_order_and_pair_corresponding_embeddings() -> None:
    first = _chunk(chunk_id="chunk-a", ordinal=0, text="First normalized chunk.")
    second = _chunk(
        document_id="doc-1",
        chunk_id="chunk-b",
        ordinal=1,
        text="Second normalized chunk.",
    )
    third = _chunk(
        document_id="doc-2",
        chunk_id="chunk-a",
        ordinal=0,
        text="Same chunk_id under a different document.",
    )
    chunks = (first, second, third)
    first_embedding = _embedding(chunk_id="chunk-a", vector=(0.1, 0.2))
    second_embedding = _embedding(chunk_id="chunk-b", vector=(0.3, 0.4))
    third_embedding = _embedding(
        document_id="doc-2",
        chunk_id="chunk-a",
        vector=(0.5, 0.6),
    )
    embeddings = (first_embedding, second_embedding, third_embedding)
    service, fake = _service(_FakeDocumentEmbedder(embeddings=embeddings))

    result = await service.prepare(chunks=chunks)

    assert fake.calls == [chunks]
    assert fake.calls[0] is chunks
    assert len(fake.calls) == 1
    assert tuple(entry.chunk for entry in result) == chunks
    assert tuple(entry.embedding for entry in result) == embeddings
    assert [entry.chunk.chunk_id for entry in result] == ["chunk-a", "chunk-b", "chunk-a"]
    assert [entry.chunk.document_id for entry in result] == ["doc-1", "doc-1", "doc-2"]
    assert result[0].chunk is first
    assert result[1].chunk is second
    assert result[2].chunk is third
    assert result[0].embedding is first_embedding
    assert result[1].embedding is second_embedding
    assert result[2].embedding is third_embedding


async def test_empty_input_returns_empty_tuple_after_one_embed_call() -> None:
    chunks: tuple[ExtractedDocumentChunk, ...] = ()
    service, fake = _service()

    result = await service.prepare(chunks=chunks)

    assert result == ()
    assert fake.calls == [chunks]
    assert fake.calls[0] is chunks
    assert len(fake.calls) == 1


async def test_fewer_embeddings_fail_closed_without_partial_entries() -> None:
    chunks = (_chunk(chunk_id="chunk-1"), _chunk(chunk_id="chunk-2"))
    service, fake = _service(_FakeDocumentEmbedder(embeddings=(_embedding(chunk_id="chunk-1"),)))

    with pytest.raises(DependencyUnavailableError) as caught:
        await service.prepare(chunks=chunks)

    assert caught.value.message == _UNAVAILABLE_MESSAGE
    assert fake.calls == [chunks]


async def test_extra_embeddings_fail_closed_without_truncation() -> None:
    chunk = _chunk()
    chunks = (chunk,)
    embeddings = (
        _embedding(),
        _embedding(chunk_id="chunk-extra", document_id="doc-extra"),
    )
    service, fake = _service(_FakeDocumentEmbedder(embeddings=embeddings))

    with pytest.raises(DependencyUnavailableError) as caught:
        await service.prepare(chunks=chunks)

    assert caught.value.message == _UNAVAILABLE_MESSAGE
    assert fake.calls == [chunks]
    assert "doc-extra" not in caught.value.message
    assert "chunk-extra" not in caught.value.message


async def test_mismatched_document_id_fails_closed_without_leaking_text() -> None:
    chunk = _chunk(document_id="doc-secret-id", text=_SENTINEL_TEXT)
    embedding = _embedding(document_id="doc-other", chunk_id="chunk-1", vector=(9.0, 8.0))
    service, fake = _service(_FakeDocumentEmbedder(embeddings=(embedding,)))

    with pytest.raises(DependencyUnavailableError) as caught:
        await service.prepare(chunks=(chunk,))

    assert caught.value.message == _UNAVAILABLE_MESSAGE
    assert _SENTINEL_TEXT not in caught.value.message
    assert "doc-secret-id" not in caught.value.message
    assert "doc-other" not in caught.value.message
    assert "(9.0, 8.0)" not in caught.value.message
    assert "9.0" not in caught.value.message
    assert fake.calls == [(chunk,)]


async def test_mismatched_chunk_id_fails_closed_without_leaking_text() -> None:
    chunk = _chunk(chunk_id="chunk-secret-id", text=_SENTINEL_TEXT)
    embedding = _embedding(chunk_id="chunk-other", vector=(7.5, -1.25))
    service, fake = _service(_FakeDocumentEmbedder(embeddings=(embedding,)))

    with pytest.raises(DependencyUnavailableError) as caught:
        await service.prepare(chunks=(chunk,))

    assert caught.value.message == _UNAVAILABLE_MESSAGE
    assert _SENTINEL_TEXT not in caught.value.message
    assert "chunk-secret-id" not in caught.value.message
    assert "chunk-other" not in caught.value.message
    assert "7.5" not in caught.value.message
    assert fake.calls == [(chunk,)]


async def test_embedding_dependency_failure_propagates_without_entries() -> None:
    error = DependencyUnavailableError(_EMBEDDING_UNAVAILABLE_MESSAGE)
    chunk = _chunk(text=_SENTINEL_TEXT)
    fake = _FakeDocumentEmbedder(error=error)
    service, _ = _service(fake)

    with pytest.raises(DependencyUnavailableError) as caught:
        await service.prepare(chunks=(chunk,))

    assert caught.value is error
    assert caught.value.message == _EMBEDDING_UNAVAILABLE_MESSAGE
    assert _SENTINEL_TEXT not in caught.value.message
    assert fake.calls == [(chunk,)]


async def test_equivalent_inputs_produce_value_equivalent_entries() -> None:
    chunks = (_chunk(), _chunk(chunk_id="chunk-2", ordinal=1, text="Second chunk."))
    first_service, _ = _service()
    second_service, _ = _service()

    first = await first_service.prepare(chunks=chunks)
    second = await second_service.prepare(chunks=chunks)

    assert first == second
    assert first is not second
    assert first[0].chunk == chunks[0]
    assert first[1].chunk == chunks[1]


async def test_original_chunks_are_not_mutated() -> None:
    chunk = _chunk()
    chunks = (chunk,)
    service, _fake = _service()

    result = await service.prepare(chunks=chunks)

    assert result[0].chunk is chunk
    assert chunk.document_id == "doc-1"
    assert chunk.chunk_id == "chunk-1"
    assert chunk.text == "Normalized extracted text."
    with pytest.raises(FrozenInstanceError):
        chunk.text = "mutated"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result[0].embedding.vector = (0.0,)  # type: ignore[misc]
