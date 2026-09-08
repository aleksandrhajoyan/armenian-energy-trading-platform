"""Production create_app installs the Regulatory query router under the API prefix."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from energy_trading.api.app import create_app
from energy_trading.application.agents.regulatory_intelligence import (
    RegulatoryIntelligenceResult,
)
from energy_trading.application.orchestration.regulatory_intelligence_query_execution import (
    RegulatoryIntelligenceQueryExecutionService,
)
from energy_trading.domain.models.regulatory import RegulatoryConstraint
from tests.unit.api.helpers import make_test_settings, noop_lifespan

_QUERY_PATH = "/api/v1/regulatory-intelligence/query"
_SERVICE_ATTR = "regulatory_intelligence_query_execution_service"
_UNAVAILABLE_MESSAGE = "Regulatory Intelligence service is unavailable."


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

    async def execute(
        self,
        *,
        query_text: str,
        limit: int,
    ) -> RegulatoryIntelligenceResult:
        self.calls.append((query_text, limit))
        return self.result


def _constraint() -> RegulatoryConstraint:
    return RegulatoryConstraint(
        constraint_id="constraint-1",
        constraint_type="capacity_limit",
        description="Generic numeric bound",
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        minimum_value=1.5,
        maximum_value=10.25,
        unit="MW",
        currency="AMD",
        source_document_id="doc-1",
    )


def _install_service_lifespan(
    service: RecordingQueryExecutionService,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        setattr(app.state, _SERVICE_ATTR, service)
        try:
            yield
        finally:
            if hasattr(app.state, _SERVICE_ATTR):
                delattr(app.state, _SERVICE_ATTR)

    return lifespan


async def test_production_query_route_is_registered_and_health_stays_offline() -> None:
    application = create_app(make_test_settings(), lifespan=noop_lifespan)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        query = await client.post(
            _QUERY_PATH,
            json={"query_text": "some text", "limit": 3},
        )
        health = await client.get("/api/v1/health")

    assert query.status_code != 404
    assert query.status_code == 503
    error = query.json()["error"]
    assert error["code"] == "dependency_unavailable"
    assert error["message"] == _UNAVAILABLE_MESSAGE
    assert health.status_code == 200
    assert health.json() == {
        "status": "ok",
        "service": "AI Energy Trading Platform",
        "environment": "test",
    }


def test_production_create_app_query_route_forwards_to_the_published_service() -> None:
    service = RecordingQueryExecutionService()
    service.result = RegulatoryIntelligenceResult(constraints=(_constraint(),))
    query_text = "  keep surrounding spaces  "
    application = create_app(
        make_test_settings(),
        lifespan=_install_service_lifespan(service),
    )
    assert service.calls == []
    assert hasattr(application.state, _SERVICE_ATTR) is False

    with TestClient(application) as client:
        assert application.state.regulatory_intelligence_query_execution_service is service
        response = client.post(
            _QUERY_PATH,
            json={"query_text": query_text, "limit": 4},
        )

    assert response.status_code == 200
    assert service.calls == [(query_text, 4)]
    assert service.calls[0][0] != query_text.strip()
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
            }
        ]
    }
    assert hasattr(application.state, _SERVICE_ATTR) is False
