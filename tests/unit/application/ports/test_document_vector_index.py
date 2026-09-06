"""Application-owned document vector indexing port contract."""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError

import pytest

from energy_trading.application.errors import (
    ConflictError,
    DependencyUnavailableError,
    InvalidRequestError,
)
from energy_trading.application.ports import (
    DocumentChunkEmbedding,
    DocumentVectorIndexEntry,
    DocumentVectorIndexPort,
    ExtractedDocumentChunk,
)


class _FakeDocumentVectorIndex:
    """Test-only fake that structurally satisfies ``DocumentVectorIndexPort``.

    Not a production vector index. Not exported from application or
    infrastructure.
    """

    def __init__(self, *, unavailable: bool = False) -> None:
        self._unavailable = unavailable
        self._stored: dict[tuple[str, str], DocumentVectorIndexEntry] = {}
        self.backend_calls = 0

    async def index(self, entries: tuple[DocumentVectorIndexEntry, ...]) -> None:
        if not entries:
            return
        self.backend_calls += 1
        if self._unavailable:
            raise DependencyUnavailableError("Document vector index is unavailable.")
        if not all(isinstance(item, DocumentVectorIndexEntry) for item in entries):
            raise InvalidRequestError("Index entries must be document vector index entries.")
        dimensions = {len(item.embedding.vector) for item in entries}
        if len(dimensions) != 1:
            raise InvalidRequestError("Index entries must share a single vector dimension.")
        coalesced: dict[tuple[str, str], DocumentVectorIndexEntry] = {}
        for entry in entries:
            identity = (entry.chunk.document_id, entry.chunk.chunk_id)
            existing = coalesced.get(identity)
            if existing is not None and existing != entry:
                raise ConflictError("A conflicting document chunk is already indexed.")
            coalesced[identity] = entry
        for identity, entry in coalesced.items():
            stored = self._stored.get(identity)
            if stored is not None and stored != entry:
                raise ConflictError("A conflicting document chunk is already indexed.")
        self._stored.update(coalesced)

    @property
    def entries(self) -> tuple[DocumentVectorIndexEntry, ...]:
        return tuple(self._stored.values())


def _as_index_port(index: _FakeDocumentVectorIndex) -> DocumentVectorIndexPort:
    """Application-shaped call site: the port type is the only accepted argument."""

    return index


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


def _entry(
    *,
    chunk: ExtractedDocumentChunk | None = None,
    embedding: DocumentChunkEmbedding | None = None,
    **overrides: object,
) -> DocumentVectorIndexEntry:
    resolved_chunk = chunk or _chunk()
    resolved_embedding = embedding or _embedding(
        document_id=resolved_chunk.document_id,
        chunk_id=resolved_chunk.chunk_id,
    )
    values: dict[str, object] = {"chunk": resolved_chunk, "embedding": resolved_embedding}
    values.update(overrides)
    return DocumentVectorIndexEntry(**values)  # type: ignore[arg-type]


def test_entry_is_valid_matching_pair() -> None:
    chunk = _chunk()
    embedding = _embedding()
    entry = DocumentVectorIndexEntry(chunk=chunk, embedding=embedding)
    assert entry.chunk is chunk
    assert entry.embedding is embedding
    assert entry.chunk.document_id == "doc-1"
    assert entry.chunk.chunk_id == "chunk-1"
    assert entry.embedding.vector == (1.0, 0.0, -0.25)


def test_entry_is_immutable() -> None:
    entry = _entry()
    with pytest.raises(FrozenInstanceError):
        entry.chunk = _chunk(text="mutated")  # type: ignore[misc]


def test_entry_rejects_mismatched_document_id() -> None:
    with pytest.raises(ValueError, match="document_id"):
        DocumentVectorIndexEntry(
            chunk=_chunk(document_id="doc-1"),
            embedding=_embedding(document_id="doc-other"),
        )


def test_entry_rejects_mismatched_chunk_id() -> None:
    with pytest.raises(ValueError, match="chunk_id"):
        DocumentVectorIndexEntry(
            chunk=_chunk(chunk_id="chunk-1"),
            embedding=_embedding(chunk_id="chunk-other"),
        )


def test_entry_accepts_same_chunk_id_under_matching_document() -> None:
    entry = DocumentVectorIndexEntry(
        chunk=_chunk(document_id="doc-1", chunk_id="chunk-shared"),
        embedding=_embedding(document_id="doc-1", chunk_id="chunk-shared"),
    )
    assert entry.chunk.document_id == "doc-1"
    assert entry.chunk.chunk_id == "chunk-shared"
    assert entry.embedding.document_id == "doc-1"
    assert entry.embedding.chunk_id == "chunk-shared"


def test_entry_requires_extracted_document_chunk_type() -> None:
    with pytest.raises(TypeError, match="ExtractedDocumentChunk"):
        DocumentVectorIndexEntry(chunk={"text": "not a chunk"}, embedding=_embedding())  # type: ignore[arg-type]


def test_entry_requires_document_chunk_embedding_type() -> None:
    with pytest.raises(TypeError, match="DocumentChunkEmbedding"):
        DocumentVectorIndexEntry(chunk=_chunk(), embedding=(1.0, 0.0))  # type: ignore[arg-type]


def test_entry_does_not_rewrite_nested_dtos() -> None:
    chunk = _chunk(document_id="doc-keep", chunk_id="chunk-keep", text="Original text.")
    embedding = _embedding(
        document_id="doc-keep",
        chunk_id="chunk-keep",
        vector=(0.5, -1.0),
    )
    entry = DocumentVectorIndexEntry(chunk=chunk, embedding=embedding)
    assert entry.chunk is chunk
    assert entry.embedding is embedding
    assert entry.chunk.text == "Original text."
    assert entry.embedding.vector == (0.5, -1.0)


def test_fake_structurally_satisfies_index_port() -> None:
    port: DocumentVectorIndexPort = _as_index_port(_FakeDocumentVectorIndex())
    assert inspect.iscoroutinefunction(port.index)
    assert list(inspect.signature(_FakeDocumentVectorIndex.index).parameters) == ["self", "entries"]


async def test_empty_input_is_successful_noop_without_backend_io() -> None:
    fake = _FakeDocumentVectorIndex()
    port = _as_index_port(fake)
    await port.index(())
    assert fake.entries == ()
    assert fake.backend_calls == 0


async def test_indexes_one_entry() -> None:
    fake = _FakeDocumentVectorIndex()
    port = _as_index_port(fake)
    entry = _entry()
    await port.index((entry,))
    assert fake.entries == (entry,)


async def test_indexes_multiple_entries() -> None:
    first = _entry(chunk=_chunk(chunk_id="chunk-1", ordinal=0, text="First."))
    second = _entry(chunk=_chunk(chunk_id="chunk-2", ordinal=1, text="Second."))
    fake = _FakeDocumentVectorIndex()
    port = _as_index_port(fake)
    await port.index((first, second))
    assert fake.entries == (first, second)


async def test_exact_retry_is_idempotent() -> None:
    entry = _entry()
    fake = _FakeDocumentVectorIndex()
    port = _as_index_port(fake)
    await port.index((entry,))
    await port.index((entry,))
    assert fake.entries == (entry,)


async def test_same_chunk_id_under_different_documents_is_distinct() -> None:
    first = _entry(
        chunk=_chunk(document_id="doc-a", chunk_id="chunk-shared", text="Alpha."),
    )
    second = _entry(
        chunk=_chunk(document_id="doc-b", chunk_id="chunk-shared", text="Beta."),
    )
    fake = _FakeDocumentVectorIndex()
    port = _as_index_port(fake)
    await port.index((first, second))
    assert fake.entries == (first, second)


async def test_in_call_exact_duplicates_are_coalesced() -> None:
    entry = _entry()
    duplicate = _entry()
    fake = _FakeDocumentVectorIndex()
    port = _as_index_port(fake)
    await port.index((entry, duplicate))
    assert fake.entries == (duplicate,)
    assert len(fake.entries) == 1


async def test_in_call_conflicting_identity_is_conflict_error() -> None:
    first = _entry(chunk=_chunk(text="Original clause."))
    conflict = _entry(chunk=_chunk(text="Changed clause."))
    fake = _FakeDocumentVectorIndex()
    port = _as_index_port(fake)
    with pytest.raises(ConflictError, match="conflicting document chunk") as caught:
        await port.index((first, conflict))
    assert fake.entries == ()
    assert first.chunk.text not in caught.value.message
    assert conflict.chunk.text not in caught.value.message


async def test_changed_chunk_content_for_stored_identity_is_conflict_error() -> None:
    original = _entry(chunk=_chunk(text="Stored clause."))
    changed = _entry(chunk=_chunk(text="Edited clause."))
    fake = _FakeDocumentVectorIndex()
    port = _as_index_port(fake)
    await port.index((original,))
    with pytest.raises(ConflictError, match="conflicting document chunk") as caught:
        await port.index((changed,))
    assert fake.entries == (original,)
    assert original.chunk.text not in caught.value.message
    assert changed.chunk.text not in caught.value.message


async def test_changed_vector_for_stored_identity_is_conflict_error() -> None:
    original = _entry(embedding=_embedding(vector=(1.0, 0.0, -0.25)))
    changed = _entry(embedding=_embedding(vector=(0.0, 1.0, 0.5)))
    fake = _FakeDocumentVectorIndex()
    port = _as_index_port(fake)
    await port.index((original,))
    with pytest.raises(ConflictError, match="conflicting document chunk") as caught:
        await port.index((changed,))
    assert fake.entries == (original,)
    assert str(original.embedding.vector) not in caught.value.message
    assert str(changed.embedding.vector) not in caught.value.message


async def test_inconsistent_batch_dimensions_are_invalid_request_error() -> None:
    first = _entry(
        chunk=_chunk(chunk_id="chunk-1", ordinal=0, text="First."),
        embedding=_embedding(chunk_id="chunk-1", vector=(1.0, 0.0, -0.25)),
    )
    second = _entry(
        chunk=_chunk(chunk_id="chunk-2", ordinal=1, text="Second."),
        embedding=_embedding(chunk_id="chunk-2", vector=(1.0, 0.0)),
    )
    fake = _FakeDocumentVectorIndex()
    port = _as_index_port(fake)
    with pytest.raises(InvalidRequestError, match="single vector dimension") as caught:
        await port.index((first, second))
    assert fake.entries == ()
    assert first.chunk.text not in caught.value.message
    assert str(first.embedding.vector) not in caught.value.message
    assert str(second.embedding.vector) not in caught.value.message


async def test_fake_can_represent_sanitized_dependency_unavailable_error() -> None:
    entry = _entry(chunk=_chunk(text="Confidential regulatory clause."))
    fake = _FakeDocumentVectorIndex(unavailable=True)
    port = _as_index_port(fake)
    with pytest.raises(
        DependencyUnavailableError, match="Document vector index is unavailable"
    ) as caught:
        await port.index((entry,))
    message = caught.value.message
    assert entry.chunk.text not in message
    assert str(entry.embedding.vector) not in message
    assert "Confidential" not in message
    assert "traceback" not in message.lower()
    assert "http://" not in message
    assert "api_key" not in message.lower()
