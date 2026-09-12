"""FastAPI document vector index lifespan exposes Chunk 91 on app.state."""

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
from energy_trading.api.composition.document_vector_index_lifespan import (
    build_document_vector_index_lifespan,
)
from energy_trading.api.composition.document_vector_index_loaded_runtime import (
    loaded_document_vector_index_runtime,
)
from tests.architecture.import_inspection import SRC_ROOT, imported_modules, imported_names
from tests.unit.api.helpers import make_test_settings

_LIFESPAN_MODULE = "energy_trading.api.composition.document_vector_index_lifespan"
_EXPLICIT_ENV_FILE = Path("sentinel-chunk92.env")
_SERVICE_ATTR = "document_vector_index_execution_service"


@dataclass
class _RecordingService:
    calls: list[str] = field(default_factory=list)

    async def execute(self, **_kwargs: object) -> None:
        self.calls.append("execute")

    async def embed(self, **_kwargs: object) -> None:
        self.calls.append("embed")

    async def index(self, **_kwargs: object) -> None:
        self.calls.append("index")


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
        f"{_LIFESPAN_MODULE}.loaded_document_vector_index_runtime",
        runtime_spy,
    )
    return runtime_spy


def _has_service(app: FastAPI) -> bool:
    return hasattr(app.state, _SERVICE_ATTR)


def test_factory_is_synchronous_keyword_only_and_matches_chunk_91_env_file() -> None:
    assert inspect.iscoroutinefunction(build_document_vector_index_lifespan) is False
    assert inspect.isasyncgenfunction(build_document_vector_index_lifespan) is False
    signature = inspect.signature(build_document_vector_index_lifespan)
    assert tuple(signature.parameters) == ("env_file",)
    parameter = signature.parameters["env_file"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    loaded_env = inspect.signature(loaded_document_vector_index_runtime).parameters["env_file"]
    assert parameter.annotation == loaded_env.annotation
    assert parameter.default == loaded_env.default
    assert parameter.default == ".env"
    with pytest.raises(TypeError):
        build_document_vector_index_lifespan(".env")  # type: ignore[misc]


def test_returned_callback_is_fastapi_lifespan_callable() -> None:
    callback = build_document_vector_index_lifespan(env_file=None)
    assert callable(callback)
    application = FastAPI()
    manager = callback(application)
    assert isinstance(manager, AbstractAsyncContextManager)


def test_factory_construction_does_not_enter_loaded_runtime_or_mutate_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spy = _patch_loaded_runtime(monkeypatch)
    application = FastAPI()
    callback = build_document_vector_index_lifespan(env_file=_EXPLICIT_ENV_FILE)
    assert spy.calls == []
    assert spy.events == []
    assert spy.active is False
    assert _has_service(application) is False
    manager = callback(application)
    assert spy.calls == []
    assert spy.events == []
    assert isinstance(manager, AbstractAsyncContextManager)
    assert _has_service(application) is False


async def test_explicit_env_file_is_forwarded_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spy = _patch_loaded_runtime(monkeypatch)
    callback = build_document_vector_index_lifespan(env_file=_EXPLICIT_ENV_FILE)
    async with callback(FastAPI()):
        pass
    assert spy.calls == [{"env_file": _EXPLICIT_ENV_FILE}]
    assert spy.calls[0]["env_file"] is _EXPLICIT_ENV_FILE


async def test_default_env_file_is_forwarded_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spy = _patch_loaded_runtime(monkeypatch)
    callback = build_document_vector_index_lifespan()
    async with callback(FastAPI()):
        pass
    assert spy.calls == [{"env_file": ".env"}]


async def test_none_env_file_is_forwarded_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spy = _patch_loaded_runtime(monkeypatch)
    callback = build_document_vector_index_lifespan(env_file=None)
    async with callback(FastAPI()):
        pass
    assert spy.calls == [{"env_file": None}]


async def test_loaded_runtime_is_entered_and_exited_exactly_once_and_stays_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spy = _patch_loaded_runtime(monkeypatch)
    callback = build_document_vector_index_lifespan(env_file=None)
    async with callback(FastAPI()):
        assert spy.events == ["enter"]
        assert spy.active is True
        assert len(spy.calls) == 1
    assert spy.events == ["enter", "exit"]
    assert spy.active is False
    assert len(spy.calls) == 1


async def test_exact_service_identity_is_exposed_during_lifespan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = object()
    spy = _patch_loaded_runtime(monkeypatch, _LoadedRuntimeSpy(service=service))
    application = FastAPI()
    callback = build_document_vector_index_lifespan(env_file=None)
    async with callback(application) as yielded:
        assert yielded is None
        assert application.state.document_vector_index_execution_service is service
        assert spy.active is True
    assert yielded is None


async def test_service_attribute_is_absent_before_and_after_lifespan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = object()
    spy = _patch_loaded_runtime(monkeypatch, _LoadedRuntimeSpy(service=service))
    application = FastAPI()
    callback = build_document_vector_index_lifespan(env_file=None)
    assert _has_service(application) is False
    async with callback(application):
        assert application.state.document_vector_index_execution_service is service
    assert _has_service(application) is False
    assert spy.events == ["enter", "exit"]


async def test_state_is_removed_before_loaded_runtime_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = object()
    spy = _LoadedRuntimeSpy(service=service)
    application = FastAPI()
    spy.owner = application
    _patch_loaded_runtime(monkeypatch, spy)
    callback = build_document_vector_index_lifespan(env_file=None)
    async with callback(application):
        assert spy.events == ["enter"]
        assert application.state.document_vector_index_execution_service is service
    assert spy.events == ["enter", "exit"]
    assert spy.state_present_on_exit is False
    assert _has_service(application) is False


async def test_exposed_service_is_not_invoked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _RecordingService()
    _patch_loaded_runtime(monkeypatch, _LoadedRuntimeSpy(service=service))
    application = FastAPI()
    callback = build_document_vector_index_lifespan(env_file=None)
    async with callback(application) as yielded:
        assert yielded is None
        assert application.state.document_vector_index_execution_service is service
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
    callback = build_document_vector_index_lifespan(env_file=None)
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
    callback = build_document_vector_index_lifespan(env_file=None)
    with pytest.raises(RuntimeError, match="lifespan-body-failed") as captured:
        async with callback(application):
            assert application.state.document_vector_index_execution_service is service
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
    callback = build_document_vector_index_lifespan(env_file=None)
    with pytest.raises(RuntimeError) as captured:
        async with callback(application):
            assert spy.active is True
            assert application.state.document_vector_index_execution_service is service
    assert captured.value is error
    assert spy.events == ["enter", "exit"]
    assert spy.active is False
    assert spy.state_present_on_exit is False
    assert _has_service(application) is False


def test_fastapi_lifespan_compatibility_exposes_service_during_active_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = object()
    spy = _patch_loaded_runtime(monkeypatch, _LoadedRuntimeSpy(service=service))
    callback = build_document_vector_index_lifespan(env_file=None)
    application = FastAPI(lifespan=callback)

    @application.get("/peek")
    async def peek(request: Request) -> dict[str, str]:
        assert spy.active is True
        exposed = request.app.state.document_vector_index_execution_service
        assert exposed is service
        return {"status": "ok"}

    assert _has_service(application) is False
    with TestClient(application) as client:
        assert spy.events == ["enter"]
        assert spy.active is True
        assert application.state.document_vector_index_execution_service is service
        response = client.get("/peek")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert spy.active is True
    assert spy.events == ["enter", "exit"]
    assert spy.active is False
    assert spy.calls == [{"env_file": None}]
    assert _has_service(application) is False


def test_create_app_does_not_import_or_enter_the_lifespan_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spy = _patch_loaded_runtime(monkeypatch)
    source = inspect.getsource(create_app)
    assert "build_document_vector_index_lifespan" not in source
    assert "loaded_document_vector_index_runtime" not in source
    application = create_app(make_test_settings())
    installed = application.router.lifespan_context
    try:
        installed_source = inspect.getsource(installed)
    except OSError:
        installed_source = ""
    assert "build_document_vector_index_lifespan" not in installed_source
    assert "loaded_document_vector_index_runtime" not in installed_source
    assert spy.calls == []
    assert spy.events == []
    assert spy.active is False
    assert _has_service(application) is False


def test_lifespan_module_does_not_import_the_app_factory() -> None:
    path = SRC_ROOT / "energy_trading/api/composition/document_vector_index_lifespan.py"
    names = imported_names(path)
    modules = imported_modules(path)
    assert "create_app" not in names
    assert "energy_trading.api.app" not in modules
    assert "energy_trading.api.routers" not in modules


def test_lifespan_module_does_not_call_lower_layers_or_execute() -> None:
    import energy_trading.api.composition.document_vector_index_lifespan as module

    source = inspect.getsource(module)
    assert "managed_document_vector_index_runtime" not in source
    assert "build_document_vector_index_configured_runtime" not in source
    assert "build_document_vector_index_provider_runtime" not in source
    assert "build_document_vector_index_execution" not in source
    assert "load_openai_settings" not in source
    assert "load_qdrant_settings" not in source
    assert "load_document_vector_index_runtime_settings" not in source
    assert "load_qdrant_document_vector_distance_settings" not in source
    assert "ensure_configured_document_vector_index_collection_ready" not in source
    assert "map_qdrant_document_vector_distance" not in source
    assert "create_openai_client" not in source
    assert "create_qdrant_client" not in source
    assert "AsyncOpenAI(" not in source
    assert "AsyncQdrantClient(" not in source
    assert "AsyncExitStack" not in source
    assert ".close(" not in source
    assert ".execute(" not in source
    assert ".embed(" not in source
    assert ".index(" not in source
    assert "app.state.document_vector_index_execution_service" in source
    assert "os.environ" not in source
    assert "getenv" not in source
    assert "dotenv" not in source
    assert "loaded_document_vector_index_runtime" in source
    assert "get_document_vector_index" not in source
    assert "Depends(" not in source
    assert "include_router" not in source
