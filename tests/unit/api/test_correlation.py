"""HTTP correlation ID propagation and isolation tests."""

import asyncio
import json
import logging

from energy_trading.api.app import create_app
from energy_trading.shared.observability.correlation import is_valid_correlation_id
from energy_trading.shared.observability.logging import CorrelationIdFilter, JsonLogFormatter

from .helpers import api_client, make_test_settings


async def test_health_reuses_valid_correlation_id() -> None:
    async with api_client() as client:
        response = await client.get(
            "/api/v1/health",
            headers={"X-Correlation-ID": "portfolio-demo-123"},
        )

    assert response.status_code == 200
    assert response.headers["x-correlation-id"] == "portfolio-demo-123"
    assert "correlation_id" not in response.json()


async def test_health_generates_correlation_id_when_missing() -> None:
    async with api_client() as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    generated = response.headers["x-correlation-id"]
    assert is_valid_correlation_id(generated)


async def test_health_replaces_invalid_correlation_id() -> None:
    async with api_client() as client:
        response = await client.get(
            "/api/v1/health",
            headers={"X-Correlation-ID": "not a valid id because of spaces"},
        )

    assert response.status_code == 200
    generated = response.headers["x-correlation-id"]
    assert generated != "not a valid id because of spaces"
    assert is_valid_correlation_id(generated)


async def test_sequential_requests_do_not_leak_correlation_ids() -> None:
    async with api_client() as client:
        first = await client.get(
            "/api/v1/health",
            headers={"X-Correlation-ID": "sequential-one"},
        )
        second = await client.get(
            "/api/v1/health",
            headers={"X-Correlation-ID": "sequential-two"},
        )

    assert first.headers["x-correlation-id"] == "sequential-one"
    assert second.headers["x-correlation-id"] == "sequential-two"


async def test_concurrent_requests_do_not_leak_correlation_ids() -> None:
    application = create_app(make_test_settings())
    async with api_client(application) as client:
        responses = await asyncio.gather(
            *[
                client.get(
                    "/api/v1/health",
                    headers={"X-Correlation-ID": f"concurrent-id-{index}"},
                )
                for index in range(8)
            ]
        )

    returned = [response.headers["x-correlation-id"] for response in responses]
    assert returned == [f"concurrent-id-{index}" for index in range(8)]


async def test_request_completion_log_uses_path_only() -> None:
    records: list[logging.LogRecord] = []

    class RecordingHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = RecordingHandler()
    handler.addFilter(CorrelationIdFilter())
    logger = logging.getLogger("energy_trading.api.http")
    logger.addHandler(handler)
    try:
        async with api_client() as client:
            await client.get(
                "/api/v1/health",
                params={"token": "super-secret-test-value"},
                headers={"X-Correlation-ID": "log-path-only"},
            )
    finally:
        logger.removeHandler(handler)

    completion = [
        record for record in records if getattr(record, "event", None) == "http_request_completed"
    ]
    assert completion
    record = completion[0]
    assert record.method == "GET"
    assert record.path == "/api/v1/health"
    assert record.status_code == 200
    payload = json.loads(JsonLogFormatter().format(record))
    dumped = json.dumps(payload)
    assert "super-secret-test-value" not in dumped
    assert "token=" not in dumped
    assert payload["correlation_id"] == "log-path-only"
