"""Regulatory Intelligence request accessor reads lifespan-scoped app.state."""

from __future__ import annotations

import inspect

import pytest
from fastapi import FastAPI, Request

from energy_trading.api.dependencies.regulatory_intelligence import (
    get_regulatory_intelligence_query_execution_service,
)
from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.orchestration.regulatory_intelligence_query_execution import (
    RegulatoryIntelligenceQueryExecutionService,
)

_SERVICE_ATTR = "regulatory_intelligence_query_execution_service"
_UNAVAILABLE_MESSAGE = "Regulatory Intelligence service is unavailable."


class _Trap:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def prepare(self, *, query_text: str, limit: int) -> None:
        self.calls.append("prepare")
        raise AssertionError("query preparation must not be invoked")

    async def run(self, request: object) -> None:
        self.calls.append("run")
        raise AssertionError("agent run must not be invoked")


def _make_service() -> tuple[RegulatoryIntelligenceQueryExecutionService, _Trap, _Trap]:
    preparation = _Trap()
    agent = _Trap()
    service = RegulatoryIntelligenceQueryExecutionService(preparation, agent)
    return service, preparation, agent


def _request_for(application: FastAPI) -> Request:
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": [],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
            "app": application,
        }
    )


def test_accessor_is_synchronous_and_accepts_exactly_one_request() -> None:
    assert inspect.iscoroutinefunction(get_regulatory_intelligence_query_execution_service) is False
    signature = inspect.signature(get_regulatory_intelligence_query_execution_service)
    assert tuple(signature.parameters) == ("request",)
    parameter = signature.parameters["request"]
    assert parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert parameter.annotation is Request
    assert signature.return_annotation is RegulatoryIntelligenceQueryExecutionService


def test_returns_exact_service_identity_from_published_state_attribute() -> None:
    service, preparation, agent = _make_service()
    application = FastAPI()
    setattr(application.state, _SERVICE_ATTR, service)
    result = get_regulatory_intelligence_query_execution_service(_request_for(application))
    assert result is service
    assert type(result) is RegulatoryIntelligenceQueryExecutionService
    assert preparation.calls == []
    assert agent.calls == []


def test_reads_exact_published_state_attribute_and_ignores_other_names() -> None:
    service, _, _ = _make_service()
    decoy, _, _ = _make_service()
    application = FastAPI()
    application.state.regulatory_intelligence_service = decoy
    setattr(application.state, _SERVICE_ATTR, service)
    result = get_regulatory_intelligence_query_execution_service(_request_for(application))
    assert result is service
    assert result is not decoy


def test_missing_service_fails_closed_as_dependency_unavailable() -> None:
    application = FastAPI()
    with pytest.raises(DependencyUnavailableError) as captured:
        get_regulatory_intelligence_query_execution_service(_request_for(application))
    assert type(captured.value) is DependencyUnavailableError
    assert captured.value.code == "dependency_unavailable"
    assert captured.value.message == _UNAVAILABLE_MESSAGE
    assert captured.value.__cause__ is None
    assert not hasattr(application.state, _SERVICE_ATTR)


def test_successful_read_does_not_mutate_state_or_invoke_the_service() -> None:
    service, preparation, agent = _make_service()
    application = FastAPI()
    setattr(application.state, _SERVICE_ATTR, service)
    first = get_regulatory_intelligence_query_execution_service(_request_for(application))
    second = get_regulatory_intelligence_query_execution_service(_request_for(application))
    assert first is service
    assert second is service
    assert getattr(application.state, _SERVICE_ATTR) is service
    assert preparation.calls == []
    assert agent.calls == []


def test_wrong_type_state_value_fails_closed_as_dependency_unavailable() -> None:
    application = FastAPI()
    wrong = object()
    setattr(application.state, _SERVICE_ATTR, wrong)
    with pytest.raises(DependencyUnavailableError) as captured:
        get_regulatory_intelligence_query_execution_service(_request_for(application))
    assert type(captured.value) is DependencyUnavailableError
    assert captured.value.code == "dependency_unavailable"
    assert captured.value.message == _UNAVAILABLE_MESSAGE
    assert getattr(application.state, _SERVICE_ATTR) is wrong


def test_state_exposure_is_isolated_per_application() -> None:
    service_a, _, _ = _make_service()
    service_b, _, _ = _make_service()
    app_a = FastAPI()
    app_b = FastAPI()
    setattr(app_a.state, _SERVICE_ATTR, service_a)
    setattr(app_b.state, _SERVICE_ATTR, service_b)
    assert get_regulatory_intelligence_query_execution_service(_request_for(app_a)) is service_a
    assert get_regulatory_intelligence_query_execution_service(_request_for(app_b)) is service_b
    assert service_a is not service_b


def test_accessor_uses_the_request_app_not_module_global_state() -> None:
    service_a, _, _ = _make_service()
    service_b, _, _ = _make_service()
    app_a = FastAPI()
    app_b = FastAPI()
    setattr(app_a.state, _SERVICE_ATTR, service_a)
    setattr(app_b.state, _SERVICE_ATTR, service_b)
    request = _request_for(app_b)
    assert request.app is app_b
    assert get_regulatory_intelligence_query_execution_service(request) is service_b
    assert get_regulatory_intelligence_query_execution_service(request) is not service_a
