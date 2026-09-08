"""Provider-aware Regulatory Intelligence composition wires published adapters."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID

import pytest
from openai import AsyncOpenAI

from energy_trading.api.composition.regulatory_intelligence import (
    build_regulatory_intelligence_query_execution,
)
from energy_trading.api.composition.regulatory_intelligence_runtime import (
    build_regulatory_intelligence_provider_runtime,
)
from energy_trading.application.agents.regulatory_intelligence import (
    RegulatoryIntelligenceAgent,
    RegulatoryIntelligenceResult,
)
from energy_trading.application.orchestration import (
    DocumentVectorSearchQueryPreparationService,
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
from tests.unit.domain._factories import constraint

_QUERY_EMBEDDING_MODEL = "text-embedding-chunk71-query"
_CONSTRAINT_INFERENCE_MODEL = "gpt-chunk71-inference"
_SENTINEL_VECTOR: tuple[float, ...] = (0.125, -0.25, 0.5)
_COLLECTION_NAME = "regulatory-docs-chunk71"
_FINGERPRINT = "a" * 64


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


def _config() -> QdrantDocumentVectorConfig:
    return QdrantDocumentVectorConfig(
        collection_name=_COLLECTION_NAME,
        vector_size=len(_SENTINEL_VECTOR),
    )


def _chunk() -> ExtractedDocumentChunk:
    return ExtractedDocumentChunk(
        document_id="doc-chunk71",
        chunk_id="chunk-chunk71",
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
    config: QdrantDocumentVectorConfig | None = None,
    query_embedding_model: str = _QUERY_EMBEDDING_MODEL,
    constraint_inference_model: str = _CONSTRAINT_INFERENCE_MODEL,
) -> RegulatoryIntelligenceQueryExecutionService:
    return build_regulatory_intelligence_provider_runtime(
        openai_client=cast(AsyncOpenAI, openai_client),
        qdrant_client=cast(Any, qdrant_client),
        qdrant_vector_config=config or _config(),
        query_embedding_model=query_embedding_model,
        constraint_inference_model=constraint_inference_model,
    )


def test_builder_returns_query_execution_service() -> None:
    service = _build(_FakeOpenAIClient(), _FakeQdrantClient())
    assert isinstance(service, RegulatoryIntelligenceQueryExecutionService)
    assert type(service) is RegulatoryIntelligenceQueryExecutionService


def test_builder_is_synchronous() -> None:
    assert inspect.iscoroutinefunction(build_regulatory_intelligence_provider_runtime) is False


def test_builder_is_keyword_only_with_exact_dependencies() -> None:
    signature = inspect.signature(build_regulatory_intelligence_provider_runtime)
    assert tuple(signature.parameters) == (
        "openai_client",
        "qdrant_client",
        "qdrant_vector_config",
        "query_embedding_model",
        "constraint_inference_model",
    )
    for name in signature.parameters:
        parameter = signature.parameters[name]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["openai_client"].annotation is AsyncOpenAI
    assert signature.parameters["qdrant_vector_config"].annotation is QdrantDocumentVectorConfig
    assert signature.parameters["query_embedding_model"].annotation is str
    assert signature.parameters["constraint_inference_model"].annotation is str
    assert signature.return_annotation is RegulatoryIntelligenceQueryExecutionService
    assert "api_key" not in signature.parameters
    assert "settings" not in signature.parameters
    assert "openai_settings" not in signature.parameters
    assert "qdrant_settings" not in signature.parameters
    assert "create_openai_client" not in signature.parameters
    assert "create_qdrant_client" not in signature.parameters
    assert "env_file" not in signature.parameters
    assert "collection_name" not in signature.parameters


def test_query_embedding_adapter_receives_exact_client_and_model() -> None:
    openai_client = _FakeOpenAIClient()
    service = _build(openai_client, _FakeQdrantClient())
    embedder = service._query_preparation_service._document_query_embedding_port
    assert isinstance(embedder, OpenAIDocumentQueryEmbeddingAdapter)
    assert embedder._client is openai_client
    assert embedder._model is _QUERY_EMBEDDING_MODEL
    assert embedder._model == _QUERY_EMBEDDING_MODEL


def test_inference_adapter_receives_the_same_openai_client_and_distinct_model() -> None:
    openai_client = _FakeOpenAIClient()
    service = _build(openai_client, _FakeQdrantClient())
    inference = service._regulatory_intelligence_agent._inference
    embedder = service._query_preparation_service._document_query_embedding_port
    assert isinstance(inference, OpenAIRegulatoryConstraintInferenceAdapter)
    assert inference._client is openai_client
    assert embedder._client is openai_client
    assert inference._client is embedder._client
    assert inference._model is _CONSTRAINT_INFERENCE_MODEL
    assert inference._model == _CONSTRAINT_INFERENCE_MODEL
    assert inference._model != embedder._model


def test_qdrant_search_adapter_receives_exact_client_and_config() -> None:
    qdrant_client = _FakeQdrantClient()
    config = _config()
    service = _build(_FakeOpenAIClient(), qdrant_client, config=config)
    search = service._regulatory_intelligence_agent._search
    assert isinstance(search, QdrantDocumentVectorSearch)
    assert search._client is qdrant_client
    assert search._config is config
    assert search._config.collection_name == _COLLECTION_NAME
    assert search._config.vector_size == len(_SENTINEL_VECTOR)


def test_delegates_to_existing_chunk_67_builder_exactly_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    real = build_regulatory_intelligence_query_execution

    def spy(**kwargs: object) -> RegulatoryIntelligenceQueryExecutionService:
        calls.append(kwargs)
        return real(**kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(
        "energy_trading.api.composition.regulatory_intelligence_runtime.build_regulatory_intelligence_query_execution",
        spy,
    )
    openai_client = _FakeOpenAIClient()
    qdrant_client = _FakeQdrantClient()
    service = _build(openai_client, qdrant_client)
    assert len(calls) == 1
    payload = calls[0]
    assert isinstance(payload["document_query_embedding_port"], OpenAIDocumentQueryEmbeddingAdapter)
    assert isinstance(payload["document_vector_search_port"], QdrantDocumentVectorSearch)
    assert isinstance(
        payload["regulatory_constraint_inference_port"],
        OpenAIRegulatoryConstraintInferenceAdapter,
    )
    assert isinstance(service, RegulatoryIntelligenceQueryExecutionService)
    assert isinstance(
        service._query_preparation_service, DocumentVectorSearchQueryPreparationService
    )
    assert isinstance(service._regulatory_intelligence_agent, RegulatoryIntelligenceAgent)


def test_construction_does_not_invoke_provider_or_application_runtime() -> None:
    openai_client = _FakeOpenAIClient()
    qdrant_client = _FakeQdrantClient()
    _build(openai_client, qdrant_client)
    assert openai_client.embeddings.create_calls == []
    assert openai_client.responses.parse_calls == []
    assert qdrant_client.query_calls == []
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
    openai_client = AsyncOpenAI(api_key="sentinel-openai-api-key-chunk71", max_retries=0)
    qdrant_client = _FakeQdrantClient()
    try:
        service = build_regulatory_intelligence_provider_runtime(
            openai_client=openai_client,
            qdrant_client=cast(Any, qdrant_client),
            qdrant_vector_config=_config(),
            query_embedding_model=_QUERY_EMBEDDING_MODEL,
            constraint_inference_model=_CONSTRAINT_INFERENCE_MODEL,
        )
        embedder = service._query_preparation_service._document_query_embedding_port
        inference = service._regulatory_intelligence_agent._inference
        assert embedder._client is openai_client
        assert inference._client is openai_client
        assert openai_client.is_closed() is False
        assert qdrant_client.query_calls == []
        assert qdrant_client.close_calls == 0
    finally:
        await openai_client.close()
    assert openai_client.is_closed() is True


async def test_built_service_executes_through_real_application_composition() -> None:
    query_text = "  keep surrounding spaces  "
    chunk = _chunk()
    expected = constraint(constraint_id="composed-chunk71")
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
    assert isinstance(result, RegulatoryIntelligenceResult)
    assert len(result.constraints) == 1
    assert result.constraints[0].constraint_id == expected.constraint_id
    assert result.constraints[0].constraint_type == expected.constraint_type
    assert openai_client.close_calls == 0
    assert qdrant_client.close_calls == 0
