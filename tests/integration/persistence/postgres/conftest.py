"""Fixtures for the opt-in live PostgreSQL/TimescaleDB suite.

These tests require the Compose ``postgres`` profile and
``ENERGY_RUN_POSTGRES_INTEGRATION=1``. They use the production
``DatabaseSettings`` / engine / session / repository stack.
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from energy_trading.infrastructure.persistence.postgres.consumption_repository import (
    PostgresConsumptionRepository,
)
from energy_trading.infrastructure.persistence.postgres.engine import (
    create_postgres_engine,
    create_session_factory,
)
from energy_trading.shared.config.database import DatabaseSettings, load_database_settings
from tests.integration.persistence.postgres._support import delete_consumer_rows

pytestmark = pytest.mark.postgres_integration


@pytest.fixture
def event_loop_policy() -> asyncio.AbstractEventLoopPolicy:
    if sys.platform == "win32":
        return asyncio.WindowsSelectorEventLoopPolicy()
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture
def db_settings() -> DatabaseSettings:
    return load_database_settings()


@pytest.fixture
async def postgres_engine(db_settings: DatabaseSettings) -> AsyncIterator[AsyncEngine]:
    engine = create_postgres_engine(db_settings)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
def session_factory(postgres_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(postgres_engine)


@pytest.fixture
def repository(session_factory: async_sessionmaker[AsyncSession]) -> PostgresConsumptionRepository:
    return PostgresConsumptionRepository(session_factory)


@pytest.fixture
def unique_consumer_id() -> str:
    return f"chunk15-{uuid4()}"


@pytest.fixture
async def owned_consumer_id(
    session_factory: async_sessionmaker[AsyncSession],
    unique_consumer_id: str,
) -> AsyncIterator[str]:
    try:
        yield unique_consumer_id
    finally:
        await delete_consumer_rows(session_factory, unique_consumer_id)
