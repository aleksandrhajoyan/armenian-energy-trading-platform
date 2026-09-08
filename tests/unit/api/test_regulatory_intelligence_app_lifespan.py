"""Production create_app installs the Regulatory lifespan and exposes it on app.state."""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass, field

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from energy_trading.api import app as app_module
from energy_trading.api.app import create_app
from energy_trading.api.composition.regulatory_intelligence_lifespan import (
    build_regulatory_intelligence_lifespan,
)
from tests.unit.api.helpers import make_test_settings, noop_lifespan

_LIFESPAN_MODULE = "energy_trading.api.composition.regulatory_intelligence_lifespan"
_SERVICE_ATTR = "regulatory_intelligence_query_execution_service"


@dataclass
class _RecordingService:
    calls: list[str] = field(default_factory=list)

    async def execute(self, **_kwargs: object) -> None:
        self.calls.append("execute")


@dataclass
class _LifespanSpy:
    calls: list[object] = field(default_factory=list)
    events: list[str] = field(default_factory=list)
    active: bool = False
    entry_error: BaseException | None = None
    exit_error: BaseException | None = None

    def __call__(self, _app: FastAPI) -> AbstractAsyncContextManager[None]:
        self.calls.append(_app)
        return self._context()

    @asynccontextmanager
    async def _context(self) -> AsyncIterator[None]:
        if self.entry_error is not None:
            self.events.append("enter-failed")
            raise self.entry_error
        self.events.append("enter")
        self.active = True
        try:
            yield
        finally:
            self.active = False
            self.events.append("exit")
            if self.exit_error is not None:
                raise self.exit_error


@dataclass
class _LoadedRuntimeSpy:
    calls: list[dict[str, object]] = field(default_factory=list)
    events: list[str] = field(default_factory=list)

    def __call__(self, **kwargs: object) -> AbstractAsyncContextManager[object]:
        self.calls.append(kwargs)
        return self._context()

    @asynccontextmanager
    async def _context(self) -> AsyncIterator[object]:
        self.events.append("enter")
        try:
            yield object()
        finally:
            self.events.append("exit")


def _has_service(app: FastAPI) -> bool:
    return hasattr(app.state, _SERVICE_ATTR)


def test_production_create_app_installs_chunk_76_lifespan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spy = _LifespanSpy()
    builder_calls: list[dict[str, object]] = []

    def fake_builder(**kwargs: object) -> _LifespanSpy:
        builder_calls.append(kwargs)
        return spy

    monkeypatch.setattr(app_module, "build_regulatory_intelligence_lifespan", fake_builder)
    application = create_app(make_test_settings())
    assert builder_calls == [{}]
    assert spy.calls == []
    assert spy.events == []
    with TestClient(application) as client:
        assert spy.calls == [application]
        assert spy.events == ["enter"]
        assert spy.active is True
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    assert spy.events == ["enter", "exit"]
    assert spy.active is False
    assert len(spy.calls) == 1


def test_create_app_construction_does_not_enter_regulatory_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spy = _LoadedRuntimeSpy()
    monkeypatch.setattr(f"{_LIFESPAN_MODULE}.loaded_regulatory_intelligence_runtime", spy)
    application = create_app(make_test_settings())
    assert isinstance(application, FastAPI)
    assert spy.calls == []
    assert spy.events == []


def test_explicit_lifespan_override_skips_production_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(**_kwargs: object) -> None:
        raise AssertionError("production builder must not be called")

    monkeypatch.setattr(app_module, "build_regulatory_intelligence_lifespan", boom)
    spy = _LifespanSpy()
    application = create_app(make_test_settings(), lifespan=spy)
    assert spy.calls == []
    with TestClient(application):
        assert spy.events == ["enter"]
        assert spy.active is True
    assert spy.events == ["enter", "exit"]


def test_injected_noop_lifespan_keeps_health_offline() -> None:
    application = create_app(make_test_settings(), lifespan=noop_lifespan)
    with TestClient(application) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "AI Energy Trading Platform",
        "environment": "test",
    }


def test_production_default_is_not_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = _LifespanSpy()

    def fake_builder(**_kwargs: object) -> _LifespanSpy:
        return sentinel

    monkeypatch.setattr(app_module, "build_regulatory_intelligence_lifespan", fake_builder)
    application = create_app(make_test_settings())
    with TestClient(application):
        assert sentinel.events == ["enter"]
    assert sentinel.events == ["enter", "exit"]


def test_create_app_exposes_chunk_75_service_on_app_state_during_lifespan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _RecordingService()

    @asynccontextmanager
    async def fake_loaded(**_kwargs: object) -> AsyncIterator[object]:
        yield service

    monkeypatch.setattr(f"{_LIFESPAN_MODULE}.loaded_regulatory_intelligence_runtime", fake_loaded)
    application = create_app(make_test_settings())
    assert _has_service(application) is False

    @application.get("/peek")
    async def peek(request: Request) -> dict[str, str]:
        exposed = request.app.state.regulatory_intelligence_query_execution_service
        assert exposed is service
        return {"status": "ok"}

    with TestClient(application) as client:
        assert application.state.regulatory_intelligence_query_execution_service is service
        response = client.get("/peek")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert service.calls == []
    assert _has_service(application) is False
    assert service.calls == []


def test_startup_failure_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    error = RuntimeError("regulatory-startup-failed")
    spy = _LifespanSpy(entry_error=error)
    monkeypatch.setattr(
        app_module,
        "build_regulatory_intelligence_lifespan",
        lambda **_kwargs: spy,
    )
    application = create_app(make_test_settings())
    with pytest.raises(RuntimeError) as captured:
        with TestClient(application):
            raise AssertionError("request must not run")
    assert captured.value is error
    assert spy.events == ["enter-failed"]


def test_shutdown_failure_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    error = RuntimeError("regulatory-shutdown-failed")
    spy = _LifespanSpy(exit_error=error)
    monkeypatch.setattr(
        app_module,
        "build_regulatory_intelligence_lifespan",
        lambda **_kwargs: spy,
    )
    application = create_app(make_test_settings())
    with pytest.raises(RuntimeError) as captured:
        with TestClient(application):
            assert spy.active is True
    assert captured.value is error
    assert spy.events == ["enter", "exit"]


def test_lifespan_parameter_is_keyword_only() -> None:
    signature = inspect.signature(create_app)
    assert "lifespan" in signature.parameters
    assert signature.parameters["lifespan"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["lifespan"].default is None
    with pytest.raises(TypeError):
        create_app(make_test_settings(), noop_lifespan)  # type: ignore[misc]


def test_production_builder_identity_is_the_chunk_76_factory() -> None:
    assert app_module.build_regulatory_intelligence_lifespan is (
        build_regulatory_intelligence_lifespan
    )
