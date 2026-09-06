"""Application-owned document embedding port contract."""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError
from math import inf, nan

import pytest

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.ports import (
    DocumentChunkEmbedding,
    DocumentEmbeddingPort,
    ExtractedDocumentChunk,
)


class _FakeDocumentEmbedder:
    """Test-only fake that structurally satisfies ``DocumentEmbeddingPort``.

    Not a production embedding implementation. Not exported from application
    or infrastructure.
    """

    _VECTOR: tuple[float, ...] = (1.0, 0.0, -0.25)

    def __init__(self, *, unavailable: bool = False) -> None:
        self._unavailable = unavailable

    async def embed(
        self,
        chunks: tuple[ExtractedDocumentChunk, ...],
    ) -> tuple[DocumentChunkEmbedding, ...]:
        if self._unavailable:
            raise DependencyUnavailableError("Document embedding is unavailable.")
        return tuple(
            DocumentChunkEmbedding(
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_id,
                vector=self._VECTOR,
            )
            for chunk in chunks
        )


def _as_embedding_port(embedder: _FakeDocumentEmbedder) -> DocumentEmbeddingPort:
    """Application-shaped call site: the port type is the only accepted argument."""

    return embedder


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
        "vector": (1.0, 0.0, -0.25),
    }
    values.update(overrides)
    return DocumentChunkEmbedding(**values)  # type: ignore[arg-type]


def test_embedding_is_valid() -> None:
    embedding = _embedding()
    assert embedding.document_id == "doc-1"
    assert embedding.chunk_id == "chunk-1"
    assert embedding.vector == (1.0, 0.0, -0.25)
    assert isinstance(embedding.vector, tuple)


def test_embedding_is_immutable() -> None:
    embedding = _embedding()
    with pytest.raises(FrozenInstanceError):
        embedding.document_id = "mutated"  # type: ignore[misc]


def test_embedding_strips_document_id() -> None:
    embedding = _embedding(document_id="  doc-1  ")
    assert embedding.document_id == "doc-1"


def test_embedding_strips_chunk_id() -> None:
    embedding = _embedding(chunk_id="  chunk-1  ")
    assert embedding.chunk_id == "chunk-1"


@pytest.mark.parametrize("document_id", ["", "   "])
def test_embedding_rejects_empty_document_id(document_id: str) -> None:
    with pytest.raises(ValueError, match="document_id"):
        _embedding(document_id=document_id)


@pytest.mark.parametrize("chunk_id", ["", "   "])
def test_embedding_rejects_empty_chunk_id(chunk_id: str) -> None:
    with pytest.raises(ValueError, match="chunk_id"):
        _embedding(chunk_id=chunk_id)


def test_embedding_vector_must_be_a_tuple() -> None:
    with pytest.raises(TypeError, match="vector must be a tuple"):
        _embedding(vector=[1.0, 0.0])  # type: ignore[arg-type]


def test_embedding_rejects_empty_vector() -> None:
    with pytest.raises(ValueError, match="vector must contain at least one element"):
        _embedding(vector=())


def test_embedding_accepts_finite_positive_negative_and_zero_floats() -> None:
    embedding = _embedding(vector=(1.5, 0.0, -2.25))
    assert embedding.vector == (1.5, 0.0, -2.25)


def test_embedding_rejects_nan() -> None:
    with pytest.raises(ValueError, match="vector elements must be finite"):
        _embedding(vector=(1.0, nan))


def test_embedding_rejects_positive_infinity() -> None:
    with pytest.raises(ValueError, match="vector elements must be finite"):
        _embedding(vector=(1.0, inf))


def test_embedding_rejects_negative_infinity() -> None:
    with pytest.raises(ValueError, match="vector elements must be finite"):
        _embedding(vector=(1.0, -inf))


def test_fake_structurally_satisfies_embedding_port() -> None:
    port: DocumentEmbeddingPort = _as_embedding_port(_FakeDocumentEmbedder())
    assert inspect.iscoroutinefunction(port.embed)
    assert list(inspect.signature(_FakeDocumentEmbedder.embed).parameters) == ["self", "chunks"]


async def test_fake_maps_batch_one_to_one() -> None:
    chunks = (
        _chunk(chunk_id="chunk-1", ordinal=0, text="First chunk."),
        _chunk(chunk_id="chunk-2", ordinal=1, text="Second chunk."),
    )
    port = _as_embedding_port(_FakeDocumentEmbedder())
    embeddings = await port.embed(chunks)
    assert len(embeddings) == len(chunks)
    assert all(isinstance(item, DocumentChunkEmbedding) for item in embeddings)


async def test_fake_preserves_document_and_chunk_identities() -> None:
    chunks = (
        _chunk(document_id="doc-a", chunk_id="chunk-a", ordinal=0, text="Alpha."),
        _chunk(document_id="doc-b", chunk_id="chunk-b", ordinal=1, text="Beta."),
    )
    port = _as_embedding_port(_FakeDocumentEmbedder())
    embeddings = await port.embed(chunks)
    assert embeddings[0].document_id == "doc-a"
    assert embeddings[0].chunk_id == "chunk-a"
    assert embeddings[1].document_id == "doc-b"
    assert embeddings[1].chunk_id == "chunk-b"


async def test_fake_preserves_input_order() -> None:
    chunks = (
        _chunk(chunk_id="chunk-z", ordinal=0, text="Last label first."),
        _chunk(chunk_id="chunk-a", ordinal=1, text="First label second."),
        _chunk(chunk_id="chunk-m", ordinal=2, text="Middle."),
    )
    port = _as_embedding_port(_FakeDocumentEmbedder())
    embeddings = await port.embed(chunks)
    assert [item.chunk_id for item in embeddings] == ["chunk-z", "chunk-a", "chunk-m"]


async def test_fake_empty_input_returns_empty_tuple() -> None:
    port = _as_embedding_port(_FakeDocumentEmbedder())
    embeddings = await port.embed(())
    assert embeddings == ()


async def test_fake_batch_vectors_have_equal_dimension() -> None:
    chunks = (
        _chunk(chunk_id="chunk-1", ordinal=0, text="First."),
        _chunk(chunk_id="chunk-2", ordinal=1, text="Second."),
        _chunk(chunk_id="chunk-3", ordinal=2, text="Third."),
    )
    port = _as_embedding_port(_FakeDocumentEmbedder())
    embeddings = await port.embed(chunks)
    dimensions = {len(item.vector) for item in embeddings}
    assert len(dimensions) == 1
    assert next(iter(dimensions)) > 0


async def test_fake_can_represent_sanitized_dependency_unavailable_error() -> None:
    chunk = _chunk(text="Confidential regulatory clause.")
    port = _as_embedding_port(_FakeDocumentEmbedder(unavailable=True))
    with pytest.raises(
        DependencyUnavailableError, match="Document embedding is unavailable"
    ) as caught:
        await port.embed((chunk,))
    message = caught.value.message
    assert chunk.text not in message
    assert "Confidential" not in message
    assert "traceback" not in message.lower()
    assert "http://" not in message
    assert "api_key" not in message.lower()
