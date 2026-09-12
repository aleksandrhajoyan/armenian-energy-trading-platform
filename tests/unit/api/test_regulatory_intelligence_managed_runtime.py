"""Managed Regulatory Intelligence runtime owns provider-client lifetime."""

from __future__ import annotations

import inspect
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from types import SimpleNamespace
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
from energy_trading.api.composition.regulatory_intelligence_managed_runtime import (
    managed_regulatory_intelligence_runtime,
)
from energy_trading.api.composition.regulatory_intelligence_runtime import (
    build_regulatory_intelligence_provider_runtime,
)
from energy_trading.application.errors import DependencyUnavailableError, InvalidRequestError
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
    QdrantDocumentVectorSearch,
    _point_uuid,
)
from energy_trading.shared.config.openai import OpenAISettings
from energy_trading.shared.config.qdrant import (
    QdrantDocumentVectorDistance,
    QdrantDocumentVectorDistanceSettings,
    QdrantSettings,
)
from energy_trading.shared.config.regulatory_intelligence import (
    RegulatoryIntelligenceRuntimeSettings,
)
from tests.unit.domain._factories import constraint

_QUERY_EMBEDDING_MODEL = "sentinel-query-embedding-model-chunk74"
_CONSTRAINT_INFERENCE_MODEL = "sentinel-constraint-inference-model-chunk74"
_SENTINEL_VECTOR: tuple[float, ...] = (0.125, -0.25, 0.5)
_COLLECTION_NAME = "sentinel-regulatory-collection-chunk74"
_FINGERPRINT = "a" * 64
_OPENAI_API_KEY = "sentinel-openai-api-key-chunk74"

_ENV_KEYS = (
    "ENERGY_OPENAI_API_KEY",
    "QDRANT_HOST",
    "QDRANT_PORT",
    "QDRANT_HTTPS",
    "QDRANT_API_KEY",
    "QDRANT_TIMEOUT_SECONDS",
    "ENERGY_REGULATORY_QUERY_EMBEDDING_MODEL",
    "ENERGY_REGULATORY_CONSTRAINT_INFERENCE_MODEL",
    "ENERGY_REGULATORY_QDRANT_COLLECTION_NAME",
    "ENERGY_REGULATORY_QDRANT_VECTOR_SIZE",
    "QDRANT_DOCUMENT_VECTOR_DISTANCE",
)

_MANAGED_MODULE = "energy_trading.api.composition.regulatory_intelligence_managed_runtime"


@pytest.fixture(autouse=True)
def clear_managed_runtime_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _ENV_KEYS:
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
    close_order: list[str]
    embeddings: _FakeEmbeddings = field(default_factory=_FakeEmbeddings)
    responses: _FakeResponses = field(default_factory=_FakeResponses)
    close_error: BaseException | None = None

    async def close(self) -> None:
        self.close_order.append("openai")
        if self.close_error is not None:
            raise self.close_error


@dataclass
class _FakeQdrantRecord:
    id: UUID
    payload: dict[str, object]


@dataclass
class _FakeQueryResponse:
    points: list[_FakeQdrantRecord]


@dataclass
class _FakeQdrantClient:
    close_order: list[str]
    query_calls: list[dict[str, object]] = field(default_factory=list)
    query_hits: list[_FakeQdrantRecord] = field(default_factory=list)
    close_error: BaseException | None = None

    async def query_points(self, **kwargs: object) -> _FakeQueryResponse:
        self.query_calls.append(dict(kwargs))
        return _FakeQueryResponse(points=list(self.query_hits))

    async def close(self) -> None:
        self.close_order.append("qdrant")
        if self.close_error is not None:
            raise self.close_error


def _openai_settings() -> OpenAISettings:
    return OpenAISettings(_env_file=None, api_key=_OPENAI_API_KEY)


def _qdrant_settings() -> QdrantSettings:
    return QdrantSettings(_env_file=None, host="qdrant.example.invalid")


def _regulatory_settings() -> RegulatoryIntelligenceRuntimeSettings:
    return RegulatoryIntelligenceRuntimeSettings(
        _env_file=None,
        query_embedding_model=_QUERY_EMBEDDING_MODEL,
        constraint_inference_model=_CONSTRAINT_INFERENCE_MODEL,
        qdrant_collection_name=_COLLECTION_NAME,
        qdrant_vector_size=len(_SENTINEL_VECTOR),
    )


def _distance_settings() -> QdrantDocumentVectorDistanceSettings:
    return QdrantDocumentVectorDistanceSettings(
        _env_file=None,
        document_vector_distance=QdrantDocumentVectorDistance.COSINE,
    )


def _managed_runtime(
    *,
    openai_settings: OpenAISettings | None = None,
    qdrant_settings: QdrantSettings | None = None,
    regulatory_settings: RegulatoryIntelligenceRuntimeSettings | None = None,
    distance_settings: QdrantDocumentVectorDistanceSettings | None = None,
) -> AbstractAsyncContextManager[RegulatoryIntelligenceQueryExecutionService]:
    return managed_regulatory_intelligence_runtime(
        openai_settings=_openai_settings() if openai_settings is None else openai_settings,
        qdrant_settings=_qdrant_settings() if qdrant_settings is None else qdrant_settings,
        regulatory_settings=(
            _regulatory_settings() if regulatory_settings is None else regulatory_settings
        ),
        distance_settings=_distance_settings() if distance_settings is None else distance_settings,
    )


def _chunk() -> ExtractedDocumentChunk:
    return ExtractedDocumentChunk(
        document_id="doc-chunk74",
        chunk_id="chunk-chunk74",
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


def _patch_factories(
    monkeypatch: pytest.MonkeyPatch,
    *,
    openai_client: _FakeOpenAIClient | None = None,
    qdrant_client: _FakeQdrantClient | None = None,
    openai_error: BaseException | None = None,
    qdrant_error: BaseException | None = None,
    verify_error: BaseException | None = None,
) -> tuple[
    list[object],
    list[object],
    list[str],
    _FakeOpenAIClient | None,
    _FakeQdrantClient | None,
    list[dict[str, object]],
    list[str],
]:
    openai_calls: list[object] = []
    qdrant_calls: list[object] = []
    verify_calls: list[dict[str, object]] = []
    call_order: list[str] = []
    close_order: list[str] = []
    created_openai = openai_client
    created_qdrant = qdrant_client

    def fake_openai(settings: OpenAISettings) -> _FakeOpenAIClient:
        openai_calls.append(settings)
        call_order.append("openai")
        if openai_error is not None:
            raise openai_error
        client = created_openai or _FakeOpenAIClient(close_order=close_order)
        return client

    def fake_qdrant(settings: QdrantSettings) -> _FakeQdrantClient:
        qdrant_calls.append(settings)
        call_order.append("qdrant")
        if qdrant_error is not None:
            raise qdrant_error
        client = created_qdrant or _FakeQdrantClient(close_order=close_order)
        return client

    async def fake_verify(**kwargs: object) -> None:
        verify_calls.append(kwargs)
        call_order.append("verify")
        if verify_error is not None:
            raise verify_error

    monkeypatch.setattr(f"{_MANAGED_MODULE}.create_openai_client", fake_openai)
    monkeypatch.setattr(f"{_MANAGED_MODULE}.create_qdrant_client", fake_qdrant)
    monkeypatch.setattr(
        f"{_MANAGED_MODULE}.verify_configured_regulatory_intelligence_collection_ready",
        fake_verify,
    )
    return (
        openai_calls,
        qdrant_calls,
        close_order,
        created_openai,
        created_qdrant,
        verify_calls,
        call_order,
    )


def test_pinned_clients_expose_async_close() -> None:
    assert inspect.iscoroutinefunction(AsyncOpenAI.close) is True
    assert inspect.iscoroutinefunction(AsyncQdrantClient.close) is True
    assert inspect.iscoroutinefunction(getattr(AsyncOpenAI, "aclose", lambda: None)) is False
    assert inspect.iscoroutinefunction(getattr(AsyncQdrantClient, "aclose", lambda: None)) is False


def test_callable_is_async_context_manager_factory() -> None:
    assert inspect.iscoroutinefunction(managed_regulatory_intelligence_runtime) is False
    assert inspect.isasyncgenfunction(managed_regulatory_intelligence_runtime) is False
    manager = _managed_runtime()
    assert isinstance(manager, AbstractAsyncContextManager)


def test_signature_is_keyword_only_with_exact_settings() -> None:
    signature = inspect.signature(managed_regulatory_intelligence_runtime)
    assert tuple(signature.parameters) == (
        "openai_settings",
        "qdrant_settings",
        "regulatory_settings",
        "distance_settings",
    )
    for name in signature.parameters:
        parameter = signature.parameters[name]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty
    assert signature.parameters["openai_settings"].annotation is OpenAISettings
    assert signature.parameters["qdrant_settings"].annotation is QdrantSettings
    assert (
        signature.parameters["regulatory_settings"].annotation
        is RegulatoryIntelligenceRuntimeSettings
    )
    assert (
        signature.parameters["distance_settings"].annotation is QdrantDocumentVectorDistanceSettings
    )
    assert "env_file" not in signature.parameters
    assert "api_key" not in signature.parameters
    assert "openai_client" not in signature.parameters
    assert "qdrant_client" not in signature.parameters
    assert "query_embedding_model" not in signature.parameters
    assert "load_openai_settings" not in signature.parameters
    assert "load_qdrant_settings" not in signature.parameters
    assert "load_regulatory_intelligence_runtime_settings" not in signature.parameters
    assert "load_qdrant_document_vector_distance_settings" not in signature.parameters
    assert "create_openai_client" not in signature.parameters
    assert "create_qdrant_client" not in signature.parameters


async def test_factories_and_chunk_73_receive_exact_identities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    close_order: list[str] = []
    openai_client = _FakeOpenAIClient(close_order=close_order)
    qdrant_client = _FakeQdrantClient(close_order=close_order)
    openai_settings = _openai_settings()
    qdrant_settings = _qdrant_settings()
    regulatory_settings = _regulatory_settings()
    distance_settings = _distance_settings()
    openai_calls, qdrant_calls, _, _, _, verify_calls, call_order = _patch_factories(
        monkeypatch,
        openai_client=openai_client,
        qdrant_client=qdrant_client,
    )
    builder_calls: list[dict[str, object]] = []
    sentinel = object()

    def spy(**kwargs: object) -> object:
        call_order.append("configured")
        builder_calls.append(kwargs)
        return sentinel

    monkeypatch.setattr(f"{_MANAGED_MODULE}.build_regulatory_intelligence_configured_runtime", spy)

    async with _managed_runtime(
        openai_settings=openai_settings,
        qdrant_settings=qdrant_settings,
        regulatory_settings=regulatory_settings,
        distance_settings=distance_settings,
    ) as service:
        call_order.append("yield")
        assert service is sentinel
        assert openai_calls == [openai_settings]
        assert qdrant_calls == [qdrant_settings]
        assert len(verify_calls) == 1
        assert verify_calls[0]["client"] is qdrant_client
        assert verify_calls[0]["runtime_settings"] is regulatory_settings
        assert verify_calls[0]["distance_settings"] is distance_settings
        assert len(builder_calls) == 1
        assert builder_calls[0]["openai_client"] is openai_client
        assert builder_calls[0]["qdrant_client"] is qdrant_client
        assert builder_calls[0]["settings"] is regulatory_settings
        assert close_order == []
        assert openai_client.embeddings.create_calls == []
        assert openai_client.responses.parse_calls == []
        assert qdrant_client.query_calls == []

    assert call_order == ["openai", "qdrant", "verify", "configured", "yield"]
    assert close_order == ["qdrant", "openai"]
    assert len(openai_calls) == 1
    assert len(qdrant_calls) == 1
    assert len(verify_calls) == 1
    assert len(builder_calls) == 1


async def test_construction_does_not_call_settings_loaders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_factories(monkeypatch)
    monkeypatch.setattr(
        f"{_MANAGED_MODULE}.build_regulatory_intelligence_configured_runtime",
        lambda **_kwargs: object(),
    )

    def fail_openai_settings(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("load_openai_settings must not be called")

    def fail_qdrant_settings(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("load_qdrant_settings must not be called")

    def fail_regulatory_settings(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("load_regulatory_intelligence_runtime_settings must not be called")

    def fail_distance_settings(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("load_qdrant_document_vector_distance_settings must not be called")

    monkeypatch.setattr(
        "energy_trading.shared.config.openai.load_openai_settings",
        fail_openai_settings,
    )
    monkeypatch.setattr(
        "energy_trading.shared.config.qdrant.load_qdrant_settings",
        fail_qdrant_settings,
    )
    monkeypatch.setattr(
        "energy_trading.shared.config.regulatory_intelligence.load_regulatory_intelligence_runtime_settings",
        fail_regulatory_settings,
    )
    monkeypatch.setattr(
        "energy_trading.shared.config.qdrant.load_qdrant_document_vector_distance_settings",
        fail_distance_settings,
    )
    async with _managed_runtime():
        pass


async def test_openai_factory_failure_short_circuits_and_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    openai_calls, qdrant_calls, close_order, _, _, verify_calls, _ = _patch_factories(
        monkeypatch,
        openai_error=RuntimeError("openai-factory-failed"),
    )
    builder_calls: list[object] = []
    monkeypatch.setattr(
        f"{_MANAGED_MODULE}.build_regulatory_intelligence_configured_runtime",
        lambda **_kwargs: builder_calls.append("called") or object(),
    )
    with pytest.raises(RuntimeError, match="openai-factory-failed"):
        async with _managed_runtime():
            raise AssertionError("context body must not run")
    assert openai_calls
    assert qdrant_calls == []
    assert verify_calls == []
    assert builder_calls == []
    assert close_order == []


async def test_qdrant_factory_failure_closes_openai_and_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    close_order: list[str] = []
    openai_client = _FakeOpenAIClient(close_order=close_order)
    _, _, _, _, _, verify_calls, _ = _patch_factories(
        monkeypatch,
        openai_client=openai_client,
        qdrant_error=RuntimeError("qdrant-factory-failed"),
    )
    builder_calls: list[object] = []
    monkeypatch.setattr(
        f"{_MANAGED_MODULE}.build_regulatory_intelligence_configured_runtime",
        lambda **_kwargs: builder_calls.append("called") or object(),
    )
    with pytest.raises(RuntimeError, match="qdrant-factory-failed"):
        async with _managed_runtime():
            raise AssertionError("context body must not run")
    assert close_order == ["openai"]
    assert verify_calls == []
    assert builder_calls == []


async def test_collection_verify_failure_closes_both_clients_and_skips_configured_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    close_order: list[str] = []
    openai_client = _FakeOpenAIClient(close_order=close_order)
    qdrant_client = _FakeQdrantClient(close_order=close_order)
    sentinel = DependencyUnavailableError("sentinel-verify-chunk113")
    _, _, _, _, _, verify_calls, call_order = _patch_factories(
        monkeypatch,
        openai_client=openai_client,
        qdrant_client=qdrant_client,
        verify_error=sentinel,
    )
    builder_calls: list[object] = []
    monkeypatch.setattr(
        f"{_MANAGED_MODULE}.build_regulatory_intelligence_configured_runtime",
        lambda **_kwargs: builder_calls.append("called") or object(),
    )
    with pytest.raises(DependencyUnavailableError) as captured:
        async with _managed_runtime():
            raise AssertionError("context body must not run")
    assert captured.value is sentinel
    assert captured.value.__cause__ is None
    assert len(verify_calls) == 1
    assert verify_calls[0]["client"] is qdrant_client
    assert builder_calls == []
    assert call_order == ["openai", "qdrant", "verify"]
    assert close_order == ["qdrant", "openai"]


async def test_invalid_request_from_verify_propagates_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    close_order: list[str] = []
    openai_client = _FakeOpenAIClient(close_order=close_order)
    qdrant_client = _FakeQdrantClient(close_order=close_order)
    sentinel = InvalidRequestError("sentinel-invalid-verify-chunk113")
    _patch_factories(
        monkeypatch,
        openai_client=openai_client,
        qdrant_client=qdrant_client,
        verify_error=sentinel,
    )
    builder_calls: list[object] = []
    monkeypatch.setattr(
        f"{_MANAGED_MODULE}.build_regulatory_intelligence_configured_runtime",
        lambda **_kwargs: builder_calls.append("called") or object(),
    )
    with pytest.raises(InvalidRequestError) as captured:
        async with _managed_runtime():
            raise AssertionError("context body must not run")
    assert captured.value is sentinel
    assert builder_calls == []
    assert close_order == ["qdrant", "openai"]


async def test_chunk_73_failure_closes_both_clients_and_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    close_order: list[str] = []
    openai_client = _FakeOpenAIClient(close_order=close_order)
    qdrant_client = _FakeQdrantClient(close_order=close_order)
    _, _, _, _, _, verify_calls, _ = _patch_factories(
        monkeypatch,
        openai_client=openai_client,
        qdrant_client=qdrant_client,
    )

    def fail_builder(**_kwargs: object) -> None:
        raise RuntimeError("chunk73-failed")

    monkeypatch.setattr(
        f"{_MANAGED_MODULE}.build_regulatory_intelligence_configured_runtime",
        fail_builder,
    )
    with pytest.raises(RuntimeError, match="chunk73-failed"):
        async with _managed_runtime():
            raise AssertionError("context body must not run")
    assert len(verify_calls) == 1
    assert close_order == ["qdrant", "openai"]


async def test_consumer_exception_closes_both_clients_and_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    close_order: list[str] = []
    openai_client = _FakeOpenAIClient(close_order=close_order)
    qdrant_client = _FakeQdrantClient(close_order=close_order)
    _patch_factories(
        monkeypatch,
        openai_client=openai_client,
        qdrant_client=qdrant_client,
    )
    monkeypatch.setattr(
        f"{_MANAGED_MODULE}.build_regulatory_intelligence_configured_runtime",
        lambda **_kwargs: object(),
    )
    with pytest.raises(RuntimeError, match="consumer-failed"):
        async with _managed_runtime():
            raise RuntimeError("consumer-failed")
    assert close_order == ["qdrant", "openai"]


async def test_qdrant_close_failure_still_closes_openai_and_is_not_suppressed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    close_order: list[str] = []
    openai_client = _FakeOpenAIClient(close_order=close_order)
    qdrant_client = _FakeQdrantClient(
        close_order=close_order,
        close_error=RuntimeError("qdrant-close-failed"),
    )
    _patch_factories(
        monkeypatch,
        openai_client=openai_client,
        qdrant_client=qdrant_client,
    )
    monkeypatch.setattr(
        f"{_MANAGED_MODULE}.build_regulatory_intelligence_configured_runtime",
        lambda **_kwargs: object(),
    )
    with pytest.raises(RuntimeError, match="qdrant-close-failed"):
        async with _managed_runtime():
            pass
    assert close_order == ["qdrant", "openai"]


async def test_repeated_entries_create_fresh_factory_clients(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    openai_clients: list[_FakeOpenAIClient] = []
    qdrant_clients: list[_FakeQdrantClient] = []
    close_orders: list[list[str]] = []
    verify_calls: list[dict[str, object]] = []

    def fake_openai(_settings: OpenAISettings) -> _FakeOpenAIClient:
        close_order: list[str] = []
        close_orders.append(close_order)
        client = _FakeOpenAIClient(close_order=close_order)
        openai_clients.append(client)
        return client

    def fake_qdrant(_settings: QdrantSettings) -> _FakeQdrantClient:
        client = _FakeQdrantClient(close_order=close_orders[-1])
        qdrant_clients.append(client)
        return client

    async def fake_verify(**kwargs: object) -> None:
        verify_calls.append(kwargs)

    monkeypatch.setattr(f"{_MANAGED_MODULE}.create_openai_client", fake_openai)
    monkeypatch.setattr(f"{_MANAGED_MODULE}.create_qdrant_client", fake_qdrant)
    monkeypatch.setattr(
        f"{_MANAGED_MODULE}.verify_configured_regulatory_intelligence_collection_ready",
        fake_verify,
    )
    monkeypatch.setattr(
        f"{_MANAGED_MODULE}.build_regulatory_intelligence_configured_runtime",
        lambda **_kwargs: object(),
    )
    async with _managed_runtime():
        pass
    async with _managed_runtime():
        pass
    assert len(openai_clients) == 2
    assert len(qdrant_clients) == 2
    assert openai_clients[0] is not openai_clients[1]
    assert qdrant_clients[0] is not qdrant_clients[1]
    assert verify_calls[0]["client"] is qdrant_clients[0]
    assert verify_calls[1]["client"] is qdrant_clients[1]
    assert close_orders[0] == ["qdrant", "openai"]
    assert close_orders[1] == ["qdrant", "openai"]


def test_module_does_not_construct_clients_or_keep_globals() -> None:
    import energy_trading.api.composition.regulatory_intelligence_managed_runtime as module

    source = inspect.getsource(module)
    assert "AsyncOpenAI(" not in source
    assert "AsyncQdrantClient(" not in source
    assert "map_qdrant_document_vector_distance" not in source
    assert "ensure_qdrant_document_collection_ready" not in source
    assert "create_qdrant_document_collection" not in source
    assert "verify_qdrant_document_collection_ready" not in source
    assert not hasattr(module, "openai_client")
    assert not hasattr(module, "qdrant_client")
    assert not hasattr(module, "CLIENT")
    assert not hasattr(module, "AsyncOpenAI")
    assert not hasattr(module, "AsyncQdrantClient")
    assert not hasattr(module, "map_qdrant_document_vector_distance")
    assert not hasattr(module, "ensure_qdrant_document_collection_ready")
    assert not hasattr(module, "create_qdrant_document_collection")
    assert not hasattr(module, "verify_qdrant_document_collection_ready")
    assert hasattr(module, "verify_configured_regulatory_intelligence_collection_ready")


async def test_managed_runtime_does_not_call_create_verify_map_or_chunk_108(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_map(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("map_qdrant_document_vector_distance must not be called")

    def fail_ensure(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("ensure_qdrant_document_collection_ready must not be called")

    def fail_create(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("create_qdrant_document_collection must not be called")

    def fail_verify(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("verify_qdrant_document_collection_ready must not be called")

    _patch_factories(monkeypatch)
    monkeypatch.setattr(
        f"{_MANAGED_MODULE}.build_regulatory_intelligence_configured_runtime",
        lambda **_kwargs: object(),
    )
    monkeypatch.setattr(
        "energy_trading.api.composition.qdrant_document_vector_distance.map_qdrant_document_vector_distance",
        fail_map,
    )
    monkeypatch.setattr(
        "energy_trading.infrastructure.vector_store.qdrant.collection_ensure.ensure_qdrant_document_collection_ready",
        fail_ensure,
    )
    monkeypatch.setattr(
        "energy_trading.infrastructure.vector_store.qdrant.collection_creation.create_qdrant_document_collection",
        fail_create,
    )
    monkeypatch.setattr(
        "energy_trading.infrastructure.vector_store.qdrant.collection_readiness.verify_qdrant_document_collection_ready",
        fail_verify,
    )
    async with _managed_runtime():
        pass


async def test_managed_runtime_composes_real_chunk_73_71_67_stack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    close_order: list[str] = []
    chunk = _chunk()
    expected = constraint(constraint_id="composed-chunk74")
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
        close_order=close_order,
        embeddings=_FakeEmbeddings(
            response=SimpleNamespace(data=[SimpleNamespace(embedding=list(_SENTINEL_VECTOR))])
        ),
        responses=_FakeResponses(response=SimpleNamespace(output_parsed=envelope)),
    )
    qdrant_client = _FakeQdrantClient(
        close_order=close_order,
        query_hits=[_search_hit(chunk)],
    )
    _patch_factories(
        monkeypatch,
        openai_client=openai_client,
        qdrant_client=qdrant_client,
    )
    query_text = "  keep surrounding spaces  "
    async with _managed_runtime() as service:
        assert isinstance(service, RegulatoryIntelligenceQueryExecutionService)
        embedder = service._query_preparation_service._document_query_embedding_port
        inference = service._regulatory_intelligence_agent._inference
        search = service._regulatory_intelligence_agent._search
        assert isinstance(embedder, OpenAIDocumentQueryEmbeddingAdapter)
        assert isinstance(inference, OpenAIRegulatoryConstraintInferenceAdapter)
        assert isinstance(search, QdrantDocumentVectorSearch)
        assert embedder._client is openai_client
        assert inference._client is openai_client
        assert search._client is qdrant_client
        assert close_order == []
        result = await service.execute(query_text=query_text, limit=4)
        assert result.constraints[0].constraint_id == expected.constraint_id
        assert openai_client.embeddings.create_calls[0]["model"] == _QUERY_EMBEDDING_MODEL
        assert qdrant_client.query_calls[0]["collection_name"] == _COLLECTION_NAME
        assert openai_client.responses.parse_calls[0]["model"] == _CONSTRAINT_INFERENCE_MODEL
    assert close_order == ["qdrant", "openai"]
    assert inspect.isfunction(build_regulatory_intelligence_configured_runtime)
    assert inspect.isfunction(build_regulatory_intelligence_provider_runtime)
    assert inspect.isfunction(build_regulatory_intelligence_query_execution)
