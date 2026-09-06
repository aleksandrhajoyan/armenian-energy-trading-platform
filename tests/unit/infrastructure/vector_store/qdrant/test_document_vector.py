"""Offline unit tests for Qdrant document vector index/search adapters.

No live Qdrant process, local mode, or network call is used.
"""

from __future__ import annotations

import inspect
import re
import uuid
from dataclasses import FrozenInstanceError, dataclass, field
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from qdrant_client.common.client_exceptions import ResourceExhaustedResponse
from qdrant_client.http import models
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

from energy_trading.application.errors import (
    ConflictError,
    DependencyUnavailableError,
    InvalidRequestError,
)
from energy_trading.application.ports import (
    DocumentChunkEmbedding,
    DocumentVectorIndexEntry,
    DocumentVectorIndexPort,
    DocumentVectorSearchPort,
    DocumentVectorSearchQuery,
    ExtractedDocumentChunk,
)
from energy_trading.infrastructure.vector_store.qdrant.document_vector import (
    QdrantDocumentVectorConfig,
    QdrantDocumentVectorIndex,
    QdrantDocumentVectorSearch,
    _encode_payload,
    _entry_fingerprint,
    _parse_stored_point,
    _point_uuid,
)

SENTINEL_TEXT = "SENTINEL_DOCUMENT_TEXT_CHUNK23"
SENTINEL_EXCEPTION = "sentinel-qdrant-exception-chunk23"
SENTINEL_VECTOR = (0.123456789, -9.87654321, 0.111111)
COLLECTION = "document-chunks"
VECTOR_SIZE = 3
SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass
class _FakeRecord:
    id: uuid.UUID
    payload: dict[str, object]
    vector: list[float] | None = None
    score: float = 0.0


@dataclass
class _FakeQueryResponse:
    points: list[_FakeRecord]


@dataclass
class _FakeQdrantClient:
    """Test-only async client surface. Not a production Qdrant connection."""

    store: dict[str, _FakeRecord] = field(default_factory=dict)
    retrieve_calls: list[dict[str, Any]] = field(default_factory=list)
    upsert_calls: list[dict[str, Any]] = field(default_factory=list)
    query_calls: list[dict[str, Any]] = field(default_factory=list)
    close_calls: int = 0
    retrieve_error: BaseException | None = None
    upsert_error: BaseException | None = None
    query_error: BaseException | None = None
    persist_upsert: bool = True
    query_hits: list[_FakeRecord] = field(default_factory=list)
    inject_before_upsert: Any = None

    async def retrieve(
        self,
        collection_name: str,
        ids: list[uuid.UUID],
        with_payload: bool,
        with_vectors: bool,
    ) -> list[_FakeRecord]:
        if self.retrieve_error is not None:
            raise self.retrieve_error
        self.retrieve_calls.append(
            {
                "collection_name": collection_name,
                "ids": list(ids),
                "with_payload": with_payload,
                "with_vectors": with_vectors,
            }
        )
        found: list[_FakeRecord] = []
        for point_id in ids:
            stored = self.store.get(str(uuid.UUID(str(point_id))))
            if stored is not None:
                found.append(stored)
        return found

    async def upsert(
        self,
        collection_name: str,
        points: list[models.PointStruct],
        wait: bool,
        update_mode: models.UpdateMode,
    ) -> None:
        if self.inject_before_upsert is not None:
            self.inject_before_upsert(self)
        if self.upsert_error is not None:
            raise self.upsert_error
        self.upsert_calls.append(
            {
                "collection_name": collection_name,
                "points": list(points),
                "wait": wait,
                "update_mode": update_mode,
            }
        )
        if not self.persist_upsert:
            return
        for point in points:
            key = str(uuid.UUID(str(point.id)))
            if update_mode == models.UpdateMode.INSERT_ONLY and key in self.store:
                continue
            payload = dict(point.payload) if point.payload is not None else {}
            vector = list(point.vector) if point.vector is not None else None
            self.store[key] = _FakeRecord(id=uuid.UUID(key), payload=payload, vector=vector)

    async def query_points(
        self,
        collection_name: str,
        query: list[float],
        limit: int,
        with_vectors: bool,
        with_payload: object,
        **kwargs: object,
    ) -> _FakeQueryResponse:
        if self.query_error is not None:
            raise self.query_error
        self.query_calls.append(
            {
                "collection_name": collection_name,
                "query": list(query),
                "limit": limit,
                "with_vectors": with_vectors,
                "with_payload": with_payload,
                "kwargs": dict(kwargs),
            }
        )
        return _FakeQueryResponse(points=list(self.query_hits))

    async def close(self) -> None:
        self.close_calls += 1


def _config(**overrides: object) -> QdrantDocumentVectorConfig:
    values: dict[str, object] = {"collection_name": COLLECTION, "vector_size": VECTOR_SIZE}
    values.update(overrides)
    return QdrantDocumentVectorConfig(**values)  # type: ignore[arg-type]


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
) -> DocumentVectorIndexEntry:
    resolved_chunk = chunk or _chunk()
    resolved_embedding = embedding or _embedding(
        document_id=resolved_chunk.document_id,
        chunk_id=resolved_chunk.chunk_id,
    )
    return DocumentVectorIndexEntry(chunk=resolved_chunk, embedding=resolved_embedding)


def _query(**overrides: object) -> DocumentVectorSearchQuery:
    values: dict[str, object] = {"vector": (1.0, 0.0, -0.25), "limit": 5}
    values.update(overrides)
    return DocumentVectorSearchQuery(**values)  # type: ignore[arg-type]


def _index(
    client: _FakeQdrantClient | None = None,
    config: QdrantDocumentVectorConfig | None = None,
) -> tuple[QdrantDocumentVectorIndex, _FakeQdrantClient]:
    fake = client or _FakeQdrantClient()
    adapter = QdrantDocumentVectorIndex(fake, config or _config())  # type: ignore[arg-type]
    return adapter, fake


def _search(
    client: _FakeQdrantClient | None = None,
    config: QdrantDocumentVectorConfig | None = None,
) -> tuple[QdrantDocumentVectorSearch, _FakeQdrantClient]:
    fake = client or _FakeQdrantClient()
    adapter = QdrantDocumentVectorSearch(fake, config or _config())  # type: ignore[arg-type]
    return adapter, fake


def _store_entry(fake: _FakeQdrantClient, entry: DocumentVectorIndexEntry) -> None:
    point_id = _point_uuid(entry.chunk.document_id, entry.chunk.chunk_id)
    fake.store[str(point_id)] = _FakeRecord(id=point_id, payload=_encode_payload(entry))


def _hit(entry: DocumentVectorIndexEntry, *, score: float = 9.9) -> _FakeRecord:
    point_id = _point_uuid(entry.chunk.document_id, entry.chunk.chunk_id)
    return _FakeRecord(id=point_id, payload=_encode_payload(entry), score=score)


def _backend_error() -> UnexpectedResponse:
    return UnexpectedResponse(
        status_code=503,
        reason_phrase="Service Unavailable",
        content=(
            f"collection={COLLECTION} api_key=secret {SENTINEL_EXCEPTION} {SENTINEL_TEXT}"
        ).encode(),
        headers=httpx.Headers({"x-api-key": "sentinel-qdrant-api-key-chunk23"}),
    )


def _as_index_port(adapter: QdrantDocumentVectorIndex) -> DocumentVectorIndexPort:
    return adapter


def _as_search_port(adapter: QdrantDocumentVectorSearch) -> DocumentVectorSearchPort:
    return adapter


def test_config_accepts_valid_collection_name_and_vector_size() -> None:
    config = QdrantDocumentVectorConfig(collection_name="docs", vector_size=8)
    assert config.collection_name == "docs"
    assert config.vector_size == 8


def test_config_strips_collection_name_whitespace() -> None:
    config = QdrantDocumentVectorConfig(collection_name="  docs  ", vector_size=4)
    assert config.collection_name == "docs"


def test_config_rejects_blank_collection_name() -> None:
    with pytest.raises(ValueError, match="collection_name"):
        QdrantDocumentVectorConfig(collection_name="   ", vector_size=4)
    with pytest.raises(ValueError, match="collection_name"):
        QdrantDocumentVectorConfig(collection_name="", vector_size=4)


def test_config_rejects_zero_or_negative_vector_size() -> None:
    with pytest.raises(ValueError, match="vector_size"):
        QdrantDocumentVectorConfig(collection_name="docs", vector_size=0)
    with pytest.raises(ValueError, match="vector_size"):
        QdrantDocumentVectorConfig(collection_name="docs", vector_size=-1)


def test_config_rejects_bool_vector_size() -> None:
    with pytest.raises(TypeError, match="vector_size"):
        QdrantDocumentVectorConfig(collection_name="docs", vector_size=True)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="vector_size"):
        QdrantDocumentVectorConfig(collection_name="docs", vector_size=False)  # type: ignore[arg-type]


def test_config_is_frozen() -> None:
    config = _config()
    with pytest.raises(FrozenInstanceError):
        config.collection_name = "other"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        config.vector_size = 99  # type: ignore[misc]


def test_point_id_is_deterministic_across_repeated_calls() -> None:
    first = _point_uuid("doc-1", "chunk-1")
    second = _point_uuid("doc-1", "chunk-1")
    assert first == second
    assert first is not second or first == second


def test_same_logical_identity_produces_same_uuid() -> None:
    assert _point_uuid("doc-1", "chunk-1") == _point_uuid("doc-1", "chunk-1")


def test_different_document_same_chunk_produces_different_uuid() -> None:
    assert _point_uuid("doc-a", "chunk-shared") != _point_uuid("doc-b", "chunk-shared")


def test_same_document_different_chunk_produces_different_uuid() -> None:
    assert _point_uuid("doc-1", "chunk-1") != _point_uuid("doc-1", "chunk-2")


def test_point_id_is_valid_uuid_and_not_raw_identifiers() -> None:
    document_id = "raw-document-id"
    chunk_id = "raw-chunk-id"
    point_id = _point_uuid(document_id, chunk_id)
    parsed = uuid.UUID(str(point_id))
    assert str(parsed) == str(point_id)
    assert str(point_id) != document_id
    assert str(point_id) != chunk_id
    assert document_id not in str(point_id)
    assert chunk_id not in str(point_id)


def test_point_id_encoding_is_not_delimiter_ambiguous() -> None:
    left = _point_uuid("a,b", "c")
    right = _point_uuid("a", "b,c")
    assert left != right


def test_fingerprint_is_deterministic_and_hex_sha256() -> None:
    entry = _entry()
    first = _entry_fingerprint(entry)
    second = _entry_fingerprint(_entry())
    assert first == second
    assert SHA256_HEX.fullmatch(first)


def test_identical_entry_has_same_fingerprint() -> None:
    assert _entry_fingerprint(_entry()) == _entry_fingerprint(_entry())


def test_changed_text_changes_fingerprint() -> None:
    original = _entry(chunk=_chunk(text="Original clause."))
    changed = _entry(chunk=_chunk(text="Edited clause."))
    assert _entry_fingerprint(original) != _entry_fingerprint(changed)


def test_changed_ordinal_changes_fingerprint() -> None:
    original = _entry(chunk=_chunk(ordinal=0))
    changed = _entry(chunk=_chunk(ordinal=1))
    assert _entry_fingerprint(original) != _entry_fingerprint(changed)


def test_changed_page_number_changes_fingerprint() -> None:
    original = _entry(chunk=_chunk(page_number=1))
    changed = _entry(chunk=_chunk(page_number=2))
    none_page = _entry(chunk=_chunk(page_number=None))
    assert _entry_fingerprint(original) != _entry_fingerprint(changed)
    assert _entry_fingerprint(original) != _entry_fingerprint(none_page)


def test_changed_vector_changes_fingerprint() -> None:
    original = _entry(embedding=_embedding(vector=(1.0, 0.0, -0.25)))
    changed = _entry(embedding=_embedding(vector=(0.0, 1.0, 0.5)))
    assert _entry_fingerprint(original) != _entry_fingerprint(changed)


def test_payload_has_exact_allowed_keys_and_no_vector_values() -> None:
    entry = _entry(embedding=_embedding(vector=SENTINEL_VECTOR))
    payload = _encode_payload(entry)
    assert set(payload) == {
        "document_id",
        "chunk_id",
        "ordinal",
        "text",
        "page_number",
        "content_sha256",
    }
    assert "vector" not in payload
    serialized = repr(payload)
    assert "0.123456789" not in serialized
    assert "-9.87654321" not in serialized
    for value in SENTINEL_VECTOR:
        assert value.hex() not in serialized
    assert SHA256_HEX.fullmatch(str(payload["content_sha256"]))


def test_payload_round_trip_reconstructs_extracted_chunk() -> None:
    entry = _entry(chunk=_chunk(text="Round-trip clause.", page_number=3, ordinal=2))
    payload = _encode_payload(entry)
    record = SimpleNamespace(
        id=_point_uuid(entry.chunk.document_id, entry.chunk.chunk_id), payload=payload
    )
    stored = _parse_stored_point(
        record, unavailable_message="Document vector index is unavailable."
    )
    assert stored.chunk == entry.chunk
    assert stored.fingerprint == _entry_fingerprint(entry)


def test_payload_round_trip_preserves_missing_page_number() -> None:
    entry = _entry(chunk=_chunk(page_number=None))
    payload = _encode_payload(entry)
    assert payload["page_number"] is None
    record = SimpleNamespace(
        id=_point_uuid(entry.chunk.document_id, entry.chunk.chunk_id), payload=payload
    )
    stored = _parse_stored_point(
        record, unavailable_message="Document vector index is unavailable."
    )
    assert stored.chunk.page_number is None


def test_payload_rejects_missing_and_malformed_fields() -> None:
    entry = _entry()
    point_id = _point_uuid(entry.chunk.document_id, entry.chunk.chunk_id)
    payload = _encode_payload(entry)
    missing = dict(payload)
    del missing["text"]
    with pytest.raises(DependencyUnavailableError):
        _parse_stored_point(SimpleNamespace(id=point_id, payload=missing), unavailable_message="x")
    with pytest.raises(DependencyUnavailableError):
        _parse_stored_point(SimpleNamespace(id=point_id, payload=None), unavailable_message="x")


def test_payload_rejects_wrong_field_types() -> None:
    entry = _entry()
    point_id = _point_uuid(entry.chunk.document_id, entry.chunk.chunk_id)
    payload = _encode_payload(entry)
    payload["ordinal"] = "0"
    with pytest.raises(DependencyUnavailableError):
        _parse_stored_point(SimpleNamespace(id=point_id, payload=payload), unavailable_message="x")


def test_payload_rejects_unexpected_extra_fields() -> None:
    entry = _entry()
    point_id = _point_uuid(entry.chunk.document_id, entry.chunk.chunk_id)
    payload = _encode_payload(entry)
    payload["source_path"] = "/tmp/secret.pdf"
    with pytest.raises(DependencyUnavailableError):
        _parse_stored_point(SimpleNamespace(id=point_id, payload=payload), unavailable_message="x")


def test_payload_point_id_mismatch_is_rejected() -> None:
    entry = _entry()
    payload = _encode_payload(entry)
    with pytest.raises(DependencyUnavailableError):
        _parse_stored_point(
            SimpleNamespace(id=uuid.uuid4(), payload=payload),
            unavailable_message="x",
        )


def test_index_structurally_satisfies_document_vector_index_port() -> None:
    adapter, _fake = _index()
    port: DocumentVectorIndexPort = _as_index_port(adapter)
    assert inspect.iscoroutinefunction(port.index)
    assert list(inspect.signature(QdrantDocumentVectorIndex.index).parameters) == [
        "self",
        "entries",
    ]


async def test_empty_index_input_makes_no_client_call() -> None:
    adapter, fake = _index()
    await _as_index_port(adapter).index(())
    assert fake.retrieve_calls == []
    assert fake.upsert_calls == []
    assert fake.close_calls == 0


async def test_indexes_correct_dimension_new_entry() -> None:
    adapter, fake = _index()
    entry = _entry()
    await _as_index_port(adapter).index((entry,))
    assert len(fake.upsert_calls) == 1
    point = fake.upsert_calls[0]["points"][0]
    assert point.id == _point_uuid(entry.chunk.document_id, entry.chunk.chunk_id)
    assert point.vector == list(entry.embedding.vector)
    assert point.payload == _encode_payload(entry)


async def test_indexes_multiple_new_entries() -> None:
    first = _entry(chunk=_chunk(chunk_id="chunk-1", ordinal=0, text="First."))
    second = _entry(chunk=_chunk(chunk_id="chunk-2", ordinal=1, text="Second."))
    adapter, fake = _index()
    await _as_index_port(adapter).index((first, second))
    ids = {str(point.id) for point in fake.upsert_calls[0]["points"]}
    assert ids == {
        str(_point_uuid(first.chunk.document_id, first.chunk.chunk_id)),
        str(_point_uuid(second.chunk.document_id, second.chunk.chunk_id)),
    }


async def test_wrong_configured_dimension_is_invalid_before_io() -> None:
    adapter, fake = _index(config=_config(vector_size=4))
    entry = _entry()
    with pytest.raises(InvalidRequestError, match="configured vector dimension") as caught:
        await _as_index_port(adapter).index((entry,))
    assert fake.retrieve_calls == []
    assert fake.upsert_calls == []
    assert str(entry.embedding.vector) not in caught.value.message
    assert "1.0" not in caught.value.message


async def test_mixed_dimensions_are_invalid_before_io() -> None:
    first = _entry(
        chunk=_chunk(chunk_id="chunk-1", ordinal=0, text="First."),
        embedding=_embedding(chunk_id="chunk-1", vector=(1.0, 0.0, -0.25)),
    )
    second = _entry(
        chunk=_chunk(chunk_id="chunk-2", ordinal=1, text="Second."),
        embedding=_embedding(chunk_id="chunk-2", vector=(1.0, 0.0)),
    )
    adapter, fake = _index()
    with pytest.raises(InvalidRequestError, match="configured vector dimension") as caught:
        await _as_index_port(adapter).index((first, second))
    assert fake.retrieve_calls == []
    assert fake.upsert_calls == []
    assert first.chunk.text not in caught.value.message
    assert str(first.embedding.vector) not in caught.value.message
    assert str(second.embedding.vector) not in caught.value.message


async def test_in_call_exact_duplicates_are_coalesced() -> None:
    entry = _entry()
    adapter, fake = _index()
    await _as_index_port(adapter).index((entry, _entry()))
    assert len(fake.upsert_calls[0]["points"]) == 1
    assert fake.upsert_calls[0]["points"][0].payload == _encode_payload(entry)


async def test_in_call_conflicting_identity_is_conflict_before_io() -> None:
    first = _entry(chunk=_chunk(text="Original clause."))
    conflict = _entry(chunk=_chunk(text="Changed clause."))
    adapter, fake = _index()
    with pytest.raises(ConflictError, match="conflicting document chunk") as caught:
        await _as_index_port(adapter).index((first, conflict))
    assert fake.retrieve_calls == []
    assert fake.upsert_calls == []
    assert first.chunk.text not in caught.value.message
    assert conflict.chunk.text not in caught.value.message


async def test_preexisting_exact_retry_succeeds_without_upsert() -> None:
    entry = _entry()
    fake = _FakeQdrantClient()
    _store_entry(fake, entry)
    adapter, fake = _index(client=fake)
    await _as_index_port(adapter).index((entry,))
    assert fake.upsert_calls == []
    assert len(fake.retrieve_calls) == 1
    assert fake.retrieve_calls[0]["with_payload"] is True
    assert fake.retrieve_calls[0]["with_vectors"] is False


async def test_preexisting_changed_text_is_conflict_without_upsert() -> None:
    original = _entry(chunk=_chunk(text="Stored clause."))
    changed = _entry(chunk=_chunk(text="Edited clause."))
    fake = _FakeQdrantClient()
    _store_entry(fake, original)
    adapter, fake = _index(client=fake)
    with pytest.raises(ConflictError, match="conflicting document chunk") as caught:
        await _as_index_port(adapter).index((changed,))
    assert fake.upsert_calls == []
    assert original.chunk.text not in caught.value.message
    assert changed.chunk.text not in caught.value.message


async def test_preexisting_changed_vector_fingerprint_is_conflict_without_upsert() -> None:
    original = _entry(embedding=_embedding(vector=(1.0, 0.0, -0.25)))
    changed = _entry(embedding=_embedding(vector=(0.0, 1.0, 0.5)))
    fake = _FakeQdrantClient()
    _store_entry(fake, original)
    adapter, fake = _index(client=fake)
    with pytest.raises(ConflictError, match="conflicting document chunk") as caught:
        await _as_index_port(adapter).index((changed,))
    assert fake.upsert_calls == []
    assert str(original.embedding.vector) not in caught.value.message
    assert str(changed.embedding.vector) not in caught.value.message


async def test_malformed_existing_payload_is_dependency_unavailable() -> None:
    entry = _entry(chunk=_chunk(text=SENTINEL_TEXT))
    fake = _FakeQdrantClient()
    point_id = _point_uuid(entry.chunk.document_id, entry.chunk.chunk_id)
    payload = _encode_payload(entry)
    payload["source_url"] = "https://example.invalid/secret.pdf"
    fake.store[str(point_id)] = _FakeRecord(id=point_id, payload=payload)
    adapter, fake = _index(client=fake)
    with pytest.raises(
        DependencyUnavailableError, match="Document vector index is unavailable"
    ) as caught:
        await _as_index_port(adapter).index((entry,))
    assert fake.upsert_calls == []
    assert SENTINEL_TEXT not in caught.value.message
    assert "source_url" not in caught.value.message


async def test_new_write_uses_insert_only_wait_and_closed_payload() -> None:
    entry = _entry(chunk=_chunk(text=SENTINEL_TEXT), embedding=_embedding(vector=SENTINEL_VECTOR))
    adapter, fake = _index()
    await _as_index_port(adapter).index((entry,))
    call = fake.upsert_calls[0]
    assert call["update_mode"] is models.UpdateMode.INSERT_ONLY
    assert call["wait"] is True
    assert call["update_mode"] is not models.UpdateMode.UPSERT
    point = call["points"][0]
    assert point.id == _point_uuid("doc-1", "chunk-1")
    assert set(point.payload) == {
        "document_id",
        "chunk_id",
        "ordinal",
        "text",
        "page_number",
        "content_sha256",
    }
    assert point.payload["text"] == SENTINEL_TEXT
    assert "vector" not in point.payload
    assert fake.retrieve_calls[0]["with_vectors"] is False
    assert fake.retrieve_calls[1]["with_vectors"] is False


async def test_post_write_verification_succeeds() -> None:
    entry = _entry()
    adapter, fake = _index()
    await _as_index_port(adapter).index((entry,))
    assert len(fake.retrieve_calls) == 2
    stored = fake.store[str(_point_uuid("doc-1", "chunk-1"))]
    assert stored.payload["content_sha256"] == _entry_fingerprint(entry)


async def test_post_write_missing_point_is_dependency_unavailable() -> None:
    entry = _entry(chunk=_chunk(text=SENTINEL_TEXT))
    fake = _FakeQdrantClient(persist_upsert=False)
    adapter, fake = _index(client=fake)
    with pytest.raises(
        DependencyUnavailableError, match="Document vector index is unavailable"
    ) as caught:
        await _as_index_port(adapter).index((entry,))
    assert fake.upsert_calls
    assert SENTINEL_TEXT not in caught.value.message


async def test_concurrent_different_content_winner_is_post_read_conflict() -> None:
    requested = _entry(chunk=_chunk(text="Writer A clause."))
    winner = _entry(chunk=_chunk(text="Writer B clause."))

    def inject(client: _FakeQdrantClient) -> None:
        _store_entry(client, winner)

    fake = _FakeQdrantClient(inject_before_upsert=inject)
    adapter, fake = _index(client=fake)
    with pytest.raises(ConflictError, match="conflicting document chunk") as caught:
        await _as_index_port(adapter).index((requested,))
    assert fake.upsert_calls[0]["update_mode"] is models.UpdateMode.INSERT_ONLY
    stored = fake.store[str(_point_uuid("doc-1", "chunk-1"))]
    assert stored.payload["text"] == "Writer B clause."
    assert requested.chunk.text not in caught.value.message
    assert winner.chunk.text not in caught.value.message


async def test_concurrent_exact_content_winner_succeeds() -> None:
    entry = _entry(chunk=_chunk(text="Shared clause."))

    def inject(client: _FakeQdrantClient) -> None:
        _store_entry(client, entry)

    fake = _FakeQdrantClient(inject_before_upsert=inject)
    adapter, fake = _index(client=fake)
    await _as_index_port(adapter).index((entry,))
    assert fake.upsert_calls[0]["update_mode"] is models.UpdateMode.INSERT_ONLY
    stored = fake.store[str(_point_uuid("doc-1", "chunk-1"))]
    assert stored.payload["content_sha256"] == _entry_fingerprint(entry)


async def test_backend_retrieve_failure_is_sanitized() -> None:
    entry = _entry(chunk=_chunk(text=SENTINEL_TEXT), embedding=_embedding(vector=SENTINEL_VECTOR))
    fake = _FakeQdrantClient(retrieve_error=_backend_error())
    adapter, fake = _index(client=fake)
    with pytest.raises(
        DependencyUnavailableError, match="Document vector index is unavailable"
    ) as caught:
        await _as_index_port(adapter).index((entry,))
    message = caught.value.message
    assert SENTINEL_EXCEPTION not in message
    assert SENTINEL_TEXT not in message
    assert "0.123456789" not in message
    assert COLLECTION not in message
    assert "api_key" not in message.lower()
    assert fake.upsert_calls == []


async def test_backend_upsert_failure_is_sanitized() -> None:
    entry = _entry(chunk=_chunk(text=SENTINEL_TEXT), embedding=_embedding(vector=SENTINEL_VECTOR))
    fake = _FakeQdrantClient(upsert_error=ResponseHandlingException(Exception(SENTINEL_EXCEPTION)))
    adapter, fake = _index(client=fake)
    with pytest.raises(
        DependencyUnavailableError, match="Document vector index is unavailable"
    ) as caught:
        await _as_index_port(adapter).index((entry,))
    assert SENTINEL_EXCEPTION not in caught.value.message
    assert SENTINEL_TEXT not in caught.value.message
    assert "0.123456789" not in caught.value.message


async def test_resource_exhausted_upsert_is_sanitized() -> None:
    entry = _entry(chunk=_chunk(text=SENTINEL_TEXT))
    fake = _FakeQdrantClient(
        upsert_error=ResourceExhaustedResponse(message=SENTINEL_EXCEPTION, retry_after_s=1)
    )
    adapter, fake = _index(client=fake)
    with pytest.raises(
        DependencyUnavailableError, match="Document vector index is unavailable"
    ) as caught:
        await _as_index_port(adapter).index((entry,))
    assert SENTINEL_EXCEPTION not in caught.value.message
    assert SENTINEL_TEXT not in caught.value.message


def test_search_structurally_satisfies_document_vector_search_port() -> None:
    adapter, _fake = _search()
    port: DocumentVectorSearchPort = _as_search_port(adapter)
    assert inspect.iscoroutinefunction(port.search)
    assert list(inspect.signature(QdrantDocumentVectorSearch.search).parameters) == [
        "self",
        "query",
    ]


async def test_wrong_query_dimension_is_invalid_before_io() -> None:
    adapter, fake = _search(config=_config(vector_size=4))
    query = _query()
    with pytest.raises(InvalidRequestError, match="incompatible with the index") as caught:
        await _as_search_port(adapter).search(query)
    assert fake.query_calls == []
    assert str(query.vector) not in caught.value.message
    assert "1.0" not in caught.value.message


async def test_empty_search_result_is_empty_tuple() -> None:
    adapter, fake = _search()
    result = await _as_search_port(adapter).search(_query())
    assert result == ()
    assert fake.query_calls[0]["limit"] == 5
    assert fake.query_calls[0]["query"] == [1.0, 0.0, -0.25]
    assert fake.query_calls[0]["with_vectors"] is False


async def test_one_valid_search_result() -> None:
    entry = _entry(chunk=_chunk(text="Ranked clause."))
    fake = _FakeQdrantClient(query_hits=[_hit(entry, score=12.5)])
    adapter, fake = _search(client=fake)
    result = await _as_search_port(adapter).search(_query(limit=3))
    assert result == (entry.chunk,)
    assert not hasattr(result[0], "score")


async def test_multiple_results_preserve_backend_ranking_order() -> None:
    first = _entry(chunk=_chunk(chunk_id="chunk-1", ordinal=0, text="First hit."))
    second = _entry(chunk=_chunk(chunk_id="chunk-2", ordinal=1, text="Second hit."))
    third = _entry(chunk=_chunk(chunk_id="chunk-3", ordinal=2, text="Third hit."))
    fake = _FakeQdrantClient(
        query_hits=[
            _hit(second, score=0.1),
            _hit(first, score=99.0),
            _hit(third, score=50.0),
        ]
    )
    adapter, fake = _search(client=fake)
    result = await _as_search_port(adapter).search(_query(limit=5))
    assert [item.chunk_id for item in result] == ["chunk-2", "chunk-1", "chunk-3"]


async def test_fewer_than_requested_limit_is_valid() -> None:
    entry = _entry()
    fake = _FakeQdrantClient(query_hits=[_hit(entry)])
    adapter, fake = _search(client=fake)
    result = await _as_search_port(adapter).search(_query(limit=8))
    assert len(result) == 1


async def test_query_limit_and_vector_are_propagated_without_tuning() -> None:
    adapter, fake = _search()
    await _as_search_port(adapter).search(_query(vector=(0.5, -1.0, 0.25), limit=7))
    call = fake.query_calls[0]
    assert call["limit"] == 7
    assert call["query"] == [0.5, -1.0, 0.25]
    assert call["with_vectors"] is False
    assert call["with_payload"] == [
        "document_id",
        "chunk_id",
        "ordinal",
        "text",
        "page_number",
        "content_sha256",
    ]
    assert "metadata" not in call["with_payload"]
    assert call["kwargs"] == {}


async def test_same_chunk_id_under_different_documents_is_valid() -> None:
    first = _entry(chunk=_chunk(document_id="doc-a", chunk_id="chunk-shared", text="Alpha."))
    second = _entry(chunk=_chunk(document_id="doc-b", chunk_id="chunk-shared", text="Beta."))
    fake = _FakeQdrantClient(query_hits=[_hit(first, score=2.0), _hit(second, score=1.0)])
    adapter, fake = _search(client=fake)
    result = await _as_search_port(adapter).search(_query())
    assert [(item.document_id, item.chunk_id) for item in result] == [
        ("doc-a", "chunk-shared"),
        ("doc-b", "chunk-shared"),
    ]


async def test_duplicate_logical_identity_is_dependency_unavailable() -> None:
    entry = _entry(chunk=_chunk(text=SENTINEL_TEXT))
    fake = _FakeQdrantClient(query_hits=[_hit(entry, score=1.0), _hit(entry, score=0.5)])
    adapter, fake = _search(client=fake)
    with pytest.raises(
        DependencyUnavailableError, match="Document vector search is unavailable"
    ) as caught:
        await _as_search_port(adapter).search(_query(limit=5))
    assert SENTINEL_TEXT not in caught.value.message


async def test_malformed_search_payload_is_dependency_unavailable() -> None:
    entry = _entry(chunk=_chunk(text=SENTINEL_TEXT))
    hit = _hit(entry)
    hit.payload["filename"] = "secret.pdf"
    fake = _FakeQdrantClient(query_hits=[hit])
    adapter, fake = _search(client=fake)
    with pytest.raises(
        DependencyUnavailableError, match="Document vector search is unavailable"
    ) as caught:
        await _as_search_port(adapter).search(_query())
    assert SENTINEL_TEXT not in caught.value.message
    assert "filename" not in caught.value.message


async def test_search_point_id_mismatch_is_dependency_unavailable() -> None:
    entry = _entry(chunk=_chunk(text=SENTINEL_TEXT))
    hit = _hit(entry)
    hit.id = uuid.uuid4()
    fake = _FakeQdrantClient(query_hits=[hit])
    adapter, fake = _search(client=fake)
    with pytest.raises(
        DependencyUnavailableError, match="Document vector search is unavailable"
    ) as caught:
        await _as_search_port(adapter).search(_query())
    assert SENTINEL_TEXT not in caught.value.message


async def test_more_hits_than_limit_is_dependency_unavailable() -> None:
    first = _entry(chunk=_chunk(chunk_id="chunk-1", ordinal=0, text=SENTINEL_TEXT))
    second = _entry(chunk=_chunk(chunk_id="chunk-2", ordinal=1, text="Other."))
    fake = _FakeQdrantClient(query_hits=[_hit(first), _hit(second)])
    adapter, fake = _search(client=fake)
    with pytest.raises(
        DependencyUnavailableError, match="Document vector search is unavailable"
    ) as caught:
        await _as_search_port(adapter).search(_query(limit=1))
    assert SENTINEL_TEXT not in caught.value.message


async def test_search_backend_failure_is_sanitized() -> None:
    query = _query(vector=SENTINEL_VECTOR)
    fake = _FakeQdrantClient(query_error=_backend_error())
    adapter, fake = _search(client=fake)
    with pytest.raises(
        DependencyUnavailableError, match="Document vector search is unavailable"
    ) as caught:
        await _as_search_port(adapter).search(query)
    message = caught.value.message
    assert SENTINEL_EXCEPTION not in message
    assert SENTINEL_TEXT not in message
    assert "0.123456789" not in message
    assert str(SENTINEL_VECTOR) not in message
    assert COLLECTION not in message
