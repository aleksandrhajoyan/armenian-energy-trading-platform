"""Configured Regulatory Intelligence composition adapts typed settings."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID

import pytest
from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient

from energy_trading.api.composition.regulatory_intelligence import (
    build_regulatory_intelligence_query_execution,
)
from energy_trading.api.composition.regulatory_intelligence_configured_runtime import (
    build_regulatory_intelligence_configured_runtime,
)
from energy_trading.api.composition.regulatory_intelligence_runtime import (
    build_regulatory_intelligence_provider_runtime,
)
from energy_trading.application.orchestration.regulatory_intelligence_query_execution import (
    RegulatoryIntelligenceQueryExecutionService,
)
from energy_trading.application.ports.document_extraction import ExtractedDocumentChunk
from energy_trading.infrastructure.embeddings.openai_query_embedding import (
    OpenAIDocumentQueryEmbeddingAdapter,
)
from energy_trading.infrastructure.regulatory.openai_constraint_inference import (
    OpenAIRegulatoryConstraintInferenceAdapter,
    _ProviderConstraintCandidate,
    _ProviderInferenceEnvelope,
)
from energy_trading.infrastructure.vector_store.qdrant.document_vector import (
    QdrantDocumentVectorConfig,
    QdrantDocumentVectorSearch,
    _point_uuid,
)
from energy_trading.shared.config.regulatory_intelligence import (
    RegulatoryIntelligenceRuntimeSettings,
)
from tests.unit.domain._factories import constraint

_QUERY_EMBEDDING_MODEL = "sentinel-query-embedding-model-chunk73"
_CONSTRAINT_INFERENCE_MODEL = "sentinel-constraint-inference-model-chunk73"
_SHARED_MODEL = "sentinel-shared-model-chunk73"
_SENTINEL_VECTOR: tuple[float, ...] = (0.125, -0.25, 0.5)
_COLLECTION_NAME = "sentinel-regulatory-collection-chunk73"
_FINGERPRINT = "a" * 64

_REGULATORY_ENV_KEYS = (
    "ENERGY_REGULATORY_QUERY_EMBEDDING_MODEL",
    "ENERGY_REGULATORY_CONSTRAINT_INFERENCE_MODEL",
    "ENERGY_REGULATORY_QDRANT_COLLECTION_NAME",
    "ENERGY_REGULATORY_QDRANT_VECTOR_SIZE",
)


@pytest.fixture(autouse=True)
def clear_regulatory_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _REGULATORY_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


@dataclass
class _FakeEmbeddings:
    create_calls: list[dict[str, object]] = field(default_factory=list)
    response: object | None = None

    async def create(self, **kwargs: object) -> object:
        self.create_calls.append(kwargs)
        assert self.response is not None
        return self.response


@dataclass
class _FakeResponses:
    parse_calls: list[dict[str, object]] = field(default_factory=list)
    response: object | None = None

    async def parse(self, **kwargs: object) -> object:
        self.parse_calls.append(kwargs)
        assert self.response is not None
        return self.response


@dataclass
class _FakeOpenAIClient:
    embeddings: _FakeEmbeddings = field(default_factory=_FakeEmbeddings)
    responses: _FakeResponses = field(default_factory=_FakeResponses)
    close_calls: int = 0

    async def close(self) -> None:
        self.close_calls += 1


@dataclass
class _FakeQdrantRecord:
    id: UUID
    payload: dict[str, object]


@dataclass
class _FakeQueryResponse:
    points: list[_FakeQdrantRecord]


@dataclass
class _FakeQdrantClient:
    query_calls: list[dict[str, object]] = field(default_factory=list)
    query_hits: list[_FakeQdrantRecord] = field(default_factory=list)
    close_calls: int = 0

    async def query_points(self, **kwargs: object) -> _FakeQueryResponse:
        self.query_calls.append(dict(kwargs))
        return _FakeQueryResponse(points=list(self.query_hits))

    async def close(self) -> None:
        self.close_calls += 1


def _settings(**overrides: object) -> RegulatoryIntelligenceRuntimeSettings:
    payload: dict[str, object] = {
        "query_embedding_model": _QUERY_EMBEDDING_MODEL,
        "constraint_inference_model": _CONSTRAINT_INFERENCE_MODEL,
        "qdrant_collection_name": _COLLECTION_NAME,
        "qdrant_vector_size": len(_SENTINEL_VECTOR),
    }
    payload.update(overrides)
    return RegulatoryIntelligenceRuntimeSettings(_env_file=None, **payload)


def _chunk() -> ExtractedDocumentChunk:
    return ExtractedDocumentChunk(
        document_id="doc-chunk73",
        chunk_id="chunk-chunk73",
        ordinal=0,
        text="Normalized synthetic regulatory chunk text.",
        page_number=1,
    )


def _search_hit(chunk: ExtractedDocumentChunk) -> _FakeQdrantRecord:
    return _FakeQdrantRecord(
        id=_point_uuid(chunk.document_id, chunk.chunk_id),
        payload={
            "document_id": chunk.document_id,
            "chunk_id": chunk.chunk_id,
            "ordinal": chunk.ordinal,
            "text": chunk.text,
            "page_number": chunk.page_number,
            "content_sha256": _FINGERPRINT,
        },
    )


def _build(
    openai_client: _FakeOpenAIClient,
    qdrant_client: _FakeQdrantClient,
    *,
    settings: RegulatoryIntelligenceRuntimeSettings | None = None,
) -> RegulatoryIntelligenceQueryExecutionService:
    return build_regulatory_intelligence_configured_runtime(
        openai_client=cast(AsyncOpenAI, openai_client),
        qdrant_client=cast(Any, qdrant_client),
        settings=settings or _settings(),
    )


def test_builder_returns_query_execution_service() -> None:
    service = _build(_FakeOpenAIClient(), _FakeQdrantClient())
    assert isinstance(service, RegulatoryIntelligenceQueryExecutionService)
    assert type(service) is RegulatoryIntelligenceQueryExecutionService


def test_builder_is_synchronous() -> None:
    assert inspect.iscoroutinefunction(build_regulatory_intelligence_configured_runtime) is False


def test_builder_is_keyword_only_with_exact_dependencies() -> None:
    signature = inspect.signature(build_regulatory_intelligence_configured_runtime)
    assert tuple(signature.parameters) == ("openai_client", "qdrant_client", "settings")
    for name in signature.parameters:
        parameter = signature.parameters[name]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["openai_client"].annotation is AsyncOpenAI
    assert signature.parameters["qdrant_client"].annotation is AsyncQdrantClient
    assert signature.parameters["settings"].annotation is RegulatoryIntelligenceRuntimeSettings
    assert signature.return_annotation is RegulatoryIntelligenceQueryExecutionService
    assert "api_key" not in signature.parameters
    assert "env_file" not in signature.parameters
    assert "query_embedding_model" not in signature.parameters
    assert "constraint_inference_model" not in signature.parameters
    assert "qdrant_vector_config" not in signature.parameters
    assert "collection_name" not in signature.parameters
    assert "vector_size" not in signature.parameters
    assert "openai_settings" not in signature.parameters
    assert "qdrant_settings" not in signature.parameters
    assert "create_openai_client" not in signature.parameters
    assert "create_qdrant_client" not in signature.parameters
    assert "load_regulatory_intelligence_runtime_settings" not in signature.parameters


def test_receives_exact_runtime_settings_type() -> None:
    settings = _settings()
    service = _build(_FakeOpenAIClient(), _FakeQdrantClient(), settings=settings)
    embedder = service._query_preparation_service._document_query_embedding_port
    inference = service._regulatory_intelligence_agent._inference
    search = service._regulatory_intelligence_agent._search
    assert isinstance(settings, RegulatoryIntelligenceRuntimeSettings)
    assert isinstance(embedder, OpenAIDocumentQueryEmbeddingAdapter)
    assert isinstance(inference, OpenAIRegulatoryConstraintInferenceAdapter)
    assert isinstance(search, QdrantDocumentVectorSearch)


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
        "energy_trading.api.composition.regulatory_intelligence_configured_runtime.QdrantDocumentVectorConfig",
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
    assert config.vector_size == len(_SENTINEL_VECTOR)
    search = service._regulatory_intelligence_agent._search
    assert search._config is config


def test_forwards_exact_model_strings_and_client_identities() -> None:
    openai_client = _FakeOpenAIClient()
    qdrant_client = _FakeQdrantClient()
    settings = _settings()
    service = _build(openai_client, qdrant_client, settings=settings)
    embedder = service._query_preparation_service._document_query_embedding_port
    inference = service._regulatory_intelligence_agent._inference
    search = service._regulatory_intelligence_agent._search
    assert embedder._client is openai_client
    assert inference._client is openai_client
    assert search._client is qdrant_client
    assert embedder._model is settings.query_embedding_model
    assert embedder._model == _QUERY_EMBEDDING_MODEL
    assert inference._model is settings.constraint_inference_model
    assert inference._model == _CONSTRAINT_INFERENCE_MODEL
    assert inference._model != embedder._model


def test_delegates_to_chunk_71_builder_exactly_once_and_returns_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    sentinel = object()

    def spy(**kwargs: object) -> object:
        calls.append(kwargs)
        return sentinel

    monkeypatch.setattr(
        "energy_trading.api.composition.regulatory_intelligence_configured_runtime.build_regulatory_intelligence_provider_runtime",
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
    config = payload["qdrant_vector_config"]
    assert isinstance(config, QdrantDocumentVectorConfig)
    assert config.collection_name == settings.qdrant_collection_name
    assert config.vector_size == settings.qdrant_vector_size
    assert payload["query_embedding_model"] is settings.query_embedding_model
    assert payload["constraint_inference_model"] is settings.constraint_inference_model
    assert result is sentinel


def test_does_not_call_chunk_67_or_construct_adapters_directly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_chunk_67(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Chunk 67 builder must not be called directly")

    monkeypatch.setattr(
        "energy_trading.api.composition.regulatory_intelligence.build_regulatory_intelligence_query_execution",
        fail_chunk_67,
    )
    captured: list[dict[str, object]] = []

    def spy(**kwargs: object) -> object:
        captured.append(kwargs)
        return object()

    monkeypatch.setattr(
        "energy_trading.api.composition.regulatory_intelligence_configured_runtime.build_regulatory_intelligence_provider_runtime",
        spy,
    )
    _build(_FakeOpenAIClient(), _FakeQdrantClient())
    assert len(captured) == 1
    import energy_trading.api.composition.regulatory_intelligence_configured_runtime as module

    assert not hasattr(module, "build_regulatory_intelligence_query_execution")
    assert not hasattr(module, "OpenAIDocumentQueryEmbeddingAdapter")
    assert not hasattr(module, "OpenAIRegulatoryConstraintInferenceAdapter")
    assert not hasattr(module, "QdrantDocumentVectorSearch")
    assert hasattr(module, "build_regulatory_intelligence_provider_runtime")


def test_construction_does_not_invoke_provider_or_close_clients() -> None:
    openai_client = _FakeOpenAIClient()
    qdrant_client = _FakeQdrantClient()
    _build(openai_client, qdrant_client)
    assert openai_client.embeddings.create_calls == []
    assert openai_client.responses.parse_calls == []
    assert qdrant_client.query_calls == []
    assert openai_client.close_calls == 0
    assert qdrant_client.close_calls == 0


def test_construction_does_not_call_settings_loaders_or_client_factories(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_regulatory_settings(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("load_regulatory_intelligence_runtime_settings must not be called")

    def fail_openai_settings(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("load_openai_settings must not be called")

    def fail_openai_client(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("create_openai_client must not be called")

    def fail_qdrant_settings(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("load_qdrant_settings must not be called")

    def fail_qdrant_client(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("create_qdrant_client must not be called")

    monkeypatch.setattr(
        "energy_trading.shared.config.regulatory_intelligence.load_regulatory_intelligence_runtime_settings",
        fail_regulatory_settings,
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


def test_equal_model_values_are_forwarded() -> None:
    settings = _settings(
        query_embedding_model=_SHARED_MODEL,
        constraint_inference_model=_SHARED_MODEL,
    )
    service = _build(_FakeOpenAIClient(), _FakeQdrantClient(), settings=settings)
    embedder = service._query_preparation_service._document_query_embedding_port
    inference = service._regulatory_intelligence_agent._inference
    assert embedder._model == _SHARED_MODEL
    assert inference._model == _SHARED_MODEL
    assert embedder._model == inference._model


async def test_built_service_executes_through_real_chunk_71_and_67_stack() -> None:
    query_text = "  keep surrounding spaces  "
    chunk = _chunk()
    expected = constraint(constraint_id="composed-chunk73")
    envelope = _ProviderInferenceEnvelope(
        constraints=(
            _ProviderConstraintCandidate.model_validate(
                {
                    "constraint_id": expected.constraint_id,
                    "constraint_type": expected.constraint_type,
                    "description": expected.description,
                    "effective_from": expected.effective_from,
                    "effective_to": expected.effective_to,
                    "minimum_value": expected.minimum_value,
                    "maximum_value": expected.maximum_value,
                    "unit": expected.unit,
                    "currency": expected.currency,
                    "source_document_id": expected.source_document_id,
                    "evidence_chunk_ids": (chunk.chunk_id,),
                }
            ),
        )
    )
    openai_client = _FakeOpenAIClient(
        embeddings=_FakeEmbeddings(
            response=SimpleNamespace(data=[SimpleNamespace(embedding=list(_SENTINEL_VECTOR))])
        ),
        responses=_FakeResponses(response=SimpleNamespace(output_parsed=envelope)),
    )
    qdrant_client = _FakeQdrantClient(query_hits=[_search_hit(chunk)])
    service = _build(openai_client, qdrant_client)

    result = await service.execute(query_text=query_text, limit=4)

    assert len(openai_client.embeddings.create_calls) == 1
    assert openai_client.embeddings.create_calls[0]["model"] == _QUERY_EMBEDDING_MODEL
    assert openai_client.embeddings.create_calls[0]["input"] == query_text
    assert openai_client.embeddings.create_calls[0]["encoding_format"] == "float"
    assert len(qdrant_client.query_calls) == 1
    assert qdrant_client.query_calls[0]["collection_name"] == _COLLECTION_NAME
    assert qdrant_client.query_calls[0]["query"] == list(_SENTINEL_VECTOR)
    assert qdrant_client.query_calls[0]["limit"] == 4
    assert len(openai_client.responses.parse_calls) == 1
    assert openai_client.responses.parse_calls[0]["model"] == _CONSTRAINT_INFERENCE_MODEL
    assert result.constraints[0].constraint_id == expected.constraint_id
    assert openai_client.close_calls == 0
    assert qdrant_client.close_calls == 0
    assert inspect.isfunction(build_regulatory_intelligence_provider_runtime)
    assert inspect.isfunction(build_regulatory_intelligence_query_execution)
