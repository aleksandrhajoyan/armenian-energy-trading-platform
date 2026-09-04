"""ASGI tests for GET /api/v1/health."""

from httpx import ASGITransport, AsyncClient

from energy_trading.api.app import create_app
from energy_trading.shared.config.settings import AppEnvironment

from .api.helpers import make_test_settings


async def test_health_returns_process_status() -> None:
    application = create_app(make_test_settings())
    transport = ASGITransport(app=application)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "status": "ok",
        "service": "AI Energy Trading Platform",
        "environment": "test",
    }
    assert "postgres" not in payload
    assert "redis" not in payload
    assert "qdrant" not in payload
    assert "correlation_id" not in payload
    assert response.headers["x-correlation-id"]


async def test_health_reflects_injected_settings() -> None:
    application = create_app(
        make_test_settings(
            app_name="Health Override",
            environment=AppEnvironment.PRODUCTION,
        )
    )
    transport = ASGITransport(app=application)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "Health Override"
    assert payload["environment"] == "production"
