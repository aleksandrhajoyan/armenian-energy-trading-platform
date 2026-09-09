"""Provider-aware document vector index composition wires published adapters."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, cast

import pytest
from openai import AsyncOpenAI

from energy_trading.api.composition.document_vector_index_execution import (
    build_document_vector_index_execution,
)
from energy_trading.api.composition.document_vector_index_runtime import (
    build_document_vector_index_provider_runtime,
)
from energy_trading.application.orchestration import (
    DocumentVectorIndexEntryPreparationService,
    DocumentVectorIndexExecutionService,
)
from energy_trading.infrastructure.embeddings.openai_document_embedding import (
    OpenAIDocumentEmbeddingAdapter,
)
from energy_trading.infrastructure.vector_store.qdrant.document_vector import (
    QdrantDocumentVectorConfig,
    QdrantDocumentVectorIndex,
)

_DOCUMENT_EMBEDDING_MODEL = "text-embedding-chunk87-document"
_COLLECTION_NAME = "document-index-chunk87"
_VECTOR_SIZE = 3


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


def _config() -> QdrantDocumentVectorConfig:
    return QdrantDocumentVectorConfig(
        collection_name=_COLLECTION_NAME,
        vector_size=_VECTOR_SIZE,
    )


def _build(
    openai_client: _FakeOpenAIClient,
    qdrant_client: _FakeQdrantClient,
    *,
    config: QdrantDocumentVectorConfig | None = None,
    document_embedding_model: str = _DOCUMENT_EMBEDDING_MODEL,
) -> DocumentVectorIndexExecutionService:
    return build_document_vector_index_provider_runtime(
        openai_client=cast(AsyncOpenAI, openai_client),
        qdrant_client=cast(Any, qdrant_client),
        qdrant_config=config or _config(),
        document_embedding_model=document_embedding_model,
    )


def test_builder_returns_index_execution_service() -> None:
    service = _build(_FakeOpenAIClient(), _FakeQdrantClient())
    assert isinstance(service, DocumentVectorIndexExecutionService)
    assert type(service) is DocumentVectorIndexExecutionService


def test_builder_is_synchronous() -> None:
    assert inspect.iscoroutinefunction(build_document_vector_index_provider_runtime) is False


def test_builder_is_keyword_only_with_exact_dependencies() -> None:
    signature = inspect.signature(build_document_vector_index_provider_runtime)
    assert tuple(signature.parameters) == (
        "openai_client",
        "qdrant_client",
        "qdrant_config",
        "document_embedding_model",
    )
    for name in signature.parameters:
        parameter = signature.parameters[name]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["openai_client"].annotation is AsyncOpenAI
    assert signature.parameters["qdrant_config"].annotation is QdrantDocumentVectorConfig
    assert signature.parameters["document_embedding_model"].annotation is str
    assert signature.return_annotation is DocumentVectorIndexExecutionService
    assert "api_key" not in signature.parameters
    assert "settings" not in signature.parameters
    assert "openai_settings" not in signature.parameters
    assert "qdrant_settings" not in signature.parameters
    assert "create_openai_client" not in signature.parameters
    assert "create_qdrant_client" not in signature.parameters
    assert "env_file" not in signature.parameters
    assert "collection_name" not in signature.parameters


def test_document_embedding_adapter_receives_exact_client_and_model() -> None:
    openai_client = _FakeOpenAIClient()
    service = _build(openai_client, _FakeQdrantClient())
    embedder = service._preparation_service._document_embedding_port
    assert isinstance(embedder, OpenAIDocumentEmbeddingAdapter)
    assert embedder._client is openai_client
    assert embedder._model is _DOCUMENT_EMBEDDING_MODEL
    assert embedder._model == _DOCUMENT_EMBEDDING_MODEL


def test_qdrant_index_adapter_receives_exact_client_and_config() -> None:
    qdrant_client = _FakeQdrantClient()
    config = _config()
    service = _build(_FakeOpenAIClient(), qdrant_client, config=config)
    index = service._document_vector_index_port
    assert isinstance(index, QdrantDocumentVectorIndex)
    assert index._client is qdrant_client
    assert index._config is config
    assert index._config.collection_name == _COLLECTION_NAME
    assert index._config.vector_size == _VECTOR_SIZE


def test_constructs_exactly_one_openai_adapter_and_one_qdrant_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    embedding_calls: list[OpenAIDocumentEmbeddingAdapter] = []
    index_calls: list[QdrantDocumentVectorIndex] = []
    real_embedding = OpenAIDocumentEmbeddingAdapter
    real_index = QdrantDocumentVectorIndex

    def tracking_embedding(*, client: object, model: str) -> OpenAIDocumentEmbeddingAdapter:
        adapter = real_embedding(client=cast(AsyncOpenAI, client), model=model)
        embedding_calls.append(adapter)
        return adapter

    def tracking_index(
        client: object,
        config: QdrantDocumentVectorConfig,
    ) -> QdrantDocumentVectorIndex:
        adapter = real_index(cast(Any, client), config)
        index_calls.append(adapter)
        return adapter

    monkeypatch.setattr(
        "energy_trading.api.composition.document_vector_index_runtime.OpenAIDocumentEmbeddingAdapter",
        tracking_embedding,
    )
    monkeypatch.setattr(
        "energy_trading.api.composition.document_vector_index_runtime.QdrantDocumentVectorIndex",
        tracking_index,
    )
    service = _build(_FakeOpenAIClient(), _FakeQdrantClient())
    assert len(embedding_calls) == 1
    assert len(index_calls) == 1
    assert service._preparation_service._document_embedding_port is embedding_calls[0]
    assert service._document_vector_index_port is index_calls[0]


def test_delegates_to_existing_chunk_86_builder_exactly_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    real = build_document_vector_index_execution

    def spy(**kwargs: object) -> DocumentVectorIndexExecutionService:
        calls.append(kwargs)
        return real(**kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(
        "energy_trading.api.composition.document_vector_index_runtime.build_document_vector_index_execution",
        spy,
    )
    openai_client = _FakeOpenAIClient()
    qdrant_client = _FakeQdrantClient()
    service = _build(openai_client, qdrant_client)
    assert len(calls) == 1
    payload = calls[0]
    assert isinstance(payload["document_embedding_port"], OpenAIDocumentEmbeddingAdapter)
    assert isinstance(payload["document_vector_index_port"], QdrantDocumentVectorIndex)
    embedder = payload["document_embedding_port"]
    index = payload["document_vector_index_port"]
    assert embedder._client is openai_client
    assert embedder._model == _DOCUMENT_EMBEDDING_MODEL
    assert index._client is qdrant_client
    assert isinstance(service, DocumentVectorIndexExecutionService)
    assert isinstance(service._preparation_service, DocumentVectorIndexEntryPreparationService)
    assert service._preparation_service._document_embedding_port is embedder
    assert service._document_vector_index_port is index


def test_delegated_chunk_86_return_identity_is_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = object()
    calls: list[dict[str, object]] = []

    def spy(**kwargs: object) -> object:
        calls.append(kwargs)
        return sentinel

    monkeypatch.setattr(
        "energy_trading.api.composition.document_vector_index_runtime.build_document_vector_index_execution",
        spy,
    )
    result = _build(_FakeOpenAIClient(), _FakeQdrantClient())
    assert len(calls) == 1
    assert result is sentinel


def test_construction_does_not_invoke_provider_or_application_runtime() -> None:
    openai_client = _FakeOpenAIClient()
    qdrant_client = _FakeQdrantClient()
    _build(openai_client, qdrant_client)
    assert openai_client.embeddings.create_calls == []
    assert qdrant_client.upsert_calls == []
    assert qdrant_client.retrieve_calls == []
    assert openai_client.close_calls == 0
    assert qdrant_client.close_calls == 0


def test_construction_does_not_call_client_factories_or_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_openai_settings(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("load_openai_settings must not be called")

    def fail_openai_client(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("create_openai_client must not be called")

    def fail_qdrant_settings(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("load_qdrant_settings must not be called")

    def fail_qdrant_client(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("create_qdrant_client must not be called")

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


def test_builder_does_not_close_injected_clients() -> None:
    openai_client = _FakeOpenAIClient()
    qdrant_client = _FakeQdrantClient()
    _build(openai_client, qdrant_client)
    assert openai_client.close_calls == 0
    assert qdrant_client.close_calls == 0


async def test_real_offline_openai_client_is_not_closed_or_called() -> None:
    openai_client = AsyncOpenAI(api_key="sentinel-openai-api-key-chunk87", max_retries=0)
    qdrant_client = _FakeQdrantClient()
    try:
        service = build_document_vector_index_provider_runtime(
            openai_client=openai_client,
            qdrant_client=cast(Any, qdrant_client),
            qdrant_config=_config(),
            document_embedding_model=_DOCUMENT_EMBEDDING_MODEL,
        )
        embedder = service._preparation_service._document_embedding_port
        index = service._document_vector_index_port
        assert embedder._client is openai_client
        assert index._client is qdrant_client
        assert openai_client.is_closed() is False
        assert qdrant_client.upsert_calls == []
        assert qdrant_client.retrieve_calls == []
        assert qdrant_client.close_calls == 0
    finally:
        await openai_client.close()
    assert openai_client.is_closed() is True
