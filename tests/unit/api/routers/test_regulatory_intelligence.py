"""Regulatory Intelligence HTTP query route stays a thin transport boundary."""

from __future__ import annotations

from datetime import date

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from energy_trading.api.exception_handlers import register_exception_handlers
from energy_trading.api.middleware import CorrelationMiddleware
from energy_trading.api.routers.regulatory_intelligence import router
from energy_trading.application.agents.regulatory_intelligence import (
    RegulatoryIntelligenceResult,
)
from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.orchestration.regulatory_intelligence_query_execution import (
    RegulatoryIntelligenceQueryExecutionService,
)
from energy_trading.domain.models.regulatory import RegulatoryConstraint

_QUERY_PATH = "/api/v1/regulatory-intelligence/query"
_SERVICE_ATTR = "regulatory_intelligence_query_execution_service"
_UNAVAILABLE_MESSAGE = "Regulatory Intelligence service is unavailable."
_EXECUTION_FAILURE_MESSAGE = "Regulatory query execution failed."


class _UnusedDependency:
    async def prepare(self, *, query_text: str, limit: int) -> None:
        raise AssertionError("overridden execute must not reach query preparation")

    async def run(self, request: object) -> None:
        raise AssertionError("overridden execute must not reach the agent")


class RecordingQueryExecutionService(RegulatoryIntelligenceQueryExecutionService):
    def __init__(self) -> None:
        super().__init__(_UnusedDependency(), _UnusedDependency())  # type: ignore[arg-type]
        self.calls: list[tuple[str, int]] = []
        self.result = RegulatoryIntelligenceResult(constraints=())
        self.error: BaseException | None = None

    async def execute(
        self,
        *,
        query_text: str,
        limit: int,
    ) -> RegulatoryIntelligenceResult:
        self.calls.append((query_text, limit))
        if self.error is not None:
            raise self.error
        return self.result


def _query_app(
    service: RegulatoryIntelligenceQueryExecutionService | None = None,
) -> FastAPI:
    application = FastAPI()
    application.add_middleware(CorrelationMiddleware)
    register_exception_handlers(application)
    application.include_router(router, prefix="/api/v1")
    if service is not None:
        setattr(application.state, _SERVICE_ATTR, service)
    return application


async def _post_query(application: FastAPI, payload: object) -> object:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post(_QUERY_PATH, json=payload)


def _constraint(
    *,
    constraint_id: str = "constraint-1",
    constraint_type: str = "capacity_limit",
    description: str = "Generic numeric bound",
    effective_from: date = date(2026, 1, 1),
    effective_to: date | None = date(2026, 12, 31),
    minimum_value: float | None = 1.5,
    maximum_value: float | None = 10.25,
    unit: str | None = "MW",
    currency: str | None = "AMD",
    source_document_id: str | None = "doc-1",
) -> RegulatoryConstraint:
    return RegulatoryConstraint(
        constraint_id=constraint_id,
        constraint_type=constraint_type,
        description=description,
        effective_from=effective_from,
        effective_to=effective_to,
        minimum_value=minimum_value,
        maximum_value=maximum_value,
        unit=unit,
        currency=currency,
        source_document_id=source_document_id,
    )


async def test_successful_query_executes_the_service_once_with_exact_fields() -> None:
    service = RecordingQueryExecutionService()
    response = await _post_query(
        _query_app(service),
        {"query_text": "some text", "limit": 3},
    )

    assert response.status_code == 200
    assert service.calls == [("some text", 3)]
    assert response.json() == {"constraints": []}


async def test_route_forwards_whitespace_query_text_unchanged() -> None:
    service = RecordingQueryExecutionService()
    surrounding = "  surrounding spaces are preserved  "
    response = await _post_query(
        _query_app(service),
        {"query_text": surrounding, "limit": 2},
    )

    assert response.status_code == 200
    assert service.calls == [(surrounding, 2)]
    assert service.calls[0][0] != surrounding.strip()


async def test_route_forwards_whitespace_only_query_text_unchanged() -> None:
    service = RecordingQueryExecutionService()
    whitespace_only = "   "
    response = await _post_query(
        _query_app(service),
        {"query_text": whitespace_only, "limit": 1},
    )

    assert response.status_code == 200
    assert service.calls == [(whitespace_only, 1)]
    assert service.calls[0][0] == "   "


async def test_response_maps_published_canonical_constraint_fields() -> None:
    service = RecordingQueryExecutionService()
    service.result = RegulatoryIntelligenceResult(
        constraints=(
            _constraint(),
            _constraint(
                constraint_id="constraint-2",
                constraint_type="license_window",
                description="Optional fields omitted",
                effective_from=date(2027, 3, 15),
                effective_to=None,
                minimum_value=None,
                maximum_value=None,
                unit=None,
                currency=None,
                source_document_id=None,
            ),
        )
    )
    response = await _post_query(
        _query_app(service),
        {"query_text": "map constraints", "limit": 4},
    )

    assert response.status_code == 200
    assert service.calls == [("map constraints", 4)]
    assert response.json() == {
        "constraints": [
            {
                "constraint_id": "constraint-1",
                "constraint_type": "capacity_limit",
                "description": "Generic numeric bound",
                "effective_from": "2026-01-01",
                "effective_to": "2026-12-31",
                "minimum_value": 1.5,
                "maximum_value": 10.25,
                "unit": "MW",
                "currency": "AMD",
                "source_document_id": "doc-1",
            },
            {
                "constraint_id": "constraint-2",
                "constraint_type": "license_window",
                "description": "Optional fields omitted",
                "effective_from": "2027-03-15",
                "effective_to": None,
                "minimum_value": None,
                "maximum_value": None,
                "unit": None,
                "currency": None,
                "source_document_id": None,
            },
        ]
    }


async def test_empty_constraints_serialize_as_an_empty_json_list() -> None:
    service = RecordingQueryExecutionService()
    service.result = RegulatoryIntelligenceResult(constraints=())
    response = await _post_query(
        _query_app(service),
        {"query_text": "empty result", "limit": 5},
    )

    assert response.status_code == 200
    assert service.calls == [("empty result", 5)]
    payload = response.json()
    assert payload == {"constraints": []}
    assert payload["constraints"] == []


async def test_non_positive_limit_is_rejected_before_execution() -> None:
    service = RecordingQueryExecutionService()
    application = _query_app(service)
    zero = await _post_query(application, {"query_text": "rules query", "limit": 0})
    negative = await _post_query(application, {"query_text": "rules query", "limit": -1})

    assert zero.status_code == 422
    assert negative.status_code == 422
    assert zero.json()["error"]["code"] == "request_validation_error"
    assert negative.json()["error"]["code"] == "request_validation_error"
    assert service.calls == []


async def test_missing_required_field_is_rejected_before_execution() -> None:
    service = RecordingQueryExecutionService()
    application = _query_app(service)
    missing_query = await _post_query(application, {"limit": 3})
    missing_limit = await _post_query(application, {"query_text": "rules query"})

    assert missing_query.status_code == 422
    assert missing_limit.status_code == 422
    assert service.calls == []


async def test_unknown_request_field_is_rejected_before_execution() -> None:
    service = RecordingQueryExecutionService()
    response = await _post_query(
        _query_app(service),
        {
            "query_text": "rules query",
            "limit": 3,
            "collection": "regulatory-docs",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "request_validation_error"
    assert service.calls == []


async def test_missing_lifespan_state_uses_published_accessor_and_existing_503() -> None:
    response = await _post_query(
        _query_app(None),
        {"query_text": "some text", "limit": 3},
    )

    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == "dependency_unavailable"
    assert error["message"] == _UNAVAILABLE_MESSAGE


async def test_application_error_from_execute_uses_centralized_mapping() -> None:
    service = RecordingQueryExecutionService()
    service.error = InvalidRequestError(_EXECUTION_FAILURE_MESSAGE)
    response = await _post_query(
        _query_app(service),
        {"query_text": "some text", "limit": 3},
    )

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "invalid_request"
    assert error["message"] == _EXECUTION_FAILURE_MESSAGE
    assert service.calls == [("some text", 3)]
    assert "traceback" not in response.text.lower()
