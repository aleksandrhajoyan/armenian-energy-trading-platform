"""Live PostgresConsumptionRepository tests against TimescaleDB."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from energy_trading.application.errors import ConflictError
from energy_trading.infrastructure.persistence.postgres.consumption_repository import (
    PostgresConsumptionRepository,
)
from energy_trading.infrastructure.persistence.postgres.tables import consumption_observations
from tests.integration.persistence.postgres._support import (
    consumption_record,
    delete_consumer_rows,
    fetch_consumer_rows,
    postgres_integration_enabled,
)

pytestmark = [
    pytest.mark.postgres_integration,
    pytest.mark.skipif(
        not postgres_integration_enabled(),
        reason="ENERGY_RUN_POSTGRES_INTEGRATION=1 is required",
    ),
]

CONCURRENCY_TIMEOUT_SECONDS = 60.0


async def test_save_many_persists_one_canonical_row(
    repository: PostgresConsumptionRepository,
    session_factory: async_sessionmaker[AsyncSession],
    owned_consumer_id: str,
) -> None:
    instant = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
    record = consumption_record(consumer_id=owned_consumer_id, timestamp=instant, value_mw=1.5)
    await repository.save_many((record,))
    stored = await fetch_consumer_rows(session_factory, owned_consumer_id)
    assert stored == [record]
    assert stored[0].timestamp == instant
    assert stored[0].value_mw == 1.5


async def test_timezone_aware_non_utc_input_round_trips_as_canonical_utc(
    repository: PostgresConsumptionRepository,
    session_factory: async_sessionmaker[AsyncSession],
    owned_consumer_id: str,
) -> None:
    local = datetime(2026, 10, 1, 14, 0, tzinfo=ZoneInfo("Asia/Yerevan"))
    record = consumption_record(consumer_id=owned_consumer_id, timestamp=local, value_mw=2.25)
    assert record.timestamp == datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
    await repository.save_many((record,))
    stored = await fetch_consumer_rows(session_factory, owned_consumer_id)
    assert stored == [record]
    assert stored[0].timestamp == record.timestamp


async def test_exact_retry_is_idempotent_and_keeps_one_row(
    repository: PostgresConsumptionRepository,
    session_factory: async_sessionmaker[AsyncSession],
    owned_consumer_id: str,
) -> None:
    record = consumption_record(
        consumer_id=owned_consumer_id,
        timestamp=datetime(2026, 10, 1, 11, 0, tzinfo=UTC),
        value_mw=3.0,
    )
    await repository.save_many((record,))
    await repository.save_many((record,))
    stored = await fetch_consumer_rows(session_factory, owned_consumer_id)
    assert stored == [record]


async def test_conflicting_value_raises_and_preserves_original(
    repository: PostgresConsumptionRepository,
    session_factory: async_sessionmaker[AsyncSession],
    owned_consumer_id: str,
) -> None:
    instant = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    original = consumption_record(consumer_id=owned_consumer_id, timestamp=instant, value_mw=4.0)
    conflicting = consumption_record(consumer_id=owned_consumer_id, timestamp=instant, value_mw=9.0)
    await repository.save_many((original,))
    with pytest.raises(ConflictError, match="conflicting consumption observation"):
        await repository.save_many((conflicting,))
    stored = await fetch_consumer_rows(session_factory, owned_consumer_id)
    assert stored == [original]


async def test_mixed_batch_conflict_rolls_back_new_row(
    repository: PostgresConsumptionRepository,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    existing_id = f"chunk15-existing-{uuid4()}"
    new_id = f"chunk15-new-{uuid4()}"
    instant = datetime(2026, 10, 1, 13, 0, tzinfo=UTC)
    existing = consumption_record(consumer_id=existing_id, timestamp=instant, value_mw=1.0)
    conflicting = consumption_record(consumer_id=existing_id, timestamp=instant, value_mw=8.0)
    new_record = consumption_record(consumer_id=new_id, timestamp=instant, value_mw=2.0)
    try:
        await repository.save_many((existing,))
        with pytest.raises(ConflictError):
            await repository.save_many((new_record, conflicting))
        assert await fetch_consumer_rows(session_factory, existing_id) == [existing]
        assert await fetch_consumer_rows(session_factory, new_id) == []
    finally:
        await delete_consumer_rows(session_factory, existing_id)
        await delete_consumer_rows(session_factory, new_id)


async def test_concurrent_exact_retry_succeeds_once_physically(
    session_factory: async_sessionmaker[AsyncSession],
    owned_consumer_id: str,
) -> None:
    record = consumption_record(
        consumer_id=owned_consumer_id,
        timestamp=datetime(2026, 10, 1, 14, 0, tzinfo=UTC),
        value_mw=5.5,
    )
    first = PostgresConsumptionRepository(session_factory)
    second = PostgresConsumptionRepository(session_factory)
    results = await asyncio.wait_for(
        asyncio.gather(first.save_many((record,)), second.save_many((record,))),
        timeout=CONCURRENCY_TIMEOUT_SECONDS,
    )
    assert results == [None, None]
    stored = await fetch_consumer_rows(session_factory, owned_consumer_id)
    assert stored == [record]


async def test_concurrent_conflicting_values_keep_one_canonical_row(
    session_factory: async_sessionmaker[AsyncSession],
    owned_consumer_id: str,
) -> None:
    instant = datetime(2026, 10, 1, 15, 0, tzinfo=UTC)
    first_record = consumption_record(
        consumer_id=owned_consumer_id, timestamp=instant, value_mw=1.0
    )
    second_record = consumption_record(
        consumer_id=owned_consumer_id, timestamp=instant, value_mw=2.0
    )
    first = PostgresConsumptionRepository(session_factory)
    second = PostgresConsumptionRepository(session_factory)
    results = await asyncio.wait_for(
        asyncio.gather(
            first.save_many((first_record,)),
            second.save_many((second_record,)),
            return_exceptions=True,
        ),
        timeout=CONCURRENCY_TIMEOUT_SECONDS,
    )
    successes = [item for item in results if item is None]
    conflicts = [item for item in results if isinstance(item, ConflictError)]
    unexpected = [
        item for item in results if item is not None and not isinstance(item, ConflictError)
    ]
    assert len(successes) == 1
    assert len(conflicts) == 1
    assert unexpected == []
    stored = await fetch_consumer_rows(session_factory, owned_consumer_id)
    assert len(stored) == 1
    assert stored[0] in {first_record, second_record}


async def test_direct_sql_rejects_negative_mw(
    session_factory: async_sessionmaker[AsyncSession],
    owned_consumer_id: str,
) -> None:
    instant = datetime(2026, 10, 1, 16, 0, tzinfo=UTC)
    async with session_factory() as session:
        with pytest.raises(IntegrityError):
            async with session.begin():
                await session.execute(
                    insert(consumption_observations).values(
                        consumer_id=owned_consumer_id,
                        timestamp=instant,
                        value_mw=-1.0,
                    )
                )
    assert await fetch_consumer_rows(session_factory, owned_consumer_id) == []
