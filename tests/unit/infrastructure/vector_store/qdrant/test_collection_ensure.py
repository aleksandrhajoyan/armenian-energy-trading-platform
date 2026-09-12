"""Offline unit tests for Qdrant document collection ensure orchestration.

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
from qdrant_client.http.models import Distance

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.infrastructure.vector_store.qdrant import (
    collection_ensure as production_module,
)
from energy_trading.infrastructure.vector_store.qdrant.collection_ensure import (
    ensure_qdrant_document_collection_ready,
)
from energy_trading.infrastructure.vector_store.qdrant.document_vector import (
    QdrantDocumentVectorConfig,
)

SENTINEL_EXCEPTION = "sentinel-qdrant-exception-chunk108"
COLLECTION = "document-chunks"
VECTOR_SIZE = 3
UNAVAILABLE = "Document vector collection availability could not be determined."
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
LOOKUP_METHODS = ("get_collection", "get_collections")
POINT_METHODS = ("query_points", "scroll", "count", "retrieve")


@dataclass
class _FakeQdrantClient:
    """Test-only async client surface. Not a production Qdrant connection."""

    exists: bool = False
    error: BaseException | None = None
    collection_exists_calls: list[dict[str, Any]] = field(default_factory=list)
    lookup_calls: list[str] = field(default_factory=list)
    mutation_calls: list[str] = field(default_factory=list)
    point_calls: list[str] = field(default_factory=list)
    other_calls: list[str] = field(default_factory=list)

    async def collection_exists(self, collection_name: str, **kwargs: object) -> bool:
        self.collection_exists_calls.append(
            {"collection_name": collection_name, "kwargs": dict(kwargs)}
        )
        if self.error is not None:
            raise self.error
        return self.exists

    async def get_collection(self, *args: object, **kwargs: object) -> object:
        self.lookup_calls.append("get_collection")
        raise AssertionError("get_collection must not be called")

    async def get_collections(self, **kwargs: object) -> None:
        self.lookup_calls.append("get_collections")
        raise AssertionError("get_collections must not be called")

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


@dataclass
class _DelegateRecorder:
    """Records keyword-only create/verify collaborator calls."""

    error: BaseException | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def __call__(
        self,
        *,
        client: object,
        config: object,
        distance: object,
    ) -> None:
        self.calls.append({"client": client, "config": config, "distance": distance})
        if self.error is not None:
            raise self.error


def _config() -> QdrantDocumentVectorConfig:
    return QdrantDocumentVectorConfig(collection_name=COLLECTION, vector_size=VECTOR_SIZE)


def _backend_error() -> UnexpectedResponse:
    return UnexpectedResponse(
        status_code=500,
        reason_phrase="Internal Server Error",
        content=(
            f"collection={COLLECTION} api_key=secret {SENTINEL_EXCEPTION} host=qdrant.internal"
        ).encode(),
        headers=httpx.Headers({"x-api-key": "sentinel-qdrant-api-key-chunk108"}),
    )


def _install_delegates(
    monkeypatch: pytest.MonkeyPatch,
    *,
    create: _DelegateRecorder,
    verify: _DelegateRecorder,
) -> None:
    monkeypatch.setattr(production_module, "create_qdrant_document_collection", create)
    monkeypatch.setattr(production_module, "verify_qdrant_document_collection_ready", verify)


def _assert_one_probe(fake: _FakeQdrantClient) -> None:
    assert fake.collection_exists_calls == [{"collection_name": COLLECTION, "kwargs": {}}]


def _assert_no_unrelated_apis(fake: _FakeQdrantClient) -> None:
    assert fake.lookup_calls == []
    assert fake.mutation_calls == []
    assert fake.point_calls == []
    assert fake.other_calls == []
    for name in (*LOOKUP_METHODS, *MUTATION_METHODS, *POINT_METHODS, "close"):
        assert name not in fake.lookup_calls
        assert name not in fake.mutation_calls
        assert name not in fake.point_calls
        assert name not in fake.other_calls


def _assert_forwarded(
    recorder: _DelegateRecorder,
    *,
    client: object,
    config: object,
    distance: object,
) -> None:
    assert len(recorder.calls) == 1
    call = recorder.calls[0]
    assert call["client"] is client
    assert call["config"] is config
    assert call["distance"] is distance


def test_signature_is_keyword_only_async_none() -> None:
    signature = inspect.signature(ensure_qdrant_document_collection_ready)
    assert inspect.iscoroutinefunction(ensure_qdrant_document_collection_ready)
    assert list(signature.parameters) == ["client", "config", "distance"]
    for name in ("client", "config", "distance"):
        parameter = signature.parameters[name]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty
    assert signature.return_annotation is None


async def test_distance_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeQdrantClient()
    create = _DelegateRecorder()
    verify = _DelegateRecorder()
    _install_delegates(monkeypatch, create=create, verify=verify)
    with pytest.raises(TypeError):
        await ensure_qdrant_document_collection_ready(client=fake, config=_config())
    assert fake.collection_exists_calls == []
    assert create.calls == []
    assert verify.calls == []
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
async def test_missing_collection_creates_once_and_skips_readiness(
    monkeypatch: pytest.MonkeyPatch,
    distance: Distance,
) -> None:
    fake = _FakeQdrantClient(exists=False)
    create = _DelegateRecorder()
    verify = _DelegateRecorder()
    _install_delegates(monkeypatch, create=create, verify=verify)
    config = _config()
    result = await ensure_qdrant_document_collection_ready(
        client=fake,
        config=config,
        distance=distance,
    )
    assert result is None
    _assert_one_probe(fake)
    _assert_forwarded(create, client=fake, config=config, distance=distance)
    assert verify.calls == []
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
async def test_existing_collection_verifies_once_and_skips_creation(
    monkeypatch: pytest.MonkeyPatch,
    distance: Distance,
) -> None:
    fake = _FakeQdrantClient(exists=True)
    create = _DelegateRecorder()
    verify = _DelegateRecorder()
    _install_delegates(monkeypatch, create=create, verify=verify)
    config = _config()
    result = await ensure_qdrant_document_collection_ready(
        client=fake,
        config=config,
        distance=distance,
    )
    assert result is None
    _assert_one_probe(fake)
    assert create.calls == []
    _assert_forwarded(verify, client=fake, config=config, distance=distance)
    _assert_no_unrelated_apis(fake)


@pytest.mark.parametrize(
    "error",
    (
        _backend_error(),
        ResponseHandlingException(Exception(SENTINEL_EXCEPTION)),
        ResourceExhaustedResponse(message=SENTINEL_EXCEPTION, retry_after_s=1),
    ),
)
async def test_existence_probe_provider_failure_is_sanitized(
    monkeypatch: pytest.MonkeyPatch,
    error: BaseException,
) -> None:
    fake = _FakeQdrantClient(error=error)
    create = _DelegateRecorder()
    verify = _DelegateRecorder()
    _install_delegates(monkeypatch, create=create, verify=verify)
    with pytest.raises(DependencyUnavailableError, match=UNAVAILABLE) as caught:
        await ensure_qdrant_document_collection_ready(
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
    assert "6333" not in message
    assert caught.value.__cause__ is error
    _assert_one_probe(fake)
    assert create.calls == []
    assert verify.calls == []
    _assert_no_unrelated_apis(fake)


async def test_creation_delegate_failure_propagates_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeQdrantClient(exists=False)
    sentinel = DependencyUnavailableError("sentinel-create-chunk108")
    create = _DelegateRecorder(error=sentinel)
    verify = _DelegateRecorder()
    _install_delegates(monkeypatch, create=create, verify=verify)
    config = _config()
    with pytest.raises(DependencyUnavailableError) as caught:
        await ensure_qdrant_document_collection_ready(
            client=fake,
            config=config,
            distance=Distance.COSINE,
        )
    assert caught.value is sentinel
    assert caught.value.message == "sentinel-create-chunk108"
    _assert_one_probe(fake)
    _assert_forwarded(create, client=fake, config=config, distance=Distance.COSINE)
    assert verify.calls == []
    _assert_no_unrelated_apis(fake)


async def test_readiness_delegate_failure_propagates_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeQdrantClient(exists=True)
    sentinel = DependencyUnavailableError("sentinel-verify-chunk108")
    create = _DelegateRecorder()
    verify = _DelegateRecorder(error=sentinel)
    _install_delegates(monkeypatch, create=create, verify=verify)
    config = _config()
    with pytest.raises(DependencyUnavailableError) as caught:
        await ensure_qdrant_document_collection_ready(
            client=fake,
            config=config,
            distance=Distance.EUCLID,
        )
    assert caught.value is sentinel
    assert caught.value.message == "sentinel-verify-chunk108"
    _assert_one_probe(fake)
    assert create.calls == []
    _assert_forwarded(verify, client=fake, config=config, distance=Distance.EUCLID)
    _assert_no_unrelated_apis(fake)


def test_production_does_not_hardcode_distance_or_duplicate_primitives() -> None:
    source = inspect.getsource(production_module)
    assert "get_collection" not in source
    assert "create_collection" not in source.replace("create_qdrant_document_collection", "")
    assert "VectorParams" not in source
    assert "Distance.COSINE" not in source
    assert "Distance.DOT" not in source
    assert "Distance.EUCLID" not in source
    assert "Distance.MANHATTAN" not in source
    assert "recreate_collection" not in source
    assert "delete_collection" not in source
    assert "update_collection" not in source
