"""Fixtures for the opt-in live n8n readiness suite.

These tests require the Compose ``n8n`` profile and
``ENERGY_RUN_N8N_INTEGRATION=1``. They contact only loopback HTTP health
endpoints and never log secrets.
"""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import AsyncIterator

import httpx
import pytest

OPT_IN_ENV = "ENERGY_RUN_N8N_INTEGRATION"
DEFAULT_HOST_PORT = 5678
READINESS_TIMEOUT_SECONDS = 60.0
READINESS_POLL_SECONDS = 0.25
READINESS_PATH = "/healthz/readiness"

pytestmark = pytest.mark.n8n_integration


def n8n_integration_enabled() -> bool:
    return os.environ.get(OPT_IN_ENV) == "1"


def n8n_host_port() -> int:
    raw = os.environ.get("N8N_HOST_PORT")
    if raw is None or not raw.strip():
        return DEFAULT_HOST_PORT
    try:
        port = int(raw)
    except ValueError:
        pytest.fail("N8N_HOST_PORT must be an integer.")
    if not 1 <= port <= 65535:
        pytest.fail("N8N_HOST_PORT is out of range.")
    return port


def n8n_base_url() -> str:
    return f"http://127.0.0.1:{n8n_host_port()}"


async def wait_for_n8n_ready(
    client: httpx.AsyncClient,
    *,
    timeout_seconds: float = READINESS_TIMEOUT_SECONDS,
) -> None:
    """Poll n8n readiness with a bounded timeout. Test-only retry loop."""

    deadline = time.monotonic() + timeout_seconds
    last_error_type = "no-attempt"
    while time.monotonic() < deadline:
        try:
            response = await client.get(READINESS_PATH)
            if response.status_code == 200:
                return
            last_error_type = f"HTTP_{response.status_code}"
        except (httpx.HTTPError, OSError, TimeoutError) as exc:
            last_error_type = type(exc).__name__
        await asyncio.sleep(READINESS_POLL_SECONDS)
    pytest.fail(f"n8n did not become ready within the bounded timeout ({last_error_type}).")


@pytest.fixture
async def n8n_http_client() -> AsyncIterator[httpx.AsyncClient]:
    if not n8n_integration_enabled():
        pytest.skip(f"{OPT_IN_ENV}=1 is required")
    async with httpx.AsyncClient(base_url=n8n_base_url(), timeout=2.0) as client:
        await wait_for_n8n_ready(client)
        yield client
