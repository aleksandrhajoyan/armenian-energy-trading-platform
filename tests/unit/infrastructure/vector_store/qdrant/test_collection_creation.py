"""Offline unit tests for Qdrant document collection creation.

No live Qdrant process, local mode, or network call is used.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest
from qdrant_client.common.client_exceptions import ResourceExhaustedResponse
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse
from qdrant_client.http.models import Distance, VectorParams

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.infrastructure.vector_store.qdrant import (
    collection_creation as production_module,
)
from energy_trading.infrastructure.vector_store.qdrant.collection_creation import (
    create_qdrant_document_collection,
)
from energy_trading.infrastructure.vector_store.qdrant.document_vector import (
    QdrantDocumentVectorConfig,
)

SENTINEL_EXCEPTION = "sentinel-qdrant-exception-chunk106"
COLLECTION = "document-chunks"
VECTOR_SIZE = 3
UNAVAILABLE = "Document vector collection could not be created."
LOOKUP_METHODS = ("get_collection", "get_collections", "collection_exists")
MUTATION_METHODS = (
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

    error: BaseException | None = None
    created: bool = True
    create_collection_calls: list[dict[str, Any]] = field(default_factory=list)
    lookup_calls: list[str] = field(default_factory=list)
    mutation_calls: list[str] = field(default_factory=list)
    point_calls: list[str] = field(default_factory=list)
    other_calls: list[str] = field(default_factory=list)

    async def create_collection(
        self,
        collection_name: str,
        vectors_config: object = None,
        **kwargs: object,
    ) -> bool:
        self.create_collection_calls.append(
            {
                "collection_name": collection_name,
                "vectors_config": vectors_config,
                "kwargs": dict(kwargs),
            }
        )
        if self.error is not None:
            raise self.error
        return self.created

    async def get_collection(self, *args: object, **kwargs: object) -> object:
        self.lookup_calls.append("get_collection")
        raise AssertionError("get_collection must not be called")

    async def get_collections(self, **kwargs: object) -> None:
        self.lookup_calls.append("get_collections")
        raise AssertionError("get_collections must not be called")

    async def collection_exists(self, *args: object, **kwargs: object) -> bool:
        self.lookup_calls.append("collection_exists")
        raise AssertionError("collection_exists must not be called")

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


def _backend_error(*, status_code: int = 500) -> UnexpectedResponse:
    return UnexpectedResponse(
        status_code=status_code,
        reason_phrase="Conflict" if status_code == 409 else "Internal Server Error",
        content=(
            f"collection={COLLECTION} api_key=secret {SENTINEL_EXCEPTION} host=qdrant.internal"
        ).encode(),
        headers=httpx.Headers({"x-api-key": "sentinel-qdrant-api-key-chunk106"}),
    )


def _assert_no_unrelated_apis(fake: _FakeQdrantClient) -> None:
    assert fake.lookup_calls == []
    assert fake.mutation_calls == []
    assert fake.point_calls == []
    assert fake.other_calls == []


def _assert_one_create(
    fake: _FakeQdrantClient,
    *,
    distance: Distance,
) -> None:
    assert len(fake.create_collection_calls) == 1
    call = fake.create_collection_calls[0]
    assert call["collection_name"] == COLLECTION
    assert call["kwargs"] == {}
    vectors_config = call["vectors_config"]
    assert isinstance(vectors_config, VectorParams)
    assert vectors_config.size == VECTOR_SIZE
    assert vectors_config.distance is distance


def test_signature_is_keyword_only_async_none() -> None:
    signature = inspect.signature(create_qdrant_document_collection)
    assert inspect.iscoroutinefunction(create_qdrant_document_collection)
    assert list(signature.parameters) == ["client", "config", "distance"]
    for name in ("client", "config", "distance"):
        parameter = signature.parameters[name]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty
    assert signature.return_annotation is None


async def test_distance_is_required() -> None:
    fake = _FakeQdrantClient()
    with pytest.raises(TypeError):
        await create_qdrant_document_collection(client=fake, config=_config())
    assert fake.create_collection_calls == []
    _assert_no_unrelated_apis(fake)


@pytest.mark.parametrize(
    "distance",
    (
        Distance.COSINE,
        Distance.DOT,
        Distance.EUCLID,
        Distance.MANHATTAN,
    ),
)
async def test_explicit_distance_creates_unnamed_dense_collection(
    distance: Distance,
) -> None:
    fake = _FakeQdrantClient()
    result = await create_qdrant_document_collection(
        client=fake,
        config=_config(),
        distance=distance,
    )
    assert result is None
    _assert_one_create(fake, distance=distance)
    _assert_no_unrelated_apis(fake)


@pytest.mark.parametrize(
    "error",
    (
        _backend_error(),
        ResponseHandlingException(Exception(SENTINEL_EXCEPTION)),
        ResourceExhaustedResponse(message=SENTINEL_EXCEPTION, retry_after_s=1),
    ),
)
async def test_provider_creation_failure_is_sanitized(error: BaseException) -> None:
    fake = _FakeQdrantClient(error=error)
    with pytest.raises(DependencyUnavailableError, match=UNAVAILABLE) as caught:
        await create_qdrant_document_collection(
            client=fake,
            config=_config(),
            distance=Distance.DOT,
        )
    message = caught.value.message
    assert message == UNAVAILABLE
    assert SENTINEL_EXCEPTION not in message
    assert COLLECTION not in message
    assert "api_key" not in message.lower()
    assert "qdrant.internal" not in message
    assert "secret" not in message
    assert str(VECTOR_SIZE) not in message
    assert "Dot" not in message
    assert "VectorParams" not in message
    assert caught.value.__cause__ is error
    _assert_one_create(fake, distance=Distance.DOT)
    _assert_no_unrelated_apis(fake)


async def test_false_create_result_is_sanitized_without_cause() -> None:
    fake = _FakeQdrantClient(created=False)
    with pytest.raises(DependencyUnavailableError, match=UNAVAILABLE) as caught:
        await create_qdrant_document_collection(
            client=fake,
            config=_config(),
            distance=Distance.DOT,
        )
    message = caught.value.message
    assert message == UNAVAILABLE
    assert SENTINEL_EXCEPTION not in message
    assert COLLECTION not in message
    assert "api_key" not in message.lower()
    assert "qdrant.internal" not in message
    assert "secret" not in message
    assert str(VECTOR_SIZE) not in message
    assert "Dot" not in message
    assert "VectorParams" not in message
    assert caught.value.__cause__ is None
    _assert_one_create(fake, distance=Distance.DOT)
    _assert_no_unrelated_apis(fake)
    assert "get_collection" not in fake.lookup_calls
    assert "collection_exists" not in fake.lookup_calls
    assert "recreate_collection" not in fake.mutation_calls
    assert "delete_collection" not in fake.mutation_calls
    assert "update_collection" not in fake.mutation_calls


async def test_already_existing_collection_is_sanitized_provider_failure() -> None:
    error = _backend_error(status_code=409)
    fake = _FakeQdrantClient(error=error)
    with pytest.raises(DependencyUnavailableError, match=UNAVAILABLE) as caught:
        await create_qdrant_document_collection(
            client=fake,
            config=_config(),
            distance=Distance.COSINE,
        )
    message = caught.value.message
    assert message == UNAVAILABLE
    assert SENTINEL_EXCEPTION not in message
    assert COLLECTION not in message
    assert "already" not in message.lower()
    assert caught.value.__cause__ is error
    _assert_one_create(fake, distance=Distance.COSINE)
    _assert_no_unrelated_apis(fake)
    assert "get_collection" not in fake.lookup_calls
    assert "collection_exists" not in fake.lookup_calls
    assert "recreate_collection" not in fake.mutation_calls
    assert "delete_collection" not in fake.mutation_calls
    assert "update_collection" not in fake.mutation_calls


async def test_success_and_failure_do_not_call_unrelated_apis() -> None:
    success = _FakeQdrantClient()
    await create_qdrant_document_collection(
        client=success,
        config=_config(),
        distance=Distance.EUCLID,
    )
    failure = _FakeQdrantClient(error=_backend_error())
    with pytest.raises(DependencyUnavailableError):
        await create_qdrant_document_collection(
            client=failure,
            config=_config(),
            distance=Distance.MANHATTAN,
        )
    for fake, distance in (
        (success, Distance.EUCLID),
        (failure, Distance.MANHATTAN),
    ):
        _assert_one_create(fake, distance=distance)
        _assert_no_unrelated_apis(fake)
        for name in (*LOOKUP_METHODS, *MUTATION_METHODS, *POINT_METHODS, "close"):
            assert name not in fake.lookup_calls
            assert name not in fake.mutation_calls
            assert name not in fake.point_calls
            assert name not in fake.other_calls


def test_production_does_not_hardcode_distance_or_call_readiness() -> None:
    source = inspect.getsource(production_module)
    assert "verify_qdrant_document_collection_ready" not in source
    assert "get_collection" not in source
    assert "collection_exists" not in source
    assert "Distance.COSINE" not in source
    assert "Distance.DOT" not in source
    assert "Distance.EUCLID" not in source
    assert "Distance.MANHATTAN" not in source
