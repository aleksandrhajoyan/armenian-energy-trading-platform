"""Production FastAPI lifespan nests the two published child lifespan boundaries."""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from fastapi import FastAPI

from energy_trading.api.app import create_app
from energy_trading.api.composition.document_vector_index_lifespan import (
    build_document_vector_index_lifespan,
)
from energy_trading.api.composition.production_lifespan import (
    build_production_lifespan,
)
from energy_trading.api.composition.regulatory_intelligence_lifespan import (
    build_regulatory_intelligence_lifespan,
)
from tests.architecture.import_inspection import SRC_ROOT, imported_modules, imported_names
from tests.unit.api.helpers import make_test_settings

_COMPOSITE_MODULE = "energy_trading.api.composition.production_lifespan"
_EXPLICIT_ENV_FILE = Path("sentinel-chunk93.env")


@dataclass
class _ChildLifespanSpy:
    label: str
    events: list[str]
    calls: list[dict[str, object]] = field(default_factory=list)
    apps: list[FastAPI] = field(default_factory=list)
    entered: bool = False
    entry_error: BaseException | None = None

    def __call__(
        self,
        *,
        env_file: object,
    ) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
        self.calls.append({"env_file": env_file})
        return self._callback

    def _callback(self, app: FastAPI) -> AbstractAsyncContextManager[None]:
        self.apps.append(app)
        return self._context()

    @asynccontextmanager
    async def _context(self) -> AsyncIterator[None]:
        if self.entry_error is not None:
            raise self.entry_error
        self.events.append(f"{self.label}_enter")
        self.entered = True
        try:
            yield
        finally:
            self.entered = False
            self.events.append(f"{self.label}_exit")


def _patch_child_lifespans(
    monkeypatch: pytest.MonkeyPatch,
    *,
    regulatory_entry_error: BaseException | None = None,
    document_index_entry_error: BaseException | None = None,
) -> tuple[_ChildLifespanSpy, _ChildLifespanSpy, list[str]]:
    events: list[str] = []
    regulatory = _ChildLifespanSpy(
        label="regulatory",
        events=events,
        entry_error=regulatory_entry_error,
    )
    document_index = _ChildLifespanSpy(
        label="document_index",
        events=events,
        entry_error=document_index_entry_error,
    )
    monkeypatch.setattr(
        f"{_COMPOSITE_MODULE}.build_regulatory_intelligence_lifespan",
        regulatory,
    )
    monkeypatch.setattr(
        f"{_COMPOSITE_MODULE}.build_document_vector_index_lifespan",
        document_index,
    )
    return regulatory, document_index, events


def test_factory_is_synchronous_keyword_only_and_matches_child_env_file() -> None:
    assert inspect.iscoroutinefunction(build_production_lifespan) is False
    assert inspect.isasyncgenfunction(build_production_lifespan) is False
    signature = inspect.signature(build_production_lifespan)
    assert tuple(signature.parameters) == ("env_file",)
    parameter = signature.parameters["env_file"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    regulatory_env = inspect.signature(build_regulatory_intelligence_lifespan).parameters[
        "env_file"
    ]
    document_index_env = inspect.signature(build_document_vector_index_lifespan).parameters[
        "env_file"
    ]
    assert parameter.annotation == regulatory_env.annotation
    assert parameter.annotation == document_index_env.annotation
    assert parameter.default == regulatory_env.default
    assert parameter.default == document_index_env.default
    assert parameter.default == ".env"
    with pytest.raises(TypeError):
        build_production_lifespan(".env")  # type: ignore[misc]


def test_returned_callback_is_fastapi_lifespan_callable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_child_lifespans(monkeypatch)
    callback = build_production_lifespan(env_file=None)
    assert callable(callback)
    application = FastAPI()
    manager = callback(application)
    assert isinstance(manager, AbstractAsyncContextManager)


def test_factory_construction_does_not_enter_either_child_lifespan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    regulatory, document_index, events = _patch_child_lifespans(monkeypatch)
    callback = build_production_lifespan(env_file=_EXPLICIT_ENV_FILE)
    assert events == []
    assert regulatory.entered is False
    assert document_index.entered is False
    assert regulatory.apps == []
    assert document_index.apps == []
    manager = callback(FastAPI())
    assert events == []
    assert regulatory.entered is False
    assert document_index.entered is False
    assert isinstance(manager, AbstractAsyncContextManager)


def test_explicit_env_file_is_forwarded_unchanged_to_both_child_factories(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    regulatory, document_index, _events = _patch_child_lifespans(monkeypatch)
    build_production_lifespan(env_file=_EXPLICIT_ENV_FILE)
    assert regulatory.calls == [{"env_file": _EXPLICIT_ENV_FILE}]
    assert document_index.calls == [{"env_file": _EXPLICIT_ENV_FILE}]
    assert regulatory.calls[0]["env_file"] is _EXPLICIT_ENV_FILE
    assert document_index.calls[0]["env_file"] is _EXPLICIT_ENV_FILE


def test_default_env_file_is_forwarded_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    regulatory, document_index, _events = _patch_child_lifespans(monkeypatch)
    build_production_lifespan()
    assert regulatory.calls == [{"env_file": ".env"}]
    assert document_index.calls == [{"env_file": ".env"}]


def test_none_env_file_is_forwarded_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    regulatory, document_index, _events = _patch_child_lifespans(monkeypatch)
    build_production_lifespan(env_file=None)
    assert regulatory.calls == [{"env_file": None}]
    assert document_index.calls == [{"env_file": None}]


async def test_entry_exit_order_is_regulatory_outer_document_index_inner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _regulatory, _document_index, events = _patch_child_lifespans(monkeypatch)
    callback = build_production_lifespan(env_file=None)
    async with callback(FastAPI()):
        events.append("application_body")
    assert events == [
        "regulatory_enter",
        "document_index_enter",
        "application_body",
        "document_index_exit",
        "regulatory_exit",
    ]


async def test_both_child_callbacks_receive_the_same_fastapi_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    regulatory, document_index, _events = _patch_child_lifespans(monkeypatch)
    callback = build_production_lifespan(env_file=None)
    application = FastAPI()
    async with callback(application):
        pass
    assert regulatory.apps == [application]
    assert document_index.apps == [application]
    assert regulatory.apps[0] is application
    assert document_index.apps[0] is application
    assert document_index.apps[0] is regulatory.apps[0]


async def test_regulatory_entry_failure_skips_document_index_and_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = RuntimeError("regulatory-entry-failed")
    regulatory, document_index, events = _patch_child_lifespans(
        monkeypatch,
        regulatory_entry_error=error,
    )
    body_reached = False
    callback = build_production_lifespan(env_file=None)
    with pytest.raises(RuntimeError) as captured:
        async with callback(FastAPI()):
            body_reached = True
    assert captured.value is error
    assert body_reached is False
    assert events == []
    assert regulatory.entered is False
    assert document_index.entered is False
    assert document_index.apps == []


async def test_document_index_entry_failure_exits_regulatory_and_skips_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = RuntimeError("document-index-entry-failed")
    regulatory, document_index, events = _patch_child_lifespans(
        monkeypatch,
        document_index_entry_error=error,
    )
    body_reached = False
    callback = build_production_lifespan(env_file=None)
    application = FastAPI()
    with pytest.raises(RuntimeError) as captured:
        async with callback(application):
            body_reached = True
    assert captured.value is error
    assert body_reached is False
    assert events == ["regulatory_enter", "regulatory_exit"]
    assert document_index.entered is False
    assert document_index.apps == [application]
    assert regulatory.apps == [application]
    assert regulatory.entered is False


async def test_composed_lifespan_yields_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _regulatory, _document_index, events = _patch_child_lifespans(monkeypatch)
    callback = build_production_lifespan(env_file=None)
    async with callback(FastAPI()) as yielded:
        assert yielded is None
        assert events == ["regulatory_enter", "document_index_enter"]
    assert yielded is None
    assert events == [
        "regulatory_enter",
        "document_index_enter",
        "document_index_exit",
        "regulatory_exit",
    ]


def test_create_app_installs_production_lifespan_without_entering_children(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    regulatory, document_index, events = _patch_child_lifespans(monkeypatch)
    source = inspect.getsource(create_app)
    assert "build_production_lifespan" in source
    assert "build_regulatory_intelligence_lifespan" not in source
    assert "build_document_vector_index_lifespan" not in source
    application = create_app(make_test_settings())
    assert events == []
    assert regulatory.calls == [{"env_file": ".env"}]
    assert document_index.calls == [{"env_file": ".env"}]
    assert regulatory.entered is False
    assert document_index.entered is False
    assert regulatory.apps == []
    assert document_index.apps == []
    installed = application.router.lifespan_context
    try:
        installed_source = inspect.getsource(installed)
    except OSError:
        installed_source = ""
    assert "build_regulatory_intelligence_lifespan" not in installed_source
    assert "build_document_vector_index_lifespan" not in installed_source


def test_composite_module_does_not_import_the_app_factory() -> None:
    path = SRC_ROOT / "energy_trading/api/composition/production_lifespan.py"
    names = imported_names(path)
    modules = imported_modules(path)
    assert "create_app" not in names
    assert "energy_trading.api.app" not in modules
    assert "energy_trading.api.routers" not in modules
    assert "build_regulatory_intelligence_lifespan" in names
    assert "build_document_vector_index_lifespan" in names
