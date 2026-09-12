"""Offline unit tests for Qdrant document collection readiness verification.

No live Qdrant process, local mode, or network call is used.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from qdrant_client.common.client_exceptions import ResourceExhaustedResponse
from qdrant_client.http import models
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.infrastructure.vector_store.qdrant.collection_readiness import (
    verify_qdrant_document_collection_ready,
)
from energy_trading.infrastructure.vector_store.qdrant.document_vector import (
    QdrantDocumentVectorConfig,
)

SENTINEL_EXCEPTION = "sentinel-qdrant-exception-chunk105"
COLLECTION = "document-chunks"
VECTOR_SIZE = 3
UNAVAILABLE = "Document vector collection is unavailable."
MUTATION_METHODS = (
    "create_collection",
    "recreate_collection",
    "delete_collection",
    "update_collection",
    "create_payload_index",
    "delete_payload_index",
    "upsert",
    "upload_points",
    "set_payload",
    "delete",
)
POINT_METHODS = ("query_points", "scroll", "count", "retrieve")


@dataclass
class _FakeQdrantClient:
    """Test-only async client surface. Not a production Qdrant connection."""

    info: object | None = None
    error: BaseException | None = None
    get_collection_calls: list[dict[str, Any]] = field(default_factory=list)
    mutation_calls: list[str] = field(default_factory=list)
    point_calls: list[str] = field(default_factory=list)
    other_calls: list[str] = field(default_factory=list)

    async def get_collection(self, collection_name: str, **kwargs: object) -> object:
        self.get_collection_calls.append(
            {"collection_name": collection_name, "kwargs": dict(kwargs)}
        )
        if self.error is not None:
            raise self.error
        if self.info is None:
            msg = "test client has no collection info"
            raise AssertionError(msg)
        return self.info

    async def get_collections(self, **kwargs: object) -> None:
        self.other_calls.append("get_collections")
        raise AssertionError("get_collections must not be called")

    async def collection_exists(self, *args: object, **kwargs: object) -> bool:
        self.other_calls.append("collection_exists")
        raise AssertionError("collection_exists must not be called")

    async def create_collection(self, *args: object, **kwargs: object) -> None:
        self.mutation_calls.append("create_collection")
        raise AssertionError("create_collection must not be called")

    async def recreate_collection(self, *args: object, **kwargs: object) -> None:
        self.mutation_calls.append("recreate_collection")
        raise AssertionError("recreate_collection must not be called")

    async def delete_collection(self, *args: object, **kwargs: object) -> None:
        self.mutation_calls.append("delete_collection")
        raise AssertionError("delete_collection must not be called")

    async def update_collection(self, *args: object, **kwargs: object) -> None:
        self.mutation_calls.append("update_collection")
        raise AssertionError("update_collection must not be called")

    async def create_payload_index(self, *args: object, **kwargs: object) -> None:
        self.mutation_calls.append("create_payload_index")
        raise AssertionError("create_payload_index must not be called")

    async def delete_payload_index(self, *args: object, **kwargs: object) -> None:
        self.mutation_calls.append("delete_payload_index")
        raise AssertionError("delete_payload_index must not be called")

    async def upsert(self, *args: object, **kwargs: object) -> None:
        self.mutation_calls.append("upsert")
        raise AssertionError("upsert must not be called")

    async def upload_points(self, *args: object, **kwargs: object) -> None:
        self.mutation_calls.append("upload_points")
        raise AssertionError("upload_points must not be called")

    async def set_payload(self, *args: object, **kwargs: object) -> None:
        self.mutation_calls.append("set_payload")
        raise AssertionError("set_payload must not be called")

    async def delete(self, *args: object, **kwargs: object) -> None:
        self.mutation_calls.append("delete")
        raise AssertionError("delete must not be called")

    async def query_points(self, *args: object, **kwargs: object) -> None:
        self.point_calls.append("query_points")
        raise AssertionError("query_points must not be called")

    async def scroll(self, *args: object, **kwargs: object) -> None:
        self.point_calls.append("scroll")
        raise AssertionError("scroll must not be called")

    async def count(self, *args: object, **kwargs: object) -> None:
        self.point_calls.append("count")
        raise AssertionError("count must not be called")

    async def retrieve(self, *args: object, **kwargs: object) -> None:
        self.point_calls.append("retrieve")
        raise AssertionError("retrieve must not be called")

    async def close(self) -> None:
        self.other_calls.append("close")
        raise AssertionError("close must not be called")


def _config() -> QdrantDocumentVectorConfig:
    return QdrantDocumentVectorConfig(collection_name=COLLECTION, vector_size=VECTOR_SIZE)


def _vector_params(size: int, distance: models.Distance) -> models.VectorParams:
    return models.VectorParams(size=size, distance=distance)


def _collection_info(
    *,
    vectors: models.VectorParams | dict[str, models.VectorParams] | None,
    sparse_vectors: dict[str, models.SparseVectorParams] | None = None,
) -> models.CollectionInfo:
    params = models.CollectionParams(vectors=vectors, sparse_vectors=sparse_vectors)
    config = models.CollectionConfig(
        params=params,
        hnsw_config=models.HnswConfig(
            m=16,
            ef_construct=100,
            full_scan_threshold=10000,
        ),
        optimizer_config=models.OptimizersConfig(
            deleted_threshold=0.2,
            vacuum_min_vector_number=1000,
            default_segment_number=0,
            flush_interval_sec=5,
            max_optimization_threads=1,
        ),
    )
    return models.CollectionInfo(
        status=models.CollectionStatus.GREEN,
        optimizer_status=models.OptimizersStatusOneOf.OK,
        segments_count=1,
        config=config,
        payload_schema={},
    )


def _backend_error() -> UnexpectedResponse:
    return UnexpectedResponse(
        status_code=404,
        reason_phrase="Not Found",
        content=(
            f"collection={COLLECTION} api_key=secret {SENTINEL_EXCEPTION} host=qdrant.internal"
        ).encode(),
        headers=httpx.Headers({"x-api-key": "sentinel-qdrant-api-key-chunk105"}),
    )


def _assert_no_side_effects(fake: _FakeQdrantClient) -> None:
    assert fake.mutation_calls == []
    assert fake.point_calls == []
    assert fake.other_calls == []


def test_signature_is_keyword_only_async_none() -> None:
    signature = inspect.signature(verify_qdrant_document_collection_ready)
    assert inspect.iscoroutinefunction(verify_qdrant_document_collection_ready)
    assert list(signature.parameters) == ["client", "config"]
    for name in ("client", "config"):
        assert signature.parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.return_annotation is None


@pytest.mark.parametrize(
    "distance",
    (
        models.Distance.COSINE,
        models.Distance.DOT,
        models.Distance.EUCLID,
        models.Distance.MANHATTAN,
    ),
)
async def test_compatible_unnamed_dense_vector_returns_none(
    distance: models.Distance,
) -> None:
    fake = _FakeQdrantClient(info=_collection_info(vectors=_vector_params(VECTOR_SIZE, distance)))
    result = await verify_qdrant_document_collection_ready(client=fake, config=_config())
    assert result is None
    assert fake.get_collection_calls == [{"collection_name": COLLECTION, "kwargs": {}}]
    _assert_no_side_effects(fake)


async def test_vector_size_mismatch_is_sanitized() -> None:
    fake = _FakeQdrantClient(
        info=_collection_info(vectors=_vector_params(VECTOR_SIZE + 1, models.Distance.COSINE))
    )
    with pytest.raises(DependencyUnavailableError, match=UNAVAILABLE) as caught:
        await verify_qdrant_document_collection_ready(client=fake, config=_config())
    assert caught.value.message == UNAVAILABLE
    assert str(VECTOR_SIZE + 1) not in caught.value.message
    assert fake.get_collection_calls == [{"collection_name": COLLECTION, "kwargs": {}}]
    _assert_no_side_effects(fake)


async def test_named_vector_mapping_fails_closed_without_selecting_a_name() -> None:
    named = {
        "dense": _vector_params(VECTOR_SIZE, models.Distance.DOT),
        "title": _vector_params(VECTOR_SIZE, models.Distance.COSINE),
    }
    fake = _FakeQdrantClient(info=_collection_info(vectors=named))
    with pytest.raises(DependencyUnavailableError, match=UNAVAILABLE) as caught:
        await verify_qdrant_document_collection_ready(client=fake, config=_config())
    assert caught.value.message == UNAVAILABLE
    assert "dense" not in caught.value.message
    assert "title" not in caught.value.message
    assert fake.get_collection_calls == [{"collection_name": COLLECTION, "kwargs": {}}]
    _assert_no_side_effects(fake)


async def test_single_named_vector_of_matching_size_fails_closed() -> None:
    fake = _FakeQdrantClient(
        info=_collection_info(vectors={"dense": _vector_params(VECTOR_SIZE, models.Distance.DOT)})
    )
    with pytest.raises(DependencyUnavailableError, match=UNAVAILABLE):
        await verify_qdrant_document_collection_ready(client=fake, config=_config())
    assert fake.get_collection_calls == [{"collection_name": COLLECTION, "kwargs": {}}]
    _assert_no_side_effects(fake)


async def test_sparse_only_configuration_fails_closed() -> None:
    fake = _FakeQdrantClient(
        info=_collection_info(
            vectors=None,
            sparse_vectors={"text": models.SparseVectorParams()},
        )
    )
    with pytest.raises(DependencyUnavailableError, match=UNAVAILABLE) as caught:
        await verify_qdrant_document_collection_ready(client=fake, config=_config())
    assert caught.value.message == UNAVAILABLE
    assert "text" not in caught.value.message
    assert fake.get_collection_calls == [{"collection_name": COLLECTION, "kwargs": {}}]
    _assert_no_side_effects(fake)


async def test_missing_dense_vector_configuration_fails_closed() -> None:
    fake = _FakeQdrantClient(info=_collection_info(vectors=None))
    with pytest.raises(DependencyUnavailableError, match=UNAVAILABLE):
        await verify_qdrant_document_collection_ready(client=fake, config=_config())
    assert fake.get_collection_calls == [{"collection_name": COLLECTION, "kwargs": {}}]
    _assert_no_side_effects(fake)


async def test_malformed_collection_metadata_fails_closed() -> None:
    fake = _FakeQdrantClient(info=SimpleNamespace())
    with pytest.raises(DependencyUnavailableError, match=UNAVAILABLE):
        await verify_qdrant_document_collection_ready(client=fake, config=_config())
    assert fake.get_collection_calls == [{"collection_name": COLLECTION, "kwargs": {}}]
    _assert_no_side_effects(fake)


@pytest.mark.parametrize(
    "error",
    (
        _backend_error(),
        ResponseHandlingException(Exception(SENTINEL_EXCEPTION)),
        ResourceExhaustedResponse(message=SENTINEL_EXCEPTION, retry_after_s=1),
    ),
)
async def test_provider_lookup_failure_is_sanitized(error: BaseException) -> None:
    fake = _FakeQdrantClient(error=error)
    with pytest.raises(DependencyUnavailableError, match=UNAVAILABLE) as caught:
        await verify_qdrant_document_collection_ready(client=fake, config=_config())
    message = caught.value.message
    assert message == UNAVAILABLE
    assert SENTINEL_EXCEPTION not in message
    assert COLLECTION not in message
    assert "api_key" not in message.lower()
    assert "qdrant.internal" not in message
    assert "secret" not in message
    assert caught.value.__cause__ is error
    assert fake.get_collection_calls == [{"collection_name": COLLECTION, "kwargs": {}}]
    _assert_no_side_effects(fake)


async def test_success_and_failure_do_not_call_mutation_or_point_apis() -> None:
    success = _FakeQdrantClient(
        info=_collection_info(vectors=_vector_params(VECTOR_SIZE, models.Distance.COSINE))
    )
    await verify_qdrant_document_collection_ready(client=success, config=_config())
    failure = _FakeQdrantClient(error=_backend_error())
    with pytest.raises(DependencyUnavailableError):
        await verify_qdrant_document_collection_ready(client=failure, config=_config())
    for fake in (success, failure):
        _assert_no_side_effects(fake)
        assert len(fake.get_collection_calls) == 1
        for name in (*MUTATION_METHODS, *POINT_METHODS, "get_collections", "collection_exists"):
            assert name not in fake.mutation_calls
            assert name not in fake.point_calls
            assert name not in fake.other_calls
