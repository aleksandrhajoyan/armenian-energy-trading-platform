"""Managed document vector index runtime owns provider-client lifetime."""

from __future__ import annotations

import inspect
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field

import pytest
from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient

from energy_trading.api.composition.document_vector_index_configured_runtime import (
    build_document_vector_index_configured_runtime,
)
from energy_trading.api.composition.document_vector_index_execution import (
    build_document_vector_index_execution,
)
from energy_trading.api.composition.document_vector_index_managed_runtime import (
    managed_document_vector_index_runtime,
)
from energy_trading.api.composition.document_vector_index_runtime import (
    build_document_vector_index_provider_runtime,
)
from energy_trading.application.errors import DependencyUnavailableError, InvalidRequestError
from energy_trading.application.orchestration.document_vector_index_execution import (
    DocumentVectorIndexExecutionService,
)
from energy_trading.infrastructure.embeddings.openai_document_embedding import (
    OpenAIDocumentEmbeddingAdapter,
)
from energy_trading.infrastructure.vector_store.qdrant.document_vector import (
    QdrantDocumentVectorIndex,
)
from energy_trading.shared.config.document_vector_index import (
    DocumentVectorIndexRuntimeSettings,
)
from energy_trading.shared.config.openai import OpenAISettings
from energy_trading.shared.config.qdrant import (
    QdrantDocumentVectorDistance,
    QdrantDocumentVectorDistanceSettings,
    QdrantSettings,
)

_DOCUMENT_EMBEDDING_MODEL = "sentinel-document-embedding-model-chunk90"
_COLLECTION_NAME = "sentinel-document-index-collection-chunk90"
_VECTOR_SIZE = 3
_OPENAI_API_KEY = "sentinel-openai-api-key-chunk90"

_ENV_KEYS = (
    "ENERGY_OPENAI_API_KEY",
    "QDRANT_HOST",
    "QDRANT_PORT",
    "QDRANT_HTTPS",
    "QDRANT_API_KEY",
    "QDRANT_TIMEOUT_SECONDS",
    "ENERGY_DOCUMENT_INDEX_DOCUMENT_EMBEDDING_MODEL",
    "ENERGY_DOCUMENT_INDEX_QDRANT_COLLECTION_NAME",
    "ENERGY_DOCUMENT_INDEX_QDRANT_VECTOR_SIZE",
    "QDRANT_DOCUMENT_VECTOR_DISTANCE",
)

_MANAGED_MODULE = "energy_trading.api.composition.document_vector_index_managed_runtime"


@pytest.fixture(autouse=True)
def clear_managed_runtime_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


@dataclass
class _FakeEmbeddings:
    create_calls: list[dict[str, object]] = field(default_factory=list)

    async def create(self, **kwargs: object) -> object:
        self.create_calls.append(kwargs)
        raise AssertionError("embeddings.create must not be called")


@dataclass
class _FakeOpenAIClient:
    close_order: list[str]
    embeddings: _FakeEmbeddings = field(default_factory=_FakeEmbeddings)
    close_error: BaseException | None = None

    async def close(self) -> None:
        self.close_order.append("openai")
        if self.close_error is not None:
            raise self.close_error


@dataclass
class _FakeQdrantClient:
    close_order: list[str]
    upsert_calls: list[dict[str, object]] = field(default_factory=list)
    retrieve_calls: list[dict[str, object]] = field(default_factory=list)
    close_error: BaseException | None = None

    async def upsert(self, **kwargs: object) -> object:
        self.upsert_calls.append(dict(kwargs))
        raise AssertionError("qdrant upsert must not be called")

    async def retrieve(self, **kwargs: object) -> object:
        self.retrieve_calls.append(dict(kwargs))
        raise AssertionError("qdrant retrieve must not be called")

    async def close(self) -> None:
        self.close_order.append("qdrant")
        if self.close_error is not None:
            raise self.close_error


def _openai_settings() -> OpenAISettings:
    return OpenAISettings(_env_file=None, api_key=_OPENAI_API_KEY)


def _qdrant_settings() -> QdrantSettings:
    return QdrantSettings(_env_file=None, host="qdrant.example.invalid")


def _document_vector_index_settings() -> DocumentVectorIndexRuntimeSettings:
    return DocumentVectorIndexRuntimeSettings(
        _env_file=None,
        document_embedding_model=_DOCUMENT_EMBEDDING_MODEL,
        qdrant_collection_name=_COLLECTION_NAME,
        qdrant_vector_size=_VECTOR_SIZE,
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
    document_vector_index_settings: DocumentVectorIndexRuntimeSettings | None = None,
    distance_settings: QdrantDocumentVectorDistanceSettings | None = None,
) -> AbstractAsyncContextManager[DocumentVectorIndexExecutionService]:
    return managed_document_vector_index_runtime(
        openai_settings=_openai_settings() if openai_settings is None else openai_settings,
        qdrant_settings=_qdrant_settings() if qdrant_settings is None else qdrant_settings,
        document_vector_index_settings=(
            _document_vector_index_settings()
            if document_vector_index_settings is None
            else document_vector_index_settings
        ),
        distance_settings=_distance_settings() if distance_settings is None else distance_settings,
    )


def _patch_factories(
    monkeypatch: pytest.MonkeyPatch,
    *,
    openai_client: _FakeOpenAIClient | None = None,
    qdrant_client: _FakeQdrantClient | None = None,
    openai_error: BaseException | None = None,
    qdrant_error: BaseException | None = None,
    ensure_error: BaseException | None = None,
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
    ensure_calls: list[dict[str, object]] = []
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

    async def fake_ensure(**kwargs: object) -> None:
        ensure_calls.append(kwargs)
        call_order.append("ensure")
        if ensure_error is not None:
            raise ensure_error

    monkeypatch.setattr(f"{_MANAGED_MODULE}.create_openai_client", fake_openai)
    monkeypatch.setattr(f"{_MANAGED_MODULE}.create_qdrant_client", fake_qdrant)
    monkeypatch.setattr(
        f"{_MANAGED_MODULE}.ensure_configured_document_vector_index_collection_ready",
        fake_ensure,
    )
    return (
        openai_calls,
        qdrant_calls,
        close_order,
        created_openai,
        created_qdrant,
        ensure_calls,
        call_order,
    )


def test_pinned_clients_expose_async_close() -> None:
    assert inspect.iscoroutinefunction(AsyncOpenAI.close) is True
    assert inspect.iscoroutinefunction(AsyncQdrantClient.close) is True
    assert inspect.iscoroutinefunction(getattr(AsyncOpenAI, "aclose", lambda: None)) is False
    assert inspect.iscoroutinefunction(getattr(AsyncQdrantClient, "aclose", lambda: None)) is False


def test_callable_is_async_context_manager_factory() -> None:
    assert inspect.iscoroutinefunction(managed_document_vector_index_runtime) is False
    assert inspect.isasyncgenfunction(managed_document_vector_index_runtime) is False
    manager = _managed_runtime()
    assert isinstance(manager, AbstractAsyncContextManager)


def test_signature_is_keyword_only_with_exact_settings() -> None:
    signature = inspect.signature(managed_document_vector_index_runtime)
    assert tuple(signature.parameters) == (
        "openai_settings",
        "qdrant_settings",
        "document_vector_index_settings",
        "distance_settings",
    )
    for name in signature.parameters:
        parameter = signature.parameters[name]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty
    assert signature.parameters["openai_settings"].annotation is OpenAISettings
    assert signature.parameters["qdrant_settings"].annotation is QdrantSettings
    assert (
        signature.parameters["document_vector_index_settings"].annotation
        is DocumentVectorIndexRuntimeSettings
    )
    assert (
        signature.parameters["distance_settings"].annotation is QdrantDocumentVectorDistanceSettings
    )
    assert "env_file" not in signature.parameters
    assert "api_key" not in signature.parameters
    assert "openai_client" not in signature.parameters
    assert "qdrant_client" not in signature.parameters
    assert "document_embedding_model" not in signature.parameters
    assert "load_openai_settings" not in signature.parameters
    assert "load_qdrant_settings" not in signature.parameters
    assert "load_document_vector_index_runtime_settings" not in signature.parameters
    assert "load_qdrant_document_vector_distance_settings" not in signature.parameters
    assert "create_openai_client" not in signature.parameters
    assert "create_qdrant_client" not in signature.parameters


async def test_factories_and_chunk_89_receive_exact_identities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    close_order: list[str] = []
    openai_client = _FakeOpenAIClient(close_order=close_order)
    qdrant_client = _FakeQdrantClient(close_order=close_order)
    openai_settings = _openai_settings()
    qdrant_settings = _qdrant_settings()
    document_vector_index_settings = _document_vector_index_settings()
    distance_settings = _distance_settings()
    openai_calls, qdrant_calls, _, _, _, ensure_calls, call_order = _patch_factories(
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

    monkeypatch.setattr(f"{_MANAGED_MODULE}.build_document_vector_index_configured_runtime", spy)

    async with _managed_runtime(
        openai_settings=openai_settings,
        qdrant_settings=qdrant_settings,
        document_vector_index_settings=document_vector_index_settings,
        distance_settings=distance_settings,
    ) as service:
        call_order.append("yield")
        assert service is sentinel
        assert openai_calls == [openai_settings]
        assert qdrant_calls == [qdrant_settings]
        assert len(ensure_calls) == 1
        assert ensure_calls[0]["client"] is qdrant_client
        assert ensure_calls[0]["runtime_settings"] is document_vector_index_settings
        assert ensure_calls[0]["distance_settings"] is distance_settings
        assert len(builder_calls) == 1
        assert builder_calls[0]["openai_client"] is openai_client
        assert builder_calls[0]["qdrant_client"] is qdrant_client
        assert builder_calls[0]["settings"] is document_vector_index_settings
        assert close_order == []
        assert openai_client.embeddings.create_calls == []
        assert qdrant_client.upsert_calls == []
        assert qdrant_client.retrieve_calls == []

    assert call_order == ["openai", "qdrant", "ensure", "configured", "yield"]
    assert close_order == ["qdrant", "openai"]
    assert len(openai_calls) == 1
    assert len(qdrant_calls) == 1
    assert len(ensure_calls) == 1
    assert len(builder_calls) == 1


async def test_construction_does_not_call_settings_loaders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_factories(monkeypatch)
    monkeypatch.setattr(
        f"{_MANAGED_MODULE}.build_document_vector_index_configured_runtime",
        lambda **_kwargs: object(),
    )

    def fail_openai_settings(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("load_openai_settings must not be called")

    def fail_qdrant_settings(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("load_qdrant_settings must not be called")

    def fail_document_index_settings(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("load_document_vector_index_runtime_settings must not be called")

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
        "energy_trading.shared.config.document_vector_index.load_document_vector_index_runtime_settings",
        fail_document_index_settings,
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
    openai_calls, qdrant_calls, close_order, _, _, ensure_calls, _ = _patch_factories(
        monkeypatch,
        openai_error=RuntimeError("openai-factory-failed"),
    )
    builder_calls: list[object] = []
    monkeypatch.setattr(
        f"{_MANAGED_MODULE}.build_document_vector_index_configured_runtime",
        lambda **_kwargs: builder_calls.append("called") or object(),
    )
    with pytest.raises(RuntimeError, match="openai-factory-failed"):
        async with _managed_runtime():
            raise AssertionError("context body must not run")
    assert openai_calls
    assert qdrant_calls == []
    assert ensure_calls == []
    assert builder_calls == []
    assert close_order == []


async def test_qdrant_factory_failure_closes_openai_and_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    close_order: list[str] = []
    openai_client = _FakeOpenAIClient(close_order=close_order)
    _, _, _, _, _, ensure_calls, _ = _patch_factories(
        monkeypatch,
        openai_client=openai_client,
        qdrant_error=RuntimeError("qdrant-factory-failed"),
    )
    builder_calls: list[object] = []
    monkeypatch.setattr(
        f"{_MANAGED_MODULE}.build_document_vector_index_configured_runtime",
        lambda **_kwargs: builder_calls.append("called") or object(),
    )
    with pytest.raises(RuntimeError, match="qdrant-factory-failed"):
        async with _managed_runtime():
            raise AssertionError("context body must not run")
    assert close_order == ["openai"]
    assert ensure_calls == []
    assert builder_calls == []


async def test_collection_ensure_failure_closes_both_clients_and_skips_configured_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    close_order: list[str] = []
    openai_client = _FakeOpenAIClient(close_order=close_order)
    qdrant_client = _FakeQdrantClient(close_order=close_order)
    sentinel = DependencyUnavailableError("sentinel-ensure-chunk111")
    _, _, _, _, _, ensure_calls, call_order = _patch_factories(
        monkeypatch,
        openai_client=openai_client,
        qdrant_client=qdrant_client,
        ensure_error=sentinel,
    )
    builder_calls: list[object] = []
    monkeypatch.setattr(
        f"{_MANAGED_MODULE}.build_document_vector_index_configured_runtime",
        lambda **_kwargs: builder_calls.append("called") or object(),
    )
    with pytest.raises(DependencyUnavailableError) as captured:
        async with _managed_runtime():
            raise AssertionError("context body must not run")
    assert captured.value is sentinel
    assert captured.value.__cause__ is None
    assert len(ensure_calls) == 1
    assert ensure_calls[0]["client"] is qdrant_client
    assert builder_calls == []
    assert call_order == ["openai", "qdrant", "ensure"]
    assert close_order == ["qdrant", "openai"]


async def test_invalid_request_from_ensure_propagates_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    close_order: list[str] = []
    openai_client = _FakeOpenAIClient(close_order=close_order)
    qdrant_client = _FakeQdrantClient(close_order=close_order)
    sentinel = InvalidRequestError("sentinel-invalid-ensure-chunk111")
    _patch_factories(
        monkeypatch,
        openai_client=openai_client,
        qdrant_client=qdrant_client,
        ensure_error=sentinel,
    )
    builder_calls: list[object] = []
    monkeypatch.setattr(
        f"{_MANAGED_MODULE}.build_document_vector_index_configured_runtime",
        lambda **_kwargs: builder_calls.append("called") or object(),
    )
    with pytest.raises(InvalidRequestError) as captured:
        async with _managed_runtime():
            raise AssertionError("context body must not run")
    assert captured.value is sentinel
    assert builder_calls == []
    assert close_order == ["qdrant", "openai"]


async def test_chunk_89_failure_closes_both_clients_and_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    close_order: list[str] = []
    openai_client = _FakeOpenAIClient(close_order=close_order)
    qdrant_client = _FakeQdrantClient(close_order=close_order)
    _, _, _, _, _, ensure_calls, _ = _patch_factories(
        monkeypatch,
        openai_client=openai_client,
        qdrant_client=qdrant_client,
    )

    def fail_builder(**_kwargs: object) -> None:
        raise RuntimeError("chunk89-failed")

    monkeypatch.setattr(
        f"{_MANAGED_MODULE}.build_document_vector_index_configured_runtime",
        fail_builder,
    )
    with pytest.raises(RuntimeError, match="chunk89-failed"):
        async with _managed_runtime():
            raise AssertionError("context body must not run")
    assert len(ensure_calls) == 1
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
        f"{_MANAGED_MODULE}.build_document_vector_index_configured_runtime",
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
        f"{_MANAGED_MODULE}.build_document_vector_index_configured_runtime",
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
    ensure_calls: list[dict[str, object]] = []

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

    async def fake_ensure(**kwargs: object) -> None:
        ensure_calls.append(kwargs)

    monkeypatch.setattr(f"{_MANAGED_MODULE}.create_openai_client", fake_openai)
    monkeypatch.setattr(f"{_MANAGED_MODULE}.create_qdrant_client", fake_qdrant)
    monkeypatch.setattr(
        f"{_MANAGED_MODULE}.ensure_configured_document_vector_index_collection_ready",
        fake_ensure,
    )
    monkeypatch.setattr(
        f"{_MANAGED_MODULE}.build_document_vector_index_configured_runtime",
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
    assert ensure_calls[0]["client"] is qdrant_clients[0]
    assert ensure_calls[1]["client"] is qdrant_clients[1]
    assert close_orders[0] == ["qdrant", "openai"]
    assert close_orders[1] == ["qdrant", "openai"]


def test_module_does_not_construct_clients_or_keep_globals() -> None:
    import energy_trading.api.composition.document_vector_index_managed_runtime as module

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
    assert hasattr(module, "ensure_configured_document_vector_index_collection_ready")


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
        f"{_MANAGED_MODULE}.build_document_vector_index_configured_runtime",
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


async def test_managed_runtime_composes_real_chunk_89_87_86_stack(
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
    async with _managed_runtime() as service:
        assert isinstance(service, DocumentVectorIndexExecutionService)
        embedder = service._preparation_service._document_embedding_port
        index = service._document_vector_index_port
        assert isinstance(embedder, OpenAIDocumentEmbeddingAdapter)
        assert isinstance(index, QdrantDocumentVectorIndex)
        assert embedder._client is openai_client
        assert embedder._model == _DOCUMENT_EMBEDDING_MODEL
        assert index._client is qdrant_client
        assert index._config.collection_name == _COLLECTION_NAME
        assert index._config.vector_size == _VECTOR_SIZE
        assert close_order == []
        assert openai_client.embeddings.create_calls == []
        assert qdrant_client.upsert_calls == []
        assert qdrant_client.retrieve_calls == []
    assert close_order == ["qdrant", "openai"]
    assert inspect.isfunction(build_document_vector_index_configured_runtime)
    assert inspect.isfunction(build_document_vector_index_provider_runtime)
    assert inspect.isfunction(build_document_vector_index_execution)
