"""Live n8n service-readiness tests.

These tests require the Compose ``n8n`` profile and
``ENERGY_RUN_N8N_INTEGRATION=1``. They do not create workflows, owners,
or credentials.
"""

from __future__ import annotations

import httpx
import pytest

from tests.integration.infrastructure.orchestration.n8n.conftest import (
    n8n_integration_enabled,
)

pytestmark = [
    pytest.mark.n8n_integration,
    pytest.mark.skipif(
        not n8n_integration_enabled(),
        reason="ENERGY_RUN_N8N_INTEGRATION=1 is required",
    ),
]


async def test_healthz_returns_200(n8n_http_client: httpx.AsyncClient) -> None:
    response = await n8n_http_client.get("/healthz")
    assert response.status_code == 200


async def test_healthz_readiness_returns_200(n8n_http_client: httpx.AsyncClient) -> None:
    response = await n8n_http_client.get("/healthz/readiness")
    assert response.status_code == 200
