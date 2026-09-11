"""Document Vector Index request accessor reads lifespan-scoped app.state."""

from __future__ import annotations

import inspect

import pytest
from fastapi import FastAPI, Request

from energy_trading.api.dependencies.document_vector_index import (
    get_document_vector_index_execution_service,
)
from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.orchestration.document_vector_index_execution import (
    DocumentVectorIndexExecutionService,
)

_SERVICE_ATTR = "document_vector_index_execution_service"
_UNAVAILABLE_MESSAGE = "Document Vector Index service is unavailable."


class _Trap:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def prepare(self, *, chunks: object) -> None:
        self.calls.append("prepare")
        raise AssertionError("index-entry preparation must not be invoked")

    async def index(self, entries: object) -> None:
        self.calls.append("index")
        raise AssertionError("vector index must not be invoked")

    async def execute(self, *, chunks: object) -> None:
        self.calls.append("execute")
        raise AssertionError("index execution must not be invoked")


def _make_service() -> tuple[DocumentVectorIndexExecutionService, _Trap, _Trap]:
    preparation = _Trap()
    index_port = _Trap()
    service = DocumentVectorIndexExecutionService(preparation, index_port)
    return service, preparation, index_port


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
    assert inspect.iscoroutinefunction(get_document_vector_index_execution_service) is False
    signature = inspect.signature(get_document_vector_index_execution_service)
    assert tuple(signature.parameters) == ("request",)
    parameter = signature.parameters["request"]
    assert parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert parameter.annotation is Request
    assert signature.return_annotation is DocumentVectorIndexExecutionService


def test_returns_exact_service_identity_from_published_state_attribute() -> None:
    service, preparation, index_port = _make_service()
    application = FastAPI()
    setattr(application.state, _SERVICE_ATTR, service)
    result = get_document_vector_index_execution_service(_request_for(application))
    assert result is service
    assert type(result) is DocumentVectorIndexExecutionService
    assert preparation.calls == []
    assert index_port.calls == []


def test_reads_exact_published_state_attribute_and_ignores_other_names() -> None:
    service, _, _ = _make_service()
    decoy, _, _ = _make_service()
    application = FastAPI()
    application.state.document_vector_index_service = decoy
    setattr(application.state, _SERVICE_ATTR, service)
    result = get_document_vector_index_execution_service(_request_for(application))
    assert result is service
    assert result is not decoy


def test_missing_service_fails_closed_as_dependency_unavailable() -> None:
    application = FastAPI()
    with pytest.raises(DependencyUnavailableError) as captured:
        get_document_vector_index_execution_service(_request_for(application))
    assert type(captured.value) is DependencyUnavailableError
    assert captured.value.code == "dependency_unavailable"
    assert captured.value.message == _UNAVAILABLE_MESSAGE
    assert captured.value.__cause__ is None
    assert not hasattr(application.state, _SERVICE_ATTR)


def test_successful_read_does_not_mutate_state_or_invoke_the_service() -> None:
    service, preparation, index_port = _make_service()
    application = FastAPI()
    setattr(application.state, _SERVICE_ATTR, service)
    first = get_document_vector_index_execution_service(_request_for(application))
    second = get_document_vector_index_execution_service(_request_for(application))
    assert first is service
    assert second is service
    assert getattr(application.state, _SERVICE_ATTR) is service
    assert preparation.calls == []
    assert index_port.calls == []


def test_wrong_type_state_value_fails_closed_as_dependency_unavailable() -> None:
    application = FastAPI()
    wrong = object()
    setattr(application.state, _SERVICE_ATTR, wrong)
    with pytest.raises(DependencyUnavailableError) as captured:
        get_document_vector_index_execution_service(_request_for(application))
    assert type(captured.value) is DependencyUnavailableError
    assert captured.value.code == "dependency_unavailable"
    assert captured.value.message == _UNAVAILABLE_MESSAGE
    assert captured.value.__cause__ is None
    assert getattr(application.state, _SERVICE_ATTR) is wrong
    assert repr(wrong) not in captured.value.message


def test_state_exposure_is_isolated_per_application() -> None:
    service_a, _, _ = _make_service()
    service_b, _, _ = _make_service()
    app_a = FastAPI()
    app_b = FastAPI()
    setattr(app_a.state, _SERVICE_ATTR, service_a)
    setattr(app_b.state, _SERVICE_ATTR, service_b)
    assert get_document_vector_index_execution_service(_request_for(app_a)) is service_a
    assert get_document_vector_index_execution_service(_request_for(app_b)) is service_b
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
    assert get_document_vector_index_execution_service(request) is service_b
    assert get_document_vector_index_execution_service(request) is not service_a
