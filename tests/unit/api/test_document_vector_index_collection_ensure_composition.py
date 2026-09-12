"""Configured document-index collection ensure composition stays a thin seam.

No live Qdrant, Docker, OpenAI, credentials, ``.env``, or network is used.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, cast

import pytest
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance

from energy_trading.api.composition.document_vector_index_collection_ensure import (
    ensure_configured_document_vector_index_collection_ready,
)
from energy_trading.api.composition.qdrant_document_vector_distance import (
    map_qdrant_document_vector_distance,
)
from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.infrastructure.vector_store.qdrant.document_vector import (
    QdrantDocumentVectorConfig,
)
from energy_trading.shared.config.document_vector_index import (
    DocumentVectorIndexRuntimeSettings,
)
from energy_trading.shared.config.qdrant import (
    QdrantDocumentVectorDistance,
    QdrantDocumentVectorDistanceSettings,
)

_COMPOSITION_MODULE = "energy_trading.api.composition.document_vector_index_collection_ensure"
_DOCUMENT_EMBEDDING_MODEL = "sentinel-document-embedding-model-chunk110"
_COLLECTION_NAME = "sentinel-document-index-collection-chunk110"
_VECTOR_SIZE = 3
_DOCUMENT_INDEX_ENV_KEYS = (
    "ENERGY_DOCUMENT_INDEX_DOCUMENT_EMBEDDING_MODEL",
    "ENERGY_DOCUMENT_INDEX_QDRANT_COLLECTION_NAME",
    "ENERGY_DOCUMENT_INDEX_QDRANT_VECTOR_SIZE",
)
_DISTANCE_ENV_KEY = "QDRANT_DOCUMENT_VECTOR_DISTANCE"
_EXPECTED_METRICS = (
    (QdrantDocumentVectorDistance.COSINE, Distance.COSINE),
    (QdrantDocumentVectorDistance.DOT, Distance.DOT),
    (QdrantDocumentVectorDistance.EUCLID, Distance.EUCLID),
    (QdrantDocumentVectorDistance.MANHATTAN, Distance.MANHATTAN),
)


@pytest.fixture(autouse=True)
def clear_configured_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (*_DOCUMENT_INDEX_ENV_KEYS, _DISTANCE_ENV_KEY, "QDRANT_HOST"):
        monkeypatch.delenv(key, raising=False)


@dataclass
class _FakeQdrantClient:
    collection_exists_calls: list[dict[str, object]] = field(default_factory=list)
    create_collection_calls: list[str] = field(default_factory=list)
    get_collection_calls: list[str] = field(default_factory=list)
    upsert_calls: list[str] = field(default_factory=list)
    query_points_calls: list[str] = field(default_factory=list)
    close_calls: int = 0

    async def collection_exists(self, **kwargs: object) -> bool:
        self.collection_exists_calls.append(dict(kwargs))
        raise AssertionError("collection_exists must not be called")

    async def create_collection(self, **kwargs: object) -> None:
        self.create_collection_calls.append("create_collection")
        raise AssertionError("create_collection must not be called")

    async def get_collection(self, **kwargs: object) -> object:
        self.get_collection_calls.append("get_collection")
        raise AssertionError("get_collection must not be called")

    async def upsert(self, **kwargs: object) -> object:
        self.upsert_calls.append("upsert")
        raise AssertionError("upsert must not be called")

    async def query_points(self, **kwargs: object) -> object:
        self.query_points_calls.append("query_points")
        raise AssertionError("query_points must not be called")

    async def close(self) -> None:
        self.close_calls += 1
        raise AssertionError("close must not be called")


def _runtime_settings(**overrides: object) -> DocumentVectorIndexRuntimeSettings:
    payload: dict[str, object] = {
        "document_embedding_model": _DOCUMENT_EMBEDDING_MODEL,
        "qdrant_collection_name": _COLLECTION_NAME,
        "qdrant_vector_size": _VECTOR_SIZE,
    }
    payload.update(overrides)
    return DocumentVectorIndexRuntimeSettings(_env_file=None, **payload)


def _distance_settings(
    distance: QdrantDocumentVectorDistance = QdrantDocumentVectorDistance.DOT,
) -> QdrantDocumentVectorDistanceSettings:
    return QdrantDocumentVectorDistanceSettings(
        _env_file=None,
        document_vector_distance=distance,
    )


def _install_ensure(
    monkeypatch: pytest.MonkeyPatch,
    *,
    error: BaseException | None = None,
) -> list[dict[str, object]]:
    calls: list[dict[str, object]] = []

    async def spy(**kwargs: object) -> None:
        calls.append(kwargs)
        if error is not None:
            raise error

    monkeypatch.setattr(f"{_COMPOSITION_MODULE}.ensure_qdrant_document_collection_ready", spy)
    return calls


def _assert_no_client_io(client: _FakeQdrantClient) -> None:
    assert client.collection_exists_calls == []
    assert client.create_collection_calls == []
    assert client.get_collection_calls == []
    assert client.upsert_calls == []
    assert client.query_points_calls == []
    assert client.close_calls == 0


def test_function_is_async_and_keyword_only() -> None:
    signature = inspect.signature(ensure_configured_document_vector_index_collection_ready)
    assert inspect.iscoroutinefunction(ensure_configured_document_vector_index_collection_ready)
    assert tuple(signature.parameters) == (
        "client",
        "runtime_settings",
        "distance_settings",
    )
    for name in signature.parameters:
        parameter = signature.parameters[name]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty
    assert signature.parameters["client"].annotation is AsyncQdrantClient
    assert signature.parameters["runtime_settings"].annotation is DocumentVectorIndexRuntimeSettings
    assert (
        signature.parameters["distance_settings"].annotation is QdrantDocumentVectorDistanceSettings
    )
    assert signature.return_annotation is None
    assert "env_file" not in signature.parameters
    assert "qdrant_config" not in signature.parameters
    assert "distance" not in signature.parameters
    assert "document_embedding_model" not in signature.parameters


async def test_positional_arguments_are_rejected() -> None:
    client = _FakeQdrantClient()
    with pytest.raises(TypeError):
        await ensure_configured_document_vector_index_collection_ready(
            client,  # type: ignore[misc]
            _runtime_settings(),
            _distance_settings(),
        )
    _assert_no_client_io(client)


async def test_forwards_exact_client_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _install_ensure(monkeypatch)
    client = _FakeQdrantClient()
    result = await ensure_configured_document_vector_index_collection_ready(
        client=cast(Any, client),
        runtime_settings=_runtime_settings(),
        distance_settings=_distance_settings(),
    )
    assert result is None
    assert len(calls) == 1
    assert calls[0]["client"] is client
    _assert_no_client_io(client)


async def test_constructs_one_qdrant_config_from_runtime_qdrant_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constructed: list[QdrantDocumentVectorConfig] = []
    real = QdrantDocumentVectorConfig

    def spy(*args: object, **kwargs: object) -> QdrantDocumentVectorConfig:
        item = real(*args, **kwargs)  # type: ignore[arg-type]
        constructed.append(item)
        return item

    monkeypatch.setattr(f"{_COMPOSITION_MODULE}.QdrantDocumentVectorConfig", spy)
    calls = _install_ensure(monkeypatch)
    settings = _runtime_settings()
    result = await ensure_configured_document_vector_index_collection_ready(
        client=cast(Any, _FakeQdrantClient()),
        runtime_settings=settings,
        distance_settings=_distance_settings(),
    )
    assert result is None
    assert len(constructed) == 1
    config = constructed[0]
    assert isinstance(config, QdrantDocumentVectorConfig)
    assert config.collection_name == settings.qdrant_collection_name
    assert config.collection_name == _COLLECTION_NAME
    assert config.vector_size == settings.qdrant_vector_size
    assert config.vector_size == _VECTOR_SIZE
    assert calls[0]["config"] is config
    assert "document_embedding_model" not in inspect.signature(real).parameters


async def test_document_embedding_model_does_not_participate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constructed_kwargs: list[dict[str, object]] = []
    real = QdrantDocumentVectorConfig

    def spy(*args: object, **kwargs: object) -> QdrantDocumentVectorConfig:
        constructed_kwargs.append(dict(kwargs))
        return real(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(f"{_COMPOSITION_MODULE}.QdrantDocumentVectorConfig", spy)
    _install_ensure(monkeypatch)
    settings = _runtime_settings(document_embedding_model="unused-model-must-not-provision")
    await ensure_configured_document_vector_index_collection_ready(
        client=cast(Any, _FakeQdrantClient()),
        runtime_settings=settings,
        distance_settings=_distance_settings(),
    )
    assert constructed_kwargs == [
        {
            "collection_name": _COLLECTION_NAME,
            "vector_size": _VECTOR_SIZE,
        }
    ]
    assert settings.document_embedding_model == "unused-model-must-not-provision"


async def test_configured_distance_is_sent_once_through_the_published_mapper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mapped: list[object] = []
    sentinel_distance = object()

    def spy(*, distance: object) -> object:
        mapped.append(distance)
        return sentinel_distance

    monkeypatch.setattr(f"{_COMPOSITION_MODULE}.map_qdrant_document_vector_distance", spy)
    calls = _install_ensure(monkeypatch)
    distance_settings = _distance_settings(QdrantDocumentVectorDistance.EUCLID)
    result = await ensure_configured_document_vector_index_collection_ready(
        client=cast(Any, _FakeQdrantClient()),
        runtime_settings=_runtime_settings(),
        distance_settings=distance_settings,
    )
    assert result is None
    assert mapped == [distance_settings.document_vector_distance]
    assert mapped[0] is QdrantDocumentVectorDistance.EUCLID
    assert calls[0]["distance"] is sentinel_distance


@pytest.mark.parametrize(("configured", "expected"), _EXPECTED_METRICS)
async def test_all_four_configured_metrics_flow_through_the_real_mapper(
    monkeypatch: pytest.MonkeyPatch,
    configured: QdrantDocumentVectorDistance,
    expected: Distance,
) -> None:
    calls = _install_ensure(monkeypatch)
    result = await ensure_configured_document_vector_index_collection_ready(
        client=cast(Any, _FakeQdrantClient()),
        runtime_settings=_runtime_settings(),
        distance_settings=_distance_settings(configured),
    )
    assert result is None
    assert len(calls) == 1
    assert calls[0]["distance"] is expected
    assert calls[0]["distance"] is map_qdrant_document_vector_distance(distance=configured)


async def test_ensure_is_awaited_exactly_once_and_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _install_ensure(monkeypatch)
    result = await ensure_configured_document_vector_index_collection_ready(
        client=cast(Any, _FakeQdrantClient()),
        runtime_settings=_runtime_settings(),
        distance_settings=_distance_settings(),
    )
    assert result is None
    assert len(calls) == 1


async def test_dependency_unavailable_from_ensure_propagates_by_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = DependencyUnavailableError("sentinel-ensure-chunk110")
    _install_ensure(monkeypatch, error=sentinel)
    with pytest.raises(DependencyUnavailableError) as caught:
        await ensure_configured_document_vector_index_collection_ready(
            client=cast(Any, _FakeQdrantClient()),
            runtime_settings=_runtime_settings(),
            distance_settings=_distance_settings(),
        )
    assert caught.value is sentinel
    assert caught.value.message == "sentinel-ensure-chunk110"
    assert caught.value.__cause__ is None


async def test_construction_does_not_load_settings_construct_clients_or_mutate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_document_index_settings(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("load_document_vector_index_runtime_settings must not be called")

    def fail_distance_settings(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("load_qdrant_document_vector_distance_settings must not be called")

    def fail_qdrant_settings(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("load_qdrant_settings must not be called")

    def fail_qdrant_client(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("create_qdrant_client must not be called")

    def fail_create(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("create_qdrant_document_collection must not be called")

    def fail_verify(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("verify_qdrant_document_collection_ready must not be called")

    monkeypatch.setattr(
        "energy_trading.shared.config.document_vector_index.load_document_vector_index_runtime_settings",
        fail_document_index_settings,
    )
    monkeypatch.setattr(
        "energy_trading.shared.config.qdrant.load_qdrant_document_vector_distance_settings",
        fail_distance_settings,
    )
    monkeypatch.setattr(
        "energy_trading.shared.config.qdrant.load_qdrant_settings",
        fail_qdrant_settings,
    )
    monkeypatch.setattr(
        "energy_trading.infrastructure.vector_store.qdrant.client.create_qdrant_client",
        fail_qdrant_client,
    )
    monkeypatch.setattr(
        "energy_trading.infrastructure.vector_store.qdrant.collection_creation.create_qdrant_document_collection",
        fail_create,
    )
    monkeypatch.setattr(
        "energy_trading.infrastructure.vector_store.qdrant.collection_readiness.verify_qdrant_document_collection_ready",
        fail_verify,
    )
    client = _FakeQdrantClient()
    _install_ensure(monkeypatch)
    await ensure_configured_document_vector_index_collection_ready(
        client=cast(Any, client),
        runtime_settings=_runtime_settings(),
        distance_settings=_distance_settings(),
    )
    _assert_no_client_io(client)
    import energy_trading.api.composition.document_vector_index_collection_ensure as module

    assert not hasattr(module, "load_document_vector_index_runtime_settings")
    assert not hasattr(module, "load_qdrant_document_vector_distance_settings")
    assert not hasattr(module, "create_qdrant_client")
    assert not hasattr(module, "create_qdrant_document_collection")
    assert not hasattr(module, "verify_qdrant_document_collection_ready")
    assert hasattr(module, "map_qdrant_document_vector_distance")
    assert hasattr(module, "ensure_qdrant_document_collection_ready")
