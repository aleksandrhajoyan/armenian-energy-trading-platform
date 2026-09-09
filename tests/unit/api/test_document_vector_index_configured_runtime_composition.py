"""Configured document vector index composition adapts typed settings."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, cast

import pytest
from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient

from energy_trading.api.composition.document_vector_index_configured_runtime import (
    build_document_vector_index_configured_runtime,
)
from energy_trading.api.composition.document_vector_index_execution import (
    build_document_vector_index_execution,
)
from energy_trading.api.composition.document_vector_index_runtime import (
    build_document_vector_index_provider_runtime,
)
from energy_trading.application.orchestration.document_vector_index_execution import (
    DocumentVectorIndexExecutionService,
)
from energy_trading.infrastructure.embeddings.openai_document_embedding import (
    OpenAIDocumentEmbeddingAdapter,
)
from energy_trading.infrastructure.vector_store.qdrant.document_vector import (
    QdrantDocumentVectorConfig,
    QdrantDocumentVectorIndex,
)
from energy_trading.shared.config.document_vector_index import (
    DocumentVectorIndexRuntimeSettings,
)

_DOCUMENT_EMBEDDING_MODEL = "sentinel-document-embedding-model-chunk89"
_COLLECTION_NAME = "sentinel-document-index-collection-chunk89"
_VECTOR_SIZE = 3

_DOCUMENT_INDEX_ENV_KEYS = (
    "ENERGY_DOCUMENT_INDEX_DOCUMENT_EMBEDDING_MODEL",
    "ENERGY_DOCUMENT_INDEX_QDRANT_COLLECTION_NAME",
    "ENERGY_DOCUMENT_INDEX_QDRANT_VECTOR_SIZE",
)


@pytest.fixture(autouse=True)
def clear_document_index_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _DOCUMENT_INDEX_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


@dataclass
class _FakeEmbeddings:
    create_calls: list[dict[str, object]] = field(default_factory=list)

    async def create(self, **kwargs: object) -> object:
        self.create_calls.append(kwargs)
        raise AssertionError("embeddings.create must not be called")


@dataclass
class _FakeOpenAIClient:
    embeddings: _FakeEmbeddings = field(default_factory=_FakeEmbeddings)
    close_calls: int = 0

    async def close(self) -> None:
        self.close_calls += 1


@dataclass
class _FakeQdrantClient:
    upsert_calls: list[dict[str, object]] = field(default_factory=list)
    retrieve_calls: list[dict[str, object]] = field(default_factory=list)
    close_calls: int = 0

    async def upsert(self, **kwargs: object) -> object:
        self.upsert_calls.append(dict(kwargs))
        raise AssertionError("qdrant upsert must not be called")

    async def retrieve(self, **kwargs: object) -> object:
        self.retrieve_calls.append(dict(kwargs))
        raise AssertionError("qdrant retrieve must not be called")

    async def close(self) -> None:
        self.close_calls += 1


def _settings(**overrides: object) -> DocumentVectorIndexRuntimeSettings:
    payload: dict[str, object] = {
        "document_embedding_model": _DOCUMENT_EMBEDDING_MODEL,
        "qdrant_collection_name": _COLLECTION_NAME,
        "qdrant_vector_size": _VECTOR_SIZE,
    }
    payload.update(overrides)
    return DocumentVectorIndexRuntimeSettings(_env_file=None, **payload)


def _build(
    openai_client: _FakeOpenAIClient,
    qdrant_client: _FakeQdrantClient,
    *,
    settings: DocumentVectorIndexRuntimeSettings | None = None,
) -> DocumentVectorIndexExecutionService:
    return build_document_vector_index_configured_runtime(
        openai_client=cast(AsyncOpenAI, openai_client),
        qdrant_client=cast(Any, qdrant_client),
        settings=settings or _settings(),
    )


def test_builder_returns_index_execution_service() -> None:
    service = _build(_FakeOpenAIClient(), _FakeQdrantClient())
    assert isinstance(service, DocumentVectorIndexExecutionService)
    assert type(service) is DocumentVectorIndexExecutionService


def test_builder_is_synchronous() -> None:
    assert inspect.iscoroutinefunction(build_document_vector_index_configured_runtime) is False


def test_builder_is_keyword_only_with_exact_dependencies() -> None:
    signature = inspect.signature(build_document_vector_index_configured_runtime)
    assert tuple(signature.parameters) == ("openai_client", "qdrant_client", "settings")
    for name in signature.parameters:
        parameter = signature.parameters[name]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["openai_client"].annotation is AsyncOpenAI
    assert signature.parameters["qdrant_client"].annotation is AsyncQdrantClient
    assert signature.parameters["settings"].annotation is DocumentVectorIndexRuntimeSettings
    assert signature.return_annotation is DocumentVectorIndexExecutionService
    assert "api_key" not in signature.parameters
    assert "env_file" not in signature.parameters
    assert "document_embedding_model" not in signature.parameters
    assert "qdrant_config" not in signature.parameters
    assert "qdrant_vector_config" not in signature.parameters
    assert "collection_name" not in signature.parameters
    assert "vector_size" not in signature.parameters
    assert "openai_settings" not in signature.parameters
    assert "qdrant_settings" not in signature.parameters
    assert "create_openai_client" not in signature.parameters
    assert "create_qdrant_client" not in signature.parameters
    assert "load_document_vector_index_runtime_settings" not in signature.parameters


def test_receives_exact_runtime_settings_type() -> None:
    settings = _settings()
    service = _build(_FakeOpenAIClient(), _FakeQdrantClient(), settings=settings)
    embedder = service._preparation_service._document_embedding_port
    index = service._document_vector_index_port
    assert isinstance(settings, DocumentVectorIndexRuntimeSettings)
    assert isinstance(embedder, OpenAIDocumentEmbeddingAdapter)
    assert isinstance(index, QdrantDocumentVectorIndex)


def test_constructs_one_qdrant_config_from_exact_settings_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constructed: list[QdrantDocumentVectorConfig] = []
    real = QdrantDocumentVectorConfig

    def spy(*args: object, **kwargs: object) -> QdrantDocumentVectorConfig:
        item = real(*args, **kwargs)  # type: ignore[arg-type]
        constructed.append(item)
        return item

    monkeypatch.setattr(
        "energy_trading.api.composition.document_vector_index_configured_runtime.QdrantDocumentVectorConfig",
        spy,
    )
    settings = _settings()
    service = _build(_FakeOpenAIClient(), _FakeQdrantClient(), settings=settings)
    assert len(constructed) == 1
    config = constructed[0]
    assert isinstance(config, QdrantDocumentVectorConfig)
    assert config.collection_name == settings.qdrant_collection_name
    assert config.collection_name == _COLLECTION_NAME
    assert config.vector_size == settings.qdrant_vector_size
    assert config.vector_size == _VECTOR_SIZE
    index = service._document_vector_index_port
    assert index._config is config


def test_forwards_exact_model_string_and_client_identities() -> None:
    openai_client = _FakeOpenAIClient()
    qdrant_client = _FakeQdrantClient()
    settings = _settings()
    service = _build(openai_client, qdrant_client, settings=settings)
    embedder = service._preparation_service._document_embedding_port
    index = service._document_vector_index_port
    assert embedder._client is openai_client
    assert index._client is qdrant_client
    assert embedder._model is settings.document_embedding_model
    assert embedder._model == _DOCUMENT_EMBEDDING_MODEL


def test_delegates_to_chunk_87_builder_exactly_once_and_returns_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    sentinel = object()

    def spy(**kwargs: object) -> object:
        calls.append(kwargs)
        return sentinel

    monkeypatch.setattr(
        "energy_trading.api.composition.document_vector_index_configured_runtime.build_document_vector_index_provider_runtime",
        spy,
    )
    openai_client = _FakeOpenAIClient()
    qdrant_client = _FakeQdrantClient()
    settings = _settings()
    result = _build(openai_client, qdrant_client, settings=settings)
    assert len(calls) == 1
    payload = calls[0]
    assert payload["openai_client"] is openai_client
    assert payload["qdrant_client"] is qdrant_client
    config = payload["qdrant_config"]
    assert isinstance(config, QdrantDocumentVectorConfig)
    assert config.collection_name == settings.qdrant_collection_name
    assert config.vector_size == settings.qdrant_vector_size
    assert payload["document_embedding_model"] is settings.document_embedding_model
    assert result is sentinel


def test_does_not_call_chunk_86_or_construct_adapters_directly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_chunk_86(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Chunk 86 builder must not be called directly")

    monkeypatch.setattr(
        "energy_trading.api.composition.document_vector_index_execution.build_document_vector_index_execution",
        fail_chunk_86,
    )
    captured: list[dict[str, object]] = []

    def spy(**kwargs: object) -> object:
        captured.append(kwargs)
        return object()

    monkeypatch.setattr(
        "energy_trading.api.composition.document_vector_index_configured_runtime.build_document_vector_index_provider_runtime",
        spy,
    )
    _build(_FakeOpenAIClient(), _FakeQdrantClient())
    assert len(captured) == 1
    import energy_trading.api.composition.document_vector_index_configured_runtime as module

    assert not hasattr(module, "build_document_vector_index_execution")
    assert not hasattr(module, "OpenAIDocumentEmbeddingAdapter")
    assert not hasattr(module, "QdrantDocumentVectorIndex")
    assert hasattr(module, "build_document_vector_index_provider_runtime")


def test_construction_does_not_invoke_provider_or_close_clients() -> None:
    openai_client = _FakeOpenAIClient()
    qdrant_client = _FakeQdrantClient()
    _build(openai_client, qdrant_client)
    assert openai_client.embeddings.create_calls == []
    assert qdrant_client.upsert_calls == []
    assert qdrant_client.retrieve_calls == []
    assert openai_client.close_calls == 0
    assert qdrant_client.close_calls == 0


def test_construction_does_not_call_settings_loaders_or_client_factories(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_document_index_settings(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("load_document_vector_index_runtime_settings must not be called")

    def fail_openai_settings(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("load_openai_settings must not be called")

    def fail_openai_client(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("create_openai_client must not be called")

    def fail_qdrant_settings(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("load_qdrant_settings must not be called")

    def fail_qdrant_client(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("create_qdrant_client must not be called")

    monkeypatch.setattr(
        "energy_trading.shared.config.document_vector_index.load_document_vector_index_runtime_settings",
        fail_document_index_settings,
    )
    monkeypatch.setattr(
        "energy_trading.shared.config.openai.load_openai_settings",
        fail_openai_settings,
    )
    monkeypatch.setattr(
        "energy_trading.infrastructure.openai.client.create_openai_client",
        fail_openai_client,
    )
    monkeypatch.setattr(
        "energy_trading.shared.config.qdrant.load_qdrant_settings",
        fail_qdrant_settings,
    )
    monkeypatch.setattr(
        "energy_trading.infrastructure.vector_store.qdrant.client.create_qdrant_client",
        fail_qdrant_client,
    )
    _build(_FakeOpenAIClient(), _FakeQdrantClient())
    assert inspect.isfunction(build_document_vector_index_provider_runtime)
    assert inspect.isfunction(build_document_vector_index_execution)
