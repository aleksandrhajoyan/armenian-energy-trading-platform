"""Shared helpers for live PostgreSQL/TimescaleDB tests."""

from __future__ import annotations

import os
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from energy_trading.domain.models.observations import ConsumptionRecord
from energy_trading.infrastructure.persistence.postgres.tables import consumption_observations

OPT_IN_ENV = "ENERGY_RUN_POSTGRES_INTEGRATION"


def postgres_integration_enabled() -> bool:
    return os.environ.get(OPT_IN_ENV) == "1"


async def delete_consumer_rows(
    session_factory: async_sessionmaker[AsyncSession],
    consumer_id: str,
) -> None:
    async with session_factory() as session:
        async with session.begin():
            await session.execute(
                delete(consumption_observations).where(
                    consumption_observations.c.consumer_id == consumer_id
                )
            )


async def fetch_consumer_rows(
    session_factory: async_sessionmaker[AsyncSession],
    consumer_id: str,
) -> list[ConsumptionRecord]:
    async with session_factory() as session:
        result = await session.execute(
            select(consumption_observations)
            .where(consumption_observations.c.consumer_id == consumer_id)
            .order_by(consumption_observations.c.timestamp)
        )
        return [
            ConsumptionRecord.model_validate(
                {
                    "consumer_id": row["consumer_id"],
                    "timestamp": row["timestamp"],
                    "value_mw": row["value_mw"],
                }
            )
            for row in result.mappings()
        ]


def consumption_record(
    *,
    consumer_id: str,
    timestamp: datetime,
    value_mw: float,
) -> ConsumptionRecord:
    return ConsumptionRecord(
        consumer_id=consumer_id,
        timestamp=timestamp,
        value_mw=value_mw,
    )
