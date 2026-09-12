"""Settings-loaded document vector index runtime delegates to Chunk 90."""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from energy_trading.api.composition.document_vector_index_loaded_runtime import (
    loaded_document_vector_index_runtime,
)
from energy_trading.shared.config.document_vector_index import (
    load_document_vector_index_runtime_settings,
)
from energy_trading.shared.config.openai import load_openai_settings
from energy_trading.shared.config.qdrant import (
    load_qdrant_document_vector_distance_settings,
    load_qdrant_settings,
)

_LOADED_MODULE = "energy_trading.api.composition.document_vector_index_loaded_runtime"
_EXPLICIT_ENV_FILE = Path("sentinel-chunk91.env")

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


@pytest.fixture(autouse=True)
def clear_loaded_runtime_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


@dataclass
class _RecordingService:
    calls: list[str] = field(default_factory=list)

    async def execute(self, **_kwargs: object) -> None:
        self.calls.append("execute")

    async def embed(self, **_kwargs: object) -> None:
        self.calls.append("embed")

    async def index(self, **_kwargs: object) -> None:
        self.calls.append("index")

    async def prepare(self, **_kwargs: object) -> None:
        self.calls.append("prepare")

    async def close(self) -> None:
        self.calls.append("close")


@dataclass
class _ManagedRuntimeSpy:
    service: object
    calls: list[dict[str, object]] = field(default_factory=list)
    events: list[str] = field(default_factory=list)
    entry_error: BaseException | None = None

    def __call__(self, **kwargs: object) -> AbstractAsyncContextManager[object]:
        self.calls.append(kwargs)
        return self._context()

    @asynccontextmanager
    async def _context(self) -> AsyncIterator[object]:
        if self.entry_error is not None:
            self.events.append("enter-failed")
            raise self.entry_error
        self.events.append("enter")
        try:
            yield self.service
        finally:
            self.events.append("exit")


def _patch_loaded_runtime(
    monkeypatch: pytest.MonkeyPatch,
    *,
    openai_settings: object | None = None,
    qdrant_settings: object | None = None,
    document_vector_index_settings: object | None = None,
    distance_settings: object | None = None,
    openai_error: BaseException | None = None,
    qdrant_error: BaseException | None = None,
    document_index_error: BaseException | None = None,
    distance_error: BaseException | None = None,
    managed: _ManagedRuntimeSpy | None = None,
) -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
    list[str],
    _ManagedRuntimeSpy,
]:
    openai_calls: list[dict[str, object]] = []
    qdrant_calls: list[dict[str, object]] = []
    document_index_calls: list[dict[str, object]] = []
    distance_calls: list[dict[str, object]] = []
    call_order: list[str] = []
    spy = managed or _ManagedRuntimeSpy(service=object())
    openai_result = object() if openai_settings is None else openai_settings
    qdrant_result = object() if qdrant_settings is None else qdrant_settings
    document_index_result = (
        object() if document_vector_index_settings is None else document_vector_index_settings
    )
    distance_result = object() if distance_settings is None else distance_settings

    def fake_openai(**kwargs: object) -> object:
        openai_calls.append(kwargs)
        call_order.append("openai")
        if openai_error is not None:
            raise openai_error
        return openai_result

    def fake_qdrant(**kwargs: object) -> object:
        qdrant_calls.append(kwargs)
        call_order.append("qdrant")
        if qdrant_error is not None:
            raise qdrant_error
        return qdrant_result

    def fake_document_index(**kwargs: object) -> object:
        document_index_calls.append(kwargs)
        call_order.append("document-index")
        if document_index_error is not None:
            raise document_index_error
        return document_index_result

    def fake_distance(**kwargs: object) -> object:
        distance_calls.append(kwargs)
        call_order.append("distance")
        if distance_error is not None:
            raise distance_error
        return distance_result

    monkeypatch.setattr(f"{_LOADED_MODULE}.load_openai_settings", fake_openai)
    monkeypatch.setattr(f"{_LOADED_MODULE}.load_qdrant_settings", fake_qdrant)
    monkeypatch.setattr(
        f"{_LOADED_MODULE}.load_document_vector_index_runtime_settings",
        fake_document_index,
    )
    monkeypatch.setattr(
        f"{_LOADED_MODULE}.load_qdrant_document_vector_distance_settings",
        fake_distance,
    )
    monkeypatch.setattr(f"{_LOADED_MODULE}.managed_document_vector_index_runtime", spy)
    return openai_calls, qdrant_calls, document_index_calls, distance_calls, call_order, spy


def test_callable_is_async_context_manager_factory() -> None:
    assert inspect.iscoroutinefunction(loaded_document_vector_index_runtime) is False
    assert inspect.isasyncgenfunction(loaded_document_vector_index_runtime) is False
    manager = loaded_document_vector_index_runtime(env_file=None)
    assert isinstance(manager, AbstractAsyncContextManager)


def test_signature_is_keyword_only_with_existing_env_file_contract() -> None:
    signature = inspect.signature(loaded_document_vector_index_runtime)
    assert tuple(signature.parameters) == ("env_file",)
    parameter = signature.parameters["env_file"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    openai_env = inspect.signature(load_openai_settings).parameters["env_file"]
    qdrant_env = inspect.signature(load_qdrant_settings).parameters["env_file"]
    document_index_env = inspect.signature(load_document_vector_index_runtime_settings).parameters[
        "env_file"
    ]
    distance_env = inspect.signature(load_qdrant_document_vector_distance_settings).parameters[
        "env_file"
    ]
    assert parameter.annotation == openai_env.annotation
    assert parameter.annotation == qdrant_env.annotation
    assert parameter.annotation == document_index_env.annotation
    assert parameter.annotation == distance_env.annotation
    assert parameter.default == openai_env.default
    assert parameter.default == qdrant_env.default
    assert parameter.default == document_index_env.default
    assert parameter.default == distance_env.default
    assert parameter.default == ".env"
    assert "openai_settings" not in signature.parameters
    assert "qdrant_settings" not in signature.parameters
    assert "document_vector_index_settings" not in signature.parameters
    assert "distance_settings" not in signature.parameters
    assert "openai_client" not in signature.parameters
    assert "qdrant_client" not in signature.parameters
    assert "create_openai_client" not in signature.parameters
    assert "create_qdrant_client" not in signature.parameters
    assert "load_openai_settings" not in signature.parameters
    assert "load_qdrant_settings" not in signature.parameters
    assert "load_document_vector_index_runtime_settings" not in signature.parameters
    assert "load_qdrant_document_vector_distance_settings" not in signature.parameters
    assert "ensure_configured_document_vector_index_collection_ready" not in signature.parameters


async def test_each_settings_loader_is_called_once_with_explicit_env_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    openai_calls, qdrant_calls, document_index_calls, distance_calls, call_order, spy = (
        _patch_loaded_runtime(monkeypatch)
    )
    async with loaded_document_vector_index_runtime(env_file=_EXPLICIT_ENV_FILE):
        pass
    assert openai_calls == [{"env_file": _EXPLICIT_ENV_FILE}]
    assert qdrant_calls == [{"env_file": _EXPLICIT_ENV_FILE}]
    assert document_index_calls == [{"env_file": _EXPLICIT_ENV_FILE}]
    assert distance_calls == [{"env_file": _EXPLICIT_ENV_FILE}]
    assert openai_calls[0]["env_file"] is _EXPLICIT_ENV_FILE
    assert qdrant_calls[0]["env_file"] is _EXPLICIT_ENV_FILE
    assert document_index_calls[0]["env_file"] is _EXPLICIT_ENV_FILE
    assert distance_calls[0]["env_file"] is _EXPLICIT_ENV_FILE
    assert call_order == ["openai", "qdrant", "document-index", "distance"]
    assert len(spy.calls) == 1


async def test_default_env_file_is_forwarded_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    openai_calls, qdrant_calls, document_index_calls, distance_calls, _, _spy = (
        _patch_loaded_runtime(monkeypatch)
    )
    async with loaded_document_vector_index_runtime():
        pass
    assert openai_calls == [{"env_file": ".env"}]
    assert qdrant_calls == [{"env_file": ".env"}]
    assert document_index_calls == [{"env_file": ".env"}]
    assert distance_calls == [{"env_file": ".env"}]


async def test_none_env_file_is_forwarded_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    openai_calls, qdrant_calls, document_index_calls, distance_calls, _, _spy = (
        _patch_loaded_runtime(monkeypatch)
    )
    async with loaded_document_vector_index_runtime(env_file=None):
        pass
    assert openai_calls == [{"env_file": None}]
    assert qdrant_calls == [{"env_file": None}]
    assert document_index_calls == [{"env_file": None}]
    assert distance_calls == [{"env_file": None}]


async def test_exact_settings_identity_is_forwarded_to_managed_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    openai_settings = object()
    qdrant_settings = object()
    document_vector_index_settings = object()
    distance_settings = object()
    _openai_calls, _qdrant_calls, _document_index_calls, _distance_calls, _order, spy = (
        _patch_loaded_runtime(
            monkeypatch,
            openai_settings=openai_settings,
            qdrant_settings=qdrant_settings,
            document_vector_index_settings=document_vector_index_settings,
            distance_settings=distance_settings,
        )
    )
    async with loaded_document_vector_index_runtime(env_file=None):
        pass
    assert len(spy.calls) == 1
    assert spy.calls[0]["openai_settings"] is openai_settings
    assert spy.calls[0]["qdrant_settings"] is qdrant_settings
    assert spy.calls[0]["document_vector_index_settings"] is document_vector_index_settings
    assert spy.calls[0]["distance_settings"] is distance_settings


async def test_yields_exact_managed_runtime_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = object()
    spy = _ManagedRuntimeSpy(service=sentinel)
    _patch_loaded_runtime(monkeypatch, managed=spy)
    async with loaded_document_vector_index_runtime(env_file=None) as service:
        assert service is sentinel


async def test_context_entry_does_not_execute_index_or_provider_methods(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _RecordingService()
    spy = _ManagedRuntimeSpy(service=service)
    _patch_loaded_runtime(monkeypatch, managed=spy)
    async with loaded_document_vector_index_runtime(env_file=None) as yielded:
        assert yielded is service
        assert service.calls == []
    assert service.calls == []
    assert spy.events == ["enter", "exit"]


async def test_managed_runtime_is_entered_and_exited_exactly_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spy = _ManagedRuntimeSpy(service=object())
    _patch_loaded_runtime(monkeypatch, managed=spy)
    async with loaded_document_vector_index_runtime(env_file=None):
        assert spy.events == ["enter"]
    assert spy.events == ["enter", "exit"]
    assert len(spy.calls) == 1


async def test_consumer_exception_exits_inner_context_and_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spy = _ManagedRuntimeSpy(service=object())
    _patch_loaded_runtime(monkeypatch, managed=spy)
    with pytest.raises(RuntimeError, match="consumer-failed") as captured:
        async with loaded_document_vector_index_runtime(env_file=None):
            raise RuntimeError("consumer-failed")
    assert type(captured.value) is RuntimeError
    assert str(captured.value) == "consumer-failed"
    assert spy.events == ["enter", "exit"]


async def test_openai_loader_failure_does_not_enter_managed_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = RuntimeError("openai-loader-failed")
    openai_calls, qdrant_calls, document_index_calls, distance_calls, call_order, spy = (
        _patch_loaded_runtime(
            monkeypatch,
            openai_error=error,
        )
    )
    with pytest.raises(RuntimeError) as captured:
        async with loaded_document_vector_index_runtime(env_file=None):
            raise AssertionError("context body must not run")
    assert captured.value is error
    assert openai_calls == [{"env_file": None}]
    assert qdrant_calls == []
    assert document_index_calls == []
    assert distance_calls == []
    assert call_order == ["openai"]
    assert spy.calls == []
    assert spy.events == []


async def test_qdrant_loader_failure_does_not_enter_managed_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = RuntimeError("qdrant-loader-failed")
    openai_calls, qdrant_calls, document_index_calls, distance_calls, call_order, spy = (
        _patch_loaded_runtime(
            monkeypatch,
            qdrant_error=error,
        )
    )
    with pytest.raises(RuntimeError) as captured:
        async with loaded_document_vector_index_runtime(env_file=None):
            raise AssertionError("context body must not run")
    assert captured.value is error
    assert openai_calls == [{"env_file": None}]
    assert qdrant_calls == [{"env_file": None}]
    assert document_index_calls == []
    assert distance_calls == []
    assert call_order == ["openai", "qdrant"]
    assert spy.calls == []
    assert spy.events == []


async def test_document_index_loader_failure_does_not_enter_managed_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = RuntimeError("document-index-loader-failed")
    openai_calls, qdrant_calls, document_index_calls, distance_calls, call_order, spy = (
        _patch_loaded_runtime(
            monkeypatch,
            document_index_error=error,
        )
    )
    with pytest.raises(RuntimeError) as captured:
        async with loaded_document_vector_index_runtime(env_file=None):
            raise AssertionError("context body must not run")
    assert captured.value is error
    assert openai_calls == [{"env_file": None}]
    assert qdrant_calls == [{"env_file": None}]
    assert document_index_calls == [{"env_file": None}]
    assert distance_calls == []
    assert call_order == ["openai", "qdrant", "document-index"]
    assert spy.calls == []
    assert spy.events == []


async def test_distance_loader_failure_does_not_enter_managed_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = RuntimeError("distance-loader-failed")
    openai_calls, qdrant_calls, document_index_calls, distance_calls, call_order, spy = (
        _patch_loaded_runtime(
            monkeypatch,
            distance_error=error,
        )
    )
    with pytest.raises(RuntimeError) as captured:
        async with loaded_document_vector_index_runtime(env_file=None):
            raise AssertionError("context body must not run")
    assert captured.value is error
    assert openai_calls == [{"env_file": None}]
    assert qdrant_calls == [{"env_file": None}]
    assert document_index_calls == [{"env_file": None}]
    assert distance_calls == [{"env_file": None}]
    assert call_order == ["openai", "qdrant", "document-index", "distance"]
    assert spy.calls == []
    assert spy.events == []


async def test_managed_runtime_entry_failure_propagates_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = RuntimeError("managed-entry-failed")
    spy = _ManagedRuntimeSpy(service=object(), entry_error=error)
    openai_calls, qdrant_calls, document_index_calls, distance_calls, call_order, _ = (
        _patch_loaded_runtime(
            monkeypatch,
            managed=spy,
        )
    )
    with pytest.raises(RuntimeError) as captured:
        async with loaded_document_vector_index_runtime(env_file=None):
            raise AssertionError("context body must not run")
    assert captured.value is error
    assert openai_calls == [{"env_file": None}]
    assert qdrant_calls == [{"env_file": None}]
    assert document_index_calls == [{"env_file": None}]
    assert distance_calls == [{"env_file": None}]
    assert call_order == ["openai", "qdrant", "document-index", "distance"]
    assert len(spy.calls) == 1
    assert spy.events == ["enter-failed"]


def test_module_does_not_construct_clients_or_own_cleanup() -> None:
    import energy_trading.api.composition.document_vector_index_loaded_runtime as module

    source = inspect.getsource(module)
    assert "create_openai_client" not in source
    assert "create_qdrant_client" not in source
    assert "AsyncOpenAI(" not in source
    assert "AsyncQdrantClient(" not in source
    assert "AsyncExitStack" not in source
    assert ".close(" not in source
    assert ".execute(" not in source
    assert ".embed(" not in source
    assert ".index(" not in source
    assert "os.environ" not in source
    assert "getenv" not in source
    assert "dotenv" not in source
    assert "ensure_configured_document_vector_index_collection_ready" not in source
    assert "map_qdrant_document_vector_distance" not in source
    assert "ensure_qdrant_document_collection_ready" not in source
    assert "create_qdrant_document_collection" not in source
    assert "verify_qdrant_document_collection_ready" not in source
    assert not hasattr(module, "openai_client")
    assert not hasattr(module, "qdrant_client")
    assert not hasattr(module, "create_openai_client")
    assert not hasattr(module, "create_qdrant_client")
    assert not hasattr(module, "AsyncOpenAI")
    assert not hasattr(module, "AsyncQdrantClient")
    assert not hasattr(module, "ensure_configured_document_vector_index_collection_ready")
    assert not hasattr(module, "map_qdrant_document_vector_distance")
