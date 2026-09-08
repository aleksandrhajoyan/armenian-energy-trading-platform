"""FastAPI Regulatory Intelligence lifespan exposes Chunk 75 on app.state."""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from energy_trading.api.composition.regulatory_intelligence_lifespan import (
    build_regulatory_intelligence_lifespan,
)
from energy_trading.api.composition.regulatory_intelligence_loaded_runtime import (
    loaded_regulatory_intelligence_runtime,
)
from tests.architecture.import_inspection import SRC_ROOT, imported_modules, imported_names

_LIFESPAN_MODULE = "energy_trading.api.composition.regulatory_intelligence_lifespan"
_EXPLICIT_ENV_FILE = Path("sentinel-chunk76.env")
_SERVICE_ATTR = "regulatory_intelligence_query_execution_service"


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
    owner: FastAPI | None = None
    state_present_on_exit: bool | None = None

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
            if self.owner is not None:
                self.state_present_on_exit = hasattr(self.owner.state, _SERVICE_ATTR)
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


def _has_service(app: FastAPI) -> bool:
    return hasattr(app.state, _SERVICE_ATTR)


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


async def test_service_is_absent_before_lifespan_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_loaded_runtime(monkeypatch)
    application = FastAPI()
    callback = build_regulatory_intelligence_lifespan(env_file=None)
    assert _has_service(application) is False
    manager = callback(application)
    assert isinstance(manager, AbstractAsyncContextManager)
    assert _has_service(application) is False


async def test_exact_service_identity_is_exposed_during_lifespan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = object()
    spy = _patch_loaded_runtime(monkeypatch, _LoadedRuntimeSpy(service=service))
    application = FastAPI()
    callback = build_regulatory_intelligence_lifespan(env_file=None)
    async with callback(application) as yielded:
        assert yielded is None
        assert application.state.regulatory_intelligence_query_execution_service is service
        assert spy.active is True
    assert yielded is None


async def test_service_remains_available_for_the_full_yield_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = object()
    spy = _patch_loaded_runtime(monkeypatch, _LoadedRuntimeSpy(service=service))
    application = FastAPI()
    callback = build_regulatory_intelligence_lifespan(env_file=None)
    async with callback(application):
        assert spy.events == ["enter"]
        assert spy.active is True
        assert application.state.regulatory_intelligence_query_execution_service is service
        assert spy.active is True
        assert application.state.regulatory_intelligence_query_execution_service is service
        assert len(spy.calls) == 1
    assert spy.events == ["enter", "exit"]
    assert spy.active is False
    assert len(spy.calls) == 1


async def test_service_attribute_is_removed_after_normal_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = object()
    spy = _patch_loaded_runtime(monkeypatch, _LoadedRuntimeSpy(service=service))
    application = FastAPI()
    callback = build_regulatory_intelligence_lifespan(env_file=None)
    async with callback(application):
        assert application.state.regulatory_intelligence_query_execution_service is service
    assert _has_service(application) is False
    assert spy.events == ["enter", "exit"]


async def test_exposed_service_is_not_invoked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _RecordingService()
    _patch_loaded_runtime(monkeypatch, _LoadedRuntimeSpy(service=service))
    application = FastAPI()
    callback = build_regulatory_intelligence_lifespan(env_file=None)
    async with callback(application) as yielded:
        assert yielded is None
        assert application.state.regulatory_intelligence_query_execution_service is service
        assert service.calls == []
    assert yielded is None
    assert service.calls == []
    assert _has_service(application) is False


async def test_startup_failure_propagates_and_never_exposes_the_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = RuntimeError("loaded-runtime-entry-failed")
    spy = _patch_loaded_runtime(
        monkeypatch,
        _LoadedRuntimeSpy(service=object(), entry_error=error),
    )
    application = FastAPI()
    body_reached = False
    callback = build_regulatory_intelligence_lifespan(env_file=None)
    with pytest.raises(RuntimeError) as captured:
        async with callback(application):
            body_reached = True
    assert captured.value is error
    assert body_reached is False
    assert spy.events == ["enter-failed"]
    assert spy.active is False
    assert len(spy.calls) == 1
    assert _has_service(application) is False


async def test_body_exception_removes_state_exits_runtime_and_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = object()
    spy = _LoadedRuntimeSpy(service=service)
    application = FastAPI()
    spy.owner = application
    _patch_loaded_runtime(monkeypatch, spy)
    callback = build_regulatory_intelligence_lifespan(env_file=None)
    with pytest.raises(RuntimeError, match="lifespan-body-failed") as captured:
        async with callback(application):
            assert application.state.regulatory_intelligence_query_execution_service is service
            raise RuntimeError("lifespan-body-failed")
    assert type(captured.value) is RuntimeError
    assert str(captured.value) == "lifespan-body-failed"
    assert spy.events == ["enter", "exit"]
    assert spy.active is False
    assert spy.state_present_on_exit is False
    assert _has_service(application) is False


async def test_teardown_failure_removes_state_before_exit_error_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = RuntimeError("loaded-runtime-exit-failed")
    service = object()
    spy = _LoadedRuntimeSpy(service=service, exit_error=error)
    application = FastAPI()
    spy.owner = application
    _patch_loaded_runtime(monkeypatch, spy)
    callback = build_regulatory_intelligence_lifespan(env_file=None)
    with pytest.raises(RuntimeError) as captured:
        async with callback(application):
            assert spy.active is True
            assert application.state.regulatory_intelligence_query_execution_service is service
    assert captured.value is error
    assert spy.events == ["enter", "exit"]
    assert spy.active is False
    assert spy.state_present_on_exit is False
    assert _has_service(application) is False


async def test_state_exposure_is_isolated_per_application(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    services = [object(), object()]
    index = {"n": 0}

    @asynccontextmanager
    async def fake_loaded(**_kwargs: object) -> AsyncIterator[object]:
        service = services[index["n"]]
        index["n"] += 1
        yield service

    monkeypatch.setattr(
        f"{_LIFESPAN_MODULE}.loaded_regulatory_intelligence_runtime",
        fake_loaded,
    )
    callback = build_regulatory_intelligence_lifespan(env_file=None)
    app_a = FastAPI()
    app_b = FastAPI()
    assert _has_service(app_a) is False
    assert _has_service(app_b) is False
    async with callback(app_a):
        assert app_a.state.regulatory_intelligence_query_execution_service is services[0]
        assert _has_service(app_b) is False
        async with callback(app_b):
            assert app_a.state.regulatory_intelligence_query_execution_service is services[0]
            assert app_b.state.regulatory_intelligence_query_execution_service is services[1]
            assert services[0] is not services[1]
        assert _has_service(app_b) is False
        assert app_a.state.regulatory_intelligence_query_execution_service is services[0]
    assert _has_service(app_a) is False
    assert _has_service(app_b) is False


def test_fastapi_lifespan_compatibility_exposes_service_during_active_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = object()
    spy = _patch_loaded_runtime(monkeypatch, _LoadedRuntimeSpy(service=service))
    callback = build_regulatory_intelligence_lifespan(env_file=None)
    application = FastAPI(lifespan=callback)

    @application.get("/peek")
    async def peek(request: Request) -> dict[str, str]:
        assert spy.active is True
        exposed = request.app.state.regulatory_intelligence_query_execution_service
        assert exposed is service
        return {"status": "ok"}

    assert _has_service(application) is False
    with TestClient(application) as client:
        assert spy.events == ["enter"]
        assert spy.active is True
        assert application.state.regulatory_intelligence_query_execution_service is service
        response = client.get("/peek")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert spy.active is True
    assert spy.events == ["enter", "exit"]
    assert spy.active is False
    assert spy.calls == [{"env_file": None}]
    assert _has_service(application) is False


def test_lifespan_module_does_not_import_the_app_factory() -> None:
    path = SRC_ROOT / "energy_trading/api/composition/regulatory_intelligence_lifespan.py"
    names = imported_names(path)
    modules = imported_modules(path)
    assert "create_app" not in names
    assert "energy_trading.api.app" not in modules
    assert "energy_trading.api.routers" not in modules
