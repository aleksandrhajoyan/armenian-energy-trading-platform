"""Qdrant adapters for document vector index and search ports.

These classes structurally implement ``DocumentVectorIndexPort`` and
``DocumentVectorSearchPort``. They do not own the ``AsyncQdrantClient``
lifecycle, create collections, select a distance metric, or perform
embedding inference.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from qdrant_client import AsyncQdrantClient
from qdrant_client.common.client_exceptions import ResourceExhaustedResponse
from qdrant_client.http import models
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

from energy_trading.application.errors import (
    ConflictError,
    DependencyUnavailableError,
    InvalidRequestError,
)
from energy_trading.application.ports.document_extraction import ExtractedDocumentChunk
from energy_trading.application.ports.document_vector_index import DocumentVectorIndexEntry
from energy_trading.application.ports.document_vector_search import DocumentVectorSearchQuery

_MSG_INDEX_UNAVAILABLE: Final[str] = "Document vector index is unavailable."
_MSG_SEARCH_UNAVAILABLE: Final[str] = "Document vector search is unavailable."
_MSG_CONFLICT: Final[str] = "A conflicting document chunk is already indexed."
_MSG_INDEX_DIMENSION: Final[str] = "Index entries must match the configured vector dimension."
_MSG_QUERY_DIMENSION: Final[str] = "Query vector dimension is incompatible with the index."

_PAYLOAD_KEYS: Final[tuple[str, ...]] = (
    "document_id",
    "chunk_id",
    "ordinal",
    "text",
    "page_number",
    "content_sha256",
)
_ALLOWED_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset(_PAYLOAD_KEYS)
_POINT_ID_NAMESPACE: Final[uuid.UUID] = uuid.uuid5(
    uuid.NAMESPACE_URL,
    "https://energy-trading.local/qdrant/document-vector-point",
)
_QDRANT_BACKEND_ERRORS: Final[tuple[type[BaseException], ...]] = (
    UnexpectedResponse,
    ResponseHandlingException,
    ResourceExhaustedResponse,
)
_LogicalIdentity = tuple[str, str]


@dataclass(frozen=True, slots=True)
class QdrantDocumentVectorConfig:
    """Infrastructure collection targeting for document vectors.

    Not an application contract and not part of ``QdrantSettings``. Distance,
    score thresholds, and collection provisioning are out of scope.
    """

    collection_name: str
    vector_size: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "collection_name", _require_collection_name(self.collection_name))
        object.__setattr__(self, "vector_size", _require_vector_size(self.vector_size))


class QdrantDocumentVectorIndex:
    """Insert-only Qdrant writer for ``DocumentVectorIndexPort``."""

    def __init__(self, client: AsyncQdrantClient, config: QdrantDocumentVectorConfig) -> None:
        self._client = client
        self._config = config

    async def index(self, entries: tuple[DocumentVectorIndexEntry, ...]) -> None:
        """Index paired chunks and embeddings with exact-retry conflict semantics."""

        if not entries:
            return
        coalesced = _coalesce_entries(entries)
        _require_configured_dimension(
            (item.embedding.vector for item in coalesced),
            self._config.vector_size,
            message=_MSG_INDEX_DIMENSION,
        )
        existing = await self._retrieve_by_entries(coalesced)
        to_insert: list[DocumentVectorIndexEntry] = []
        for entry in coalesced:
            point_id = _point_uuid(entry.chunk.document_id, entry.chunk.chunk_id)
            stored = existing.get(str(point_id))
            if stored is None:
                to_insert.append(entry)
                continue
            if stored.fingerprint == _entry_fingerprint(entry):
                continue
            raise ConflictError(_MSG_CONFLICT)
        if not to_insert:
            return
        points = [_to_point_struct(item) for item in to_insert]
        try:
            await self._client.upsert(
                collection_name=self._config.collection_name,
                points=points,
                wait=True,
                update_mode=models.UpdateMode.INSERT_ONLY,
            )
        except _QDRANT_BACKEND_ERRORS as exc:
            raise DependencyUnavailableError(_MSG_INDEX_UNAVAILABLE) from exc
        after = await self._retrieve_by_entries(to_insert)
        for entry in to_insert:
            point_id = _point_uuid(entry.chunk.document_id, entry.chunk.chunk_id)
            stored = after.get(str(point_id))
            if stored is None:
                raise DependencyUnavailableError(_MSG_INDEX_UNAVAILABLE)
            if stored.fingerprint != _entry_fingerprint(entry):
                raise ConflictError(_MSG_CONFLICT)

    async def _retrieve_by_entries(
        self,
        entries: Sequence[DocumentVectorIndexEntry],
    ) -> dict[str, _StoredPoint]:
        ids = [_point_uuid(item.chunk.document_id, item.chunk.chunk_id) for item in entries]
        try:
            records = await self._client.retrieve(
                collection_name=self._config.collection_name,
                ids=ids,
                with_payload=True,
                with_vectors=False,
            )
        except _QDRANT_BACKEND_ERRORS as exc:
            raise DependencyUnavailableError(_MSG_INDEX_UNAVAILABLE) from exc
        stored: dict[str, _StoredPoint] = {}
        for record in records:
            parsed = _parse_stored_point(record, unavailable_message=_MSG_INDEX_UNAVAILABLE)
            if parsed.point_id in stored:
                raise DependencyUnavailableError(_MSG_INDEX_UNAVAILABLE)
            stored[parsed.point_id] = parsed
        return stored


class QdrantDocumentVectorSearch:
    """Ranked Qdrant reader for ``DocumentVectorSearchPort``."""

    def __init__(self, client: AsyncQdrantClient, config: QdrantDocumentVectorConfig) -> None:
        self._client = client
        self._config = config

    async def search(self, query: DocumentVectorSearchQuery) -> tuple[ExtractedDocumentChunk, ...]:
        """Return ranked normalized chunks for an already-embedded query."""

        _require_configured_dimension(
            (query.vector,),
            self._config.vector_size,
            message=_MSG_QUERY_DIMENSION,
        )
        try:
            response = await self._client.query_points(
                collection_name=self._config.collection_name,
                query=list(query.vector),
                limit=query.limit,
                with_vectors=False,
                with_payload=list(_PAYLOAD_KEYS),
            )
        except _QDRANT_BACKEND_ERRORS as exc:
            raise DependencyUnavailableError(_MSG_SEARCH_UNAVAILABLE) from exc
        points = getattr(response, "points", None)
        if not isinstance(points, Sequence) or isinstance(points, (str, bytes, bytearray)):
            raise DependencyUnavailableError(_MSG_SEARCH_UNAVAILABLE)
        if len(points) > query.limit:
            raise DependencyUnavailableError(_MSG_SEARCH_UNAVAILABLE)
        results: list[ExtractedDocumentChunk] = []
        seen: set[_LogicalIdentity] = set()
        for point in points:
            stored = _parse_stored_point(point, unavailable_message=_MSG_SEARCH_UNAVAILABLE)
            identity = (stored.chunk.document_id, stored.chunk.chunk_id)
            if identity in seen:
                raise DependencyUnavailableError(_MSG_SEARCH_UNAVAILABLE)
            seen.add(identity)
            results.append(stored.chunk)
        return tuple(results)


@dataclass(frozen=True, slots=True)
class _StoredPoint:
    point_id: str
    chunk: ExtractedDocumentChunk
    fingerprint: str


def _require_collection_name(value: object) -> str:
    if not isinstance(value, str):
        msg = "collection_name must be a string"
        raise TypeError(msg)
    stripped = value.strip()
    if not stripped:
        msg = "collection_name must not be blank"
        raise ValueError(msg)
    return stripped


def _require_vector_size(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = "vector_size must be an integer"
        raise TypeError(msg)
    if value < 1:
        msg = "vector_size must be greater than 0"
        raise ValueError(msg)
    return value


def _require_configured_dimension(
    vectors: Iterable[Sequence[float]],
    expected: int,
    *,
    message: str,
) -> None:
    for vector in vectors:
        if len(vector) != expected:
            raise InvalidRequestError(message)


def _coalesce_entries(
    entries: tuple[DocumentVectorIndexEntry, ...],
) -> tuple[DocumentVectorIndexEntry, ...]:
    coalesced: dict[_LogicalIdentity, DocumentVectorIndexEntry] = {}
    for entry in entries:
        identity = (entry.chunk.document_id, entry.chunk.chunk_id)
        existing = coalesced.get(identity)
        if existing is not None and existing != entry:
            raise ConflictError(_MSG_CONFLICT)
        coalesced[identity] = entry
    return tuple(coalesced.values())


def _point_uuid(document_id: str, chunk_id: str) -> uuid.UUID:
    encoded = json.dumps(
        [document_id, chunk_id],
        ensure_ascii=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return uuid.uuid5(_POINT_ID_NAMESPACE, encoded)


def _entry_fingerprint(entry: DocumentVectorIndexEntry) -> str:
    chunk = entry.chunk
    canonical = {
        "chunk_id": chunk.chunk_id,
        "document_id": chunk.document_id,
        "ordinal": chunk.ordinal,
        "page_number": chunk.page_number,
        "text": chunk.text,
        "vector": [value.hex() for value in entry.embedding.vector],
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _encode_payload(entry: DocumentVectorIndexEntry) -> dict[str, object]:
    chunk = entry.chunk
    return {
        "document_id": chunk.document_id,
        "chunk_id": chunk.chunk_id,
        "ordinal": chunk.ordinal,
        "text": chunk.text,
        "page_number": chunk.page_number,
        "content_sha256": _entry_fingerprint(entry),
    }


def _to_point_struct(entry: DocumentVectorIndexEntry) -> models.PointStruct:
    return models.PointStruct(
        id=_point_uuid(entry.chunk.document_id, entry.chunk.chunk_id),
        vector=list(entry.embedding.vector),
        payload=_encode_payload(entry),
    )


def _parse_stored_point(record: object, *, unavailable_message: str) -> _StoredPoint:
    point_id = _normalize_point_id(
        getattr(record, "id", None), unavailable_message=unavailable_message
    )
    payload = getattr(record, "payload", None)
    if not isinstance(payload, Mapping):
        raise DependencyUnavailableError(unavailable_message)
    keys = set(payload.keys())
    if keys != _ALLOWED_PAYLOAD_KEYS:
        raise DependencyUnavailableError(unavailable_message)
    try:
        chunk = ExtractedDocumentChunk(
            document_id=_require_payload_str(payload["document_id"]),
            chunk_id=_require_payload_str(payload["chunk_id"]),
            ordinal=_require_payload_int(payload["ordinal"], allow_zero=True),
            text=_require_payload_str(payload["text"]),
            page_number=_require_payload_page_number(payload["page_number"]),
        )
        fingerprint = _require_fingerprint(payload["content_sha256"])
    except (TypeError, ValueError) as exc:
        raise DependencyUnavailableError(unavailable_message) from exc
    expected = str(_point_uuid(chunk.document_id, chunk.chunk_id))
    if point_id != expected:
        raise DependencyUnavailableError(unavailable_message)
    return _StoredPoint(point_id=point_id, chunk=chunk, fingerprint=fingerprint)


def _normalize_point_id(value: object, *, unavailable_message: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise DependencyUnavailableError(unavailable_message) from exc


def _require_payload_str(value: object) -> str:
    if not isinstance(value, str):
        msg = "payload field must be a string"
        raise TypeError(msg)
    return value


def _require_payload_int(value: object, *, allow_zero: bool) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = "payload field must be an integer"
        raise TypeError(msg)
    if allow_zero and value < 0:
        msg = "payload ordinal must be non-negative"
        raise ValueError(msg)
    if not allow_zero and value < 1:
        msg = "payload integer must be positive"
        raise ValueError(msg)
    return value


def _require_payload_page_number(value: object) -> int | None:
    if value is None:
        return None
    return _require_payload_int(value, allow_zero=False)


def _require_fingerprint(value: object) -> str:
    if not isinstance(value, str):
        msg = "content_sha256 must be a string"
        raise TypeError(msg)
    digest = value.lower()
    if len(digest) != 64:
        msg = "content_sha256 must be a SHA-256 hex digest"
        raise ValueError(msg)
    try:
        int(digest, 16)
    except ValueError as exc:
        msg = "content_sha256 must be a SHA-256 hex digest"
        raise ValueError(msg) from exc
    return digest
