"""Settings-loaded Regulatory Intelligence runtime delegates to Chunk 74."""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from energy_trading.api.composition.regulatory_intelligence_loaded_runtime import (
    loaded_regulatory_intelligence_runtime,
)
from energy_trading.shared.config.openai import load_openai_settings
from energy_trading.shared.config.qdrant import load_qdrant_settings
from energy_trading.shared.config.regulatory_intelligence import (
    load_regulatory_intelligence_runtime_settings,
)

_LOADED_MODULE = "energy_trading.api.composition.regulatory_intelligence_loaded_runtime"
_EXPLICIT_ENV_FILE = Path("sentinel-chunk75.env")

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

    async def embed_query(self, **_kwargs: object) -> None:
        self.calls.append("embed_query")

    async def search(self, **_kwargs: object) -> None:
        self.calls.append("search")

    async def infer(self, **_kwargs: object) -> None:
        self.calls.append("infer")

    async def run(self, **_kwargs: object) -> None:
        self.calls.append("run")


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
    regulatory_settings: object | None = None,
    openai_error: BaseException | None = None,
    qdrant_error: BaseException | None = None,
    regulatory_error: BaseException | None = None,
    managed: _ManagedRuntimeSpy | None = None,
) -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
    _ManagedRuntimeSpy,
]:
    openai_calls: list[dict[str, object]] = []
    qdrant_calls: list[dict[str, object]] = []
    regulatory_calls: list[dict[str, object]] = []
    spy = managed or _ManagedRuntimeSpy(service=object())
    openai_result = object() if openai_settings is None else openai_settings
    qdrant_result = object() if qdrant_settings is None else qdrant_settings
    regulatory_result = object() if regulatory_settings is None else regulatory_settings

    def fake_openai(**kwargs: object) -> object:
        openai_calls.append(kwargs)
        if openai_error is not None:
            raise openai_error
        return openai_result

    def fake_qdrant(**kwargs: object) -> object:
        qdrant_calls.append(kwargs)
        if qdrant_error is not None:
            raise qdrant_error
        return qdrant_result

    def fake_regulatory(**kwargs: object) -> object:
        regulatory_calls.append(kwargs)
        if regulatory_error is not None:
            raise regulatory_error
        return regulatory_result

    monkeypatch.setattr(f"{_LOADED_MODULE}.load_openai_settings", fake_openai)
    monkeypatch.setattr(f"{_LOADED_MODULE}.load_qdrant_settings", fake_qdrant)
    monkeypatch.setattr(
        f"{_LOADED_MODULE}.load_regulatory_intelligence_runtime_settings",
        fake_regulatory,
    )
    monkeypatch.setattr(f"{_LOADED_MODULE}.managed_regulatory_intelligence_runtime", spy)
    return openai_calls, qdrant_calls, regulatory_calls, spy


def test_callable_is_async_context_manager_factory() -> None:
    assert inspect.iscoroutinefunction(loaded_regulatory_intelligence_runtime) is False
    assert inspect.isasyncgenfunction(loaded_regulatory_intelligence_runtime) is False
    manager = loaded_regulatory_intelligence_runtime(env_file=None)
    assert isinstance(manager, AbstractAsyncContextManager)


def test_signature_is_keyword_only_with_existing_env_file_contract() -> None:
    signature = inspect.signature(loaded_regulatory_intelligence_runtime)
    assert tuple(signature.parameters) == ("env_file",)
    parameter = signature.parameters["env_file"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    openai_env = inspect.signature(load_openai_settings).parameters["env_file"]
    qdrant_env = inspect.signature(load_qdrant_settings).parameters["env_file"]
    regulatory_env = inspect.signature(load_regulatory_intelligence_runtime_settings).parameters[
        "env_file"
    ]
    assert parameter.annotation == openai_env.annotation
    assert parameter.annotation == qdrant_env.annotation
    assert parameter.annotation == regulatory_env.annotation
    assert parameter.default == openai_env.default
    assert parameter.default == qdrant_env.default
    assert parameter.default == regulatory_env.default
    assert parameter.default == ".env"
    assert "openai_settings" not in signature.parameters
    assert "qdrant_settings" not in signature.parameters
    assert "regulatory_settings" not in signature.parameters
    assert "openai_client" not in signature.parameters
    assert "qdrant_client" not in signature.parameters
    assert "create_openai_client" not in signature.parameters
    assert "create_qdrant_client" not in signature.parameters


async def test_each_settings_loader_is_called_once_with_explicit_env_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    openai_calls, qdrant_calls, regulatory_calls, spy = _patch_loaded_runtime(monkeypatch)
    async with loaded_regulatory_intelligence_runtime(env_file=_EXPLICIT_ENV_FILE):
        pass
    assert openai_calls == [{"env_file": _EXPLICIT_ENV_FILE}]
    assert qdrant_calls == [{"env_file": _EXPLICIT_ENV_FILE}]
    assert regulatory_calls == [{"env_file": _EXPLICIT_ENV_FILE}]
    assert openai_calls[0]["env_file"] is _EXPLICIT_ENV_FILE
    assert qdrant_calls[0]["env_file"] is _EXPLICIT_ENV_FILE
    assert regulatory_calls[0]["env_file"] is _EXPLICIT_ENV_FILE
    assert len(spy.calls) == 1


async def test_default_env_file_is_forwarded_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    openai_calls, qdrant_calls, regulatory_calls, _spy = _patch_loaded_runtime(monkeypatch)
    async with loaded_regulatory_intelligence_runtime():
        pass
    assert openai_calls == [{"env_file": ".env"}]
    assert qdrant_calls == [{"env_file": ".env"}]
    assert regulatory_calls == [{"env_file": ".env"}]


async def test_none_env_file_is_forwarded_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    openai_calls, qdrant_calls, regulatory_calls, _spy = _patch_loaded_runtime(monkeypatch)
    async with loaded_regulatory_intelligence_runtime(env_file=None):
        pass
    assert openai_calls == [{"env_file": None}]
    assert qdrant_calls == [{"env_file": None}]
    assert regulatory_calls == [{"env_file": None}]


async def test_exact_settings_identity_is_forwarded_to_managed_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    openai_settings = object()
    qdrant_settings = object()
    regulatory_settings = object()
    _openai_calls, _qdrant_calls, _regulatory_calls, spy = _patch_loaded_runtime(
        monkeypatch,
        openai_settings=openai_settings,
        qdrant_settings=qdrant_settings,
        regulatory_settings=regulatory_settings,
    )
    async with loaded_regulatory_intelligence_runtime(env_file=None):
        pass
    assert len(spy.calls) == 1
    assert spy.calls[0]["openai_settings"] is openai_settings
    assert spy.calls[0]["qdrant_settings"] is qdrant_settings
    assert spy.calls[0]["regulatory_settings"] is regulatory_settings


async def test_yields_exact_managed_runtime_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = object()
    spy = _ManagedRuntimeSpy(service=sentinel)
    _patch_loaded_runtime(monkeypatch, managed=spy)
    async with loaded_regulatory_intelligence_runtime(env_file=None) as service:
        assert service is sentinel


async def test_context_entry_does_not_execute_query_or_provider_methods(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _RecordingService()
    spy = _ManagedRuntimeSpy(service=service)
    _patch_loaded_runtime(monkeypatch, managed=spy)
    async with loaded_regulatory_intelligence_runtime(env_file=None) as yielded:
        assert yielded is service
        assert service.calls == []
    assert service.calls == []
    assert spy.events == ["enter", "exit"]


async def test_managed_runtime_is_entered_and_exited_exactly_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spy = _ManagedRuntimeSpy(service=object())
    _patch_loaded_runtime(monkeypatch, managed=spy)
    async with loaded_regulatory_intelligence_runtime(env_file=None):
        assert spy.events == ["enter"]
    assert spy.events == ["enter", "exit"]
    assert len(spy.calls) == 1


async def test_consumer_exception_exits_inner_context_and_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spy = _ManagedRuntimeSpy(service=object())
    _patch_loaded_runtime(monkeypatch, managed=spy)
    with pytest.raises(RuntimeError, match="consumer-failed") as captured:
        async with loaded_regulatory_intelligence_runtime(env_file=None):
            raise RuntimeError("consumer-failed")
    assert type(captured.value) is RuntimeError
    assert str(captured.value) == "consumer-failed"
    assert spy.events == ["enter", "exit"]


async def test_openai_loader_failure_does_not_enter_managed_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = RuntimeError("openai-loader-failed")
    openai_calls, qdrant_calls, regulatory_calls, spy = _patch_loaded_runtime(
        monkeypatch,
        openai_error=error,
    )
    with pytest.raises(RuntimeError) as captured:
        async with loaded_regulatory_intelligence_runtime(env_file=None):
            raise AssertionError("context body must not run")
    assert captured.value is error
    assert openai_calls == [{"env_file": None}]
    assert qdrant_calls == []
    assert regulatory_calls == []
    assert spy.calls == []
    assert spy.events == []


async def test_qdrant_loader_failure_does_not_enter_managed_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = RuntimeError("qdrant-loader-failed")
    openai_calls, qdrant_calls, regulatory_calls, spy = _patch_loaded_runtime(
        monkeypatch,
        qdrant_error=error,
    )
    with pytest.raises(RuntimeError) as captured:
        async with loaded_regulatory_intelligence_runtime(env_file=None):
            raise AssertionError("context body must not run")
    assert captured.value is error
    assert openai_calls == [{"env_file": None}]
    assert qdrant_calls == [{"env_file": None}]
    assert regulatory_calls == []
    assert spy.calls == []
    assert spy.events == []


async def test_regulatory_loader_failure_does_not_enter_managed_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = RuntimeError("regulatory-loader-failed")
    openai_calls, qdrant_calls, regulatory_calls, spy = _patch_loaded_runtime(
        monkeypatch,
        regulatory_error=error,
    )
    with pytest.raises(RuntimeError) as captured:
        async with loaded_regulatory_intelligence_runtime(env_file=None):
            raise AssertionError("context body must not run")
    assert captured.value is error
    assert openai_calls == [{"env_file": None}]
    assert qdrant_calls == [{"env_file": None}]
    assert regulatory_calls == [{"env_file": None}]
    assert spy.calls == []
    assert spy.events == []


async def test_managed_runtime_entry_failure_propagates_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = RuntimeError("managed-entry-failed")
    spy = _ManagedRuntimeSpy(service=object(), entry_error=error)
    openai_calls, qdrant_calls, regulatory_calls, _ = _patch_loaded_runtime(
        monkeypatch,
        managed=spy,
    )
    with pytest.raises(RuntimeError) as captured:
        async with loaded_regulatory_intelligence_runtime(env_file=None):
            raise AssertionError("context body must not run")
    assert captured.value is error
    assert openai_calls == [{"env_file": None}]
    assert qdrant_calls == [{"env_file": None}]
    assert regulatory_calls == [{"env_file": None}]
    assert len(spy.calls) == 1
    assert spy.events == ["enter-failed"]
