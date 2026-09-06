"""Fixtures for the opt-in live Qdrant document-vector suite.

These tests require the Compose ``qdrant`` profile and
``ENERGY_RUN_QDRANT_INTEGRATION=1``. They use the production
``QdrantSettings`` / ``create_qdrant_client()`` /
``QdrantDocumentVectorIndex`` / ``QdrantDocumentVectorSearch`` stack.

Temporary collections are created only in this test package. Vector size 3
and ``Distance.DOT`` are test-fixture configuration, not production
embedding-metric selection.
"""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import AsyncIterator
from uuid import uuid4

import httpx
import pytest
from qdrant_client import AsyncQdrantClient
from qdrant_client.common.client_exceptions import ResourceExhaustedResponse
from qdrant_client.http import models
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

from energy_trading.infrastructure.vector_store.qdrant.client import create_qdrant_client
from energy_trading.infrastructure.vector_store.qdrant.document_vector import (
    QdrantDocumentVectorConfig,
)
from energy_trading.shared.config.qdrant import QdrantSettings, load_qdrant_settings

OPT_IN_ENV = "ENERGY_RUN_QDRANT_INTEGRATION"
LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost"})
READINESS_TIMEOUT_SECONDS = 30.0
READINESS_POLL_SECONDS = 0.25
TEST_VECTOR_SIZE = 3
AUTH_FAILURE_STATUSES = frozenset({401, 403})

pytestmark = pytest.mark.qdrant_integration


def qdrant_integration_enabled() -> bool:
    return os.environ.get(OPT_IN_ENV) == "1"


async def wait_for_qdrant_ready(
    client: AsyncQdrantClient,
    *,
    timeout_seconds: float = READINESS_TIMEOUT_SECONDS,
) -> None:
    """Poll a harmless authenticated Qdrant operation with a bounded timeout."""

    deadline = time.monotonic() + timeout_seconds
    last_error_type = "no-attempt"
    while time.monotonic() < deadline:
        try:
            await client.get_collections()
            return
        except UnexpectedResponse as exc:
            if getattr(exc, "status_code", None) in AUTH_FAILURE_STATUSES:
                pytest.fail("Qdrant rejected the authenticated client during readiness.")
            last_error_type = type(exc).__name__
        except (
            ResponseHandlingException,
            ResourceExhaustedResponse,
            httpx.HTTPError,
            OSError,
            TimeoutError,
        ) as exc:
            last_error_type = type(exc).__name__
        await asyncio.sleep(READINESS_POLL_SECONDS)
    pytest.fail(f"Qdrant did not become ready within the bounded timeout ({last_error_type}).")


@pytest.fixture
def qdrant_settings() -> QdrantSettings:
    if not qdrant_integration_enabled():
        pytest.skip(f"{OPT_IN_ENV}=1 is required")
    settings = load_qdrant_settings()
    host = settings.host.strip().lower()
    if host not in LOCAL_HOSTS:
        pytest.fail("Qdrant live tests accept only 127.0.0.1 or localhost as QDRANT_HOST.")
    if settings.api_key is None:
        pytest.fail("Local Compose Qdrant live tests require a non-empty QDRANT_API_KEY.")
    if settings.https:
        pytest.fail("Local Compose Qdrant live tests require QDRANT_HTTPS=false.")
    return settings


@pytest.fixture
async def qdrant_client(qdrant_settings: QdrantSettings) -> AsyncIterator[AsyncQdrantClient]:
    client = create_qdrant_client(qdrant_settings)
    try:
        await wait_for_qdrant_ready(client)
        yield client
    finally:
        await client.close()


@pytest.fixture
async def qdrant_config(
    qdrant_client: AsyncQdrantClient,
) -> AsyncIterator[QdrantDocumentVectorConfig]:
    collection_name = f"chunk24-live-{uuid4()}"
    await qdrant_client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(
            size=TEST_VECTOR_SIZE,
            distance=models.Distance.DOT,
        ),
    )
    config = QdrantDocumentVectorConfig(
        collection_name=collection_name,
        vector_size=TEST_VECTOR_SIZE,
    )
    try:
        yield config
    except BaseException:
        try:
            await qdrant_client.delete_collection(collection_name=collection_name)
        except Exception:
            pass
        raise
    else:
        await qdrant_client.delete_collection(collection_name=collection_name)
