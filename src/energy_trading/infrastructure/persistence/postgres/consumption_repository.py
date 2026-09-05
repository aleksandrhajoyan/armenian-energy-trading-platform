"""Persist canonical Consumption observations in PostgreSQL/TimescaleDB.

This adapter structurally implements ``ConsumptionRepositoryPort``. It does not
create engines, own configuration, or wire ingestion adapters.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from pydantic import ValidationError
from sqlalchemy import select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from energy_trading.application.errors import ConflictError, DependencyUnavailableError
from energy_trading.domain.models.observations import ConsumptionRecord
from energy_trading.infrastructure.persistence.postgres.tables import consumption_observations

_MSG_CONFLICT = "A conflicting consumption observation already exists"
_MSG_UNAVAILABLE = "Consumption persistence is unavailable"

_ConsumptionIdentity = tuple[str, datetime]


class PostgresConsumptionRepository:
    """Atomic, conflict-safe writer for canonical Consumption observations."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def save_many(self, records: tuple[ConsumptionRecord, ...]) -> None:
        """Persist canonical Consumption observations in one transaction."""

        normalized = _normalize(records)
        if not normalized:
            return
        try:
            async with self._session_factory() as session:
                async with session.begin():
                    await _persist(session, normalized)
        except ConflictError:
            raise
        except DependencyUnavailableError:
            raise
        except (SQLAlchemyTimeoutError, DBAPIError) as exc:
            raise DependencyUnavailableError(_MSG_UNAVAILABLE) from exc


def _normalize(records: object) -> tuple[ConsumptionRecord, ...]:
    if not isinstance(records, tuple):
        msg = "records must be a tuple of ConsumptionRecord"
        raise TypeError(msg)

    by_identity: dict[_ConsumptionIdentity, ConsumptionRecord] = {}
    for item in records:
        if not isinstance(item, ConsumptionRecord):
            msg = "records must contain ConsumptionRecord values only"
            raise TypeError(msg)
        record = item
        identity = _identity(record)
        existing = by_identity.get(identity)
        if existing is None:
            by_identity[identity] = record
            continue
        if existing != record:
            raise ConflictError(_MSG_CONFLICT)
    return tuple(by_identity.values())


def _identity(record: ConsumptionRecord) -> _ConsumptionIdentity:
    return (record.consumer_id, record.timestamp)


async def _persist(session: AsyncSession, records: tuple[ConsumptionRecord, ...]) -> None:
    values = [
        {
            "consumer_id": record.consumer_id,
            "timestamp": record.timestamp,
            "value_mw": record.value_mw,
        }
        for record in records
    ]
    insert_statement = (
        insert(consumption_observations)
        .values(values)
        .on_conflict_do_nothing(index_elements=("consumer_id", "timestamp"))
    )
    await session.execute(insert_statement)

    identities = [_identity(record) for record in records]
    select_statement = select(consumption_observations).where(
        tuple_(
            consumption_observations.c.consumer_id,
            consumption_observations.c.timestamp,
        ).in_(identities)
    )
    result = await session.execute(select_statement)
    persisted_by_identity: dict[_ConsumptionIdentity, ConsumptionRecord] = {}
    for row in result.mappings():
        persisted = _canonical_from_row(dict(row))
        persisted_by_identity[_identity(persisted)] = persisted

    for record in records:
        stored = persisted_by_identity.get(_identity(record))
        if stored is None:
            raise DependencyUnavailableError(_MSG_UNAVAILABLE)
        if stored != record:
            raise ConflictError(_MSG_CONFLICT)


def _canonical_from_row(row: Mapping[str, object]) -> ConsumptionRecord:
    try:
        return ConsumptionRecord.model_validate(
            {
                "consumer_id": row["consumer_id"],
                "timestamp": row["timestamp"],
                "value_mw": row["value_mw"],
            }
        )
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        raise DependencyUnavailableError(_MSG_UNAVAILABLE) from exc
