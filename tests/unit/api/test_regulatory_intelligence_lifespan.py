"""FastAPI Regulatory Intelligence lifespan owns Chunk 75 lifetime without exposing it."""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from energy_trading.api.app import create_app
from energy_trading.api.composition.regulatory_intelligence_lifespan import (
    build_regulatory_intelligence_lifespan,
)
from energy_trading.api.composition.regulatory_intelligence_loaded_runtime import (
    loaded_regulatory_intelligence_runtime,
)
from tests.unit.api.helpers import make_test_settings

_LIFESPAN_MODULE = "energy_trading.api.composition.regulatory_intelligence_lifespan"
_EXPLICIT_ENV_FILE = Path("sentinel-chunk76.env")


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
class _LoadedRuntimeSpy:
    service: object
    calls: list[dict[str, object]] = field(default_factory=list)
    events: list[str] = field(default_factory=list)
    active: bool = False
    entry_error: BaseException | None = None
    exit_error: BaseException | None = None

    def __call__(self, **kwargs: object) -> AbstractAsyncContextManager[object]:
        self.calls.append(kwargs)
        return self._context()

    @asynccontextmanager
    async def _context(self) -> AsyncIterator[object]:
        if self.entry_error is not None:
            self.events.append("enter-failed")
            raise self.entry_error
        self.events.append("enter")
        self.active = True
        try:
            yield self.service
        finally:
            self.active = False
            self.events.append("exit")
            if self.exit_error is not None:
                raise self.exit_error


def _patch_loaded_runtime(
    monkeypatch: pytest.MonkeyPatch,
    spy: _LoadedRuntimeSpy | None = None,
) -> _LoadedRuntimeSpy:
    runtime_spy = spy or _LoadedRuntimeSpy(service=object())
    monkeypatch.setattr(
        f"{_LIFESPAN_MODULE}.loaded_regulatory_intelligence_runtime",
        runtime_spy,
    )
    return runtime_spy


def _state_values(owner: object) -> list[object]:
    state = getattr(owner, "_state", {})
    if isinstance(state, dict):
        return list(state.values())
    return []


def test_factory_is_synchronous_keyword_only_and_matches_chunk_75_env_file() -> None:
    assert inspect.iscoroutinefunction(build_regulatory_intelligence_lifespan) is False
    assert inspect.isasyncgenfunction(build_regulatory_intelligence_lifespan) is False
    signature = inspect.signature(build_regulatory_intelligence_lifespan)
    assert tuple(signature.parameters) == ("env_file",)
    parameter = signature.parameters["env_file"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    loaded_env = inspect.signature(loaded_regulatory_intelligence_runtime).parameters["env_file"]
    assert parameter.annotation == loaded_env.annotation
    assert parameter.default == loaded_env.default
    assert parameter.default == ".env"
    with pytest.raises(TypeError):
        build_regulatory_intelligence_lifespan(".env")  # type: ignore[misc]


def test_returned_callback_is_fastapi_lifespan_callable() -> None:
    callback = build_regulatory_intelligence_lifespan(env_file=None)
    assert callable(callback)
    application = FastAPI()
    manager = callback(application)
    assert isinstance(manager, AbstractAsyncContextManager)


def test_factory_construction_does_not_enter_loaded_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spy = _patch_loaded_runtime(monkeypatch)
    callback = build_regulatory_intelligence_lifespan(env_file=_EXPLICIT_ENV_FILE)
    assert spy.calls == []
    assert spy.events == []
    assert spy.active is False
    manager = callback(FastAPI())
    assert spy.calls == []
    assert spy.events == []
    assert isinstance(manager, AbstractAsyncContextManager)


async def test_explicit_env_file_is_forwarded_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spy = _patch_loaded_runtime(monkeypatch)
    callback = build_regulatory_intelligence_lifespan(env_file=_EXPLICIT_ENV_FILE)
    async with callback(FastAPI()):
        pass
    assert spy.calls == [{"env_file": _EXPLICIT_ENV_FILE}]
    assert spy.calls[0]["env_file"] is _EXPLICIT_ENV_FILE


async def test_default_env_file_is_forwarded_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spy = _patch_loaded_runtime(monkeypatch)
    callback = build_regulatory_intelligence_lifespan()
    async with callback(FastAPI()):
        pass
    assert spy.calls == [{"env_file": ".env"}]


async def test_none_env_file_is_forwarded_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spy = _patch_loaded_runtime(monkeypatch)
    callback = build_regulatory_intelligence_lifespan(env_file=None)
    async with callback(FastAPI()):
        pass
    assert spy.calls == [{"env_file": None}]


async def test_loaded_runtime_is_entered_and_exited_exactly_once_and_stays_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spy = _patch_loaded_runtime(monkeypatch)
    callback = build_regulatory_intelligence_lifespan(env_file=None)
    async with callback(FastAPI()):
        assert spy.events == ["enter"]
        assert spy.active is True
        assert len(spy.calls) == 1
    assert spy.events == ["enter", "exit"]
    assert spy.active is False
    assert len(spy.calls) == 1


async def test_yielded_service_is_not_exposed_or_invoked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _RecordingService()
    spy = _patch_loaded_runtime(monkeypatch, _LoadedRuntimeSpy(service=service))
    application = FastAPI()
    callback = build_regulatory_intelligence_lifespan(env_file=None)
    async with callback(application) as yielded:
        assert yielded is None
        assert spy.active is True
        assert service not in _state_values(application.state)
        public_state = [
            getattr(application.state, name)
            for name in dir(application.state)
            if not name.startswith("_")
        ]
        assert service not in public_state
        assert service.calls == []
    assert yielded is None
    assert service.calls == []
    assert spy.events == ["enter", "exit"]


async def test_startup_failure_propagates_and_skips_lifespan_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = RuntimeError("loaded-runtime-entry-failed")
    spy = _patch_loaded_runtime(
        monkeypatch,
        _LoadedRuntimeSpy(service=object(), entry_error=error),
    )
    body_reached = False
    callback = build_regulatory_intelligence_lifespan(env_file=None)
    with pytest.raises(RuntimeError) as captured:
        async with callback(FastAPI()):
            body_reached = True
    assert captured.value is error
    assert body_reached is False
    assert spy.events == ["enter-failed"]
    assert spy.active is False
    assert len(spy.calls) == 1


async def test_body_exception_exits_loaded_runtime_and_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spy = _patch_loaded_runtime(monkeypatch)
    callback = build_regulatory_intelligence_lifespan(env_file=None)
    with pytest.raises(RuntimeError, match="lifespan-body-failed") as captured:
        async with callback(FastAPI()):
            raise RuntimeError("lifespan-body-failed")
    assert type(captured.value) is RuntimeError
    assert str(captured.value) == "lifespan-body-failed"
    assert spy.events == ["enter", "exit"]
    assert spy.active is False


async def test_teardown_failure_propagates_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = RuntimeError("loaded-runtime-exit-failed")
    spy = _patch_loaded_runtime(
        monkeypatch,
        _LoadedRuntimeSpy(service=object(), exit_error=error),
    )
    callback = build_regulatory_intelligence_lifespan(env_file=None)
    with pytest.raises(RuntimeError) as captured:
        async with callback(FastAPI()):
            assert spy.active is True
    assert captured.value is error
    assert spy.events == ["enter", "exit"]
    assert spy.active is False


def test_fastapi_lifespan_compatibility_without_modifying_create_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = object()
    spy = _patch_loaded_runtime(monkeypatch, _LoadedRuntimeSpy(service=service))
    callback = build_regulatory_intelligence_lifespan(env_file=None)
    application = FastAPI(lifespan=callback)

    @application.get("/peek")
    async def peek(request: Request) -> dict[str, str]:
        assert spy.active is True
        assert service not in _state_values(request.app.state)
        assert service not in _state_values(request.state)
        return {"status": "ok"}

    with TestClient(application) as client:
        assert spy.events == ["enter"]
        assert spy.active is True
        response = client.get("/peek")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert spy.active is True
    assert spy.events == ["enter", "exit"]
    assert spy.active is False
    assert spy.calls == [{"env_file": None}]


def test_create_app_remains_unwired_to_the_lifespan_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spy = _patch_loaded_runtime(monkeypatch)
    source = inspect.getsource(create_app)
    assert "build_regulatory_intelligence_lifespan" not in source
    assert "loaded_regulatory_intelligence_runtime" not in source
    application = create_app(make_test_settings())
    installed = application.router.lifespan_context
    try:
        installed_source = inspect.getsource(installed)
    except OSError:
        installed_source = ""
    assert "build_regulatory_intelligence_lifespan" not in installed_source
    assert "loaded_regulatory_intelligence_runtime" not in installed_source
    assert spy.calls == []
    assert spy.events == []
    assert spy.active is False
