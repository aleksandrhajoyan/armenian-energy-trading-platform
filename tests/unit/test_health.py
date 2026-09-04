"""ASGI tests for GET /api/v1/health."""

from typing import Literal

import pytest
from httpx import ASGITransport, AsyncClient

from energy_trading.api.app import create_app
from energy_trading.shared.config.settings import AppEnvironment, AppSettings


def _test_settings(
    *,
    app_name: str = "AI Energy Trading Platform",
    environment: AppEnvironment = AppEnvironment.TEST,
    api_prefix: str = "/api/v1",
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO",
) -> AppSettings:
    return AppSettings(
        _env_file=None,
        app_name=app_name,
        environment=environment,
        api_prefix=api_prefix,
        log_level=log_level,
    )


@pytest.mark.asyncio
async def test_health_returns_process_status() -> None:
    application = create_app(_test_settings())
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


@pytest.mark.asyncio
async def test_health_reflects_injected_settings() -> None:
    application = create_app(
        _test_settings(
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
