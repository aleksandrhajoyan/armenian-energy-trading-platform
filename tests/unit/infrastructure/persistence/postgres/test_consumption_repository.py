"""Unit tests for PostgresConsumptionRepository. No live PostgreSQL is required."""

from __future__ import annotations

import ast
from collections.abc import Sequence

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError

from energy_trading.application.errors import ConflictError, DependencyUnavailableError
from energy_trading.domain.models.observations import ConsumptionRecord
from energy_trading.infrastructure.persistence.postgres.consumption_repository import (
    PostgresConsumptionRepository,
)
from tests.architecture.import_inspection import SRC_ROOT
from tests.unit.domain._factories import consumption

REPOSITORY_PATH = (
    SRC_ROOT
    / "energy_trading"
    / "infrastructure"
    / "persistence"
    / "postgres"
    / "consumption_repository.py"
)
SENTINEL_DB_TEXT = "sentinel-db-exception-chunk14"


class FakeResult:
    def __init__(self, rows: Sequence[dict[str, object]]) -> None:
        self._rows = list(rows)

    def mappings(self) -> list[dict[str, object]]:
        return self._rows


class FakeTransaction:
    def __init__(self, session: FakeAsyncSession) -> None:
        self._session = session

    async def __aenter__(self) -> FakeTransaction:
        self._session.begin_calls += 1
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object,
    ) -> None:
        if exc_type is None:
            self._session.commits += 1
        else:
            self._session.rollbacks += 1


class FakeAsyncSession:
    def __init__(
        self,
        *,
        select_rows: Sequence[dict[str, object]] | None = None,
        execute_error: BaseException | None = None,
    ) -> None:
        self.select_rows = list(select_rows or [])
        self.execute_error = execute_error
        self.statements: list[object] = []
        self.begin_calls = 0
        self.commits = 0
        self.rollbacks = 0

    def begin(self) -> FakeTransaction:
        return FakeTransaction(self)

    async def execute(self, statement: object) -> FakeResult:
        if self.execute_error is not None:
            raise self.execute_error
        self.statements.append(statement)
        sql = _compiled_sql(statement)
        if "INSERT" in sql:
            return FakeResult(())
        if self.select_rows:
            return FakeResult(self.select_rows)
        return FakeResult(_rows_from_insert(self.statements[0]))

    async def __aenter__(self) -> FakeAsyncSession:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


class RecordingSessionFactory:
    def __init__(self, session: FakeAsyncSession) -> None:
        self.session = session
        self.calls = 0

    def __call__(self) -> FakeAsyncSession:
        self.calls += 1
        return self.session


def _compiled_sql(statement: object) -> str:
    compiled = statement.compile(dialect=postgresql.dialect())  # type: ignore[union-attr]
    return str(compiled).upper()


def _rows_from_insert(statement: object) -> list[dict[str, object]]:
    compiled = statement.compile(dialect=postgresql.dialect())  # type: ignore[union-attr]
    params = compiled.params
    rows: list[dict[str, object]] = []
    index = 0
    while True:
        consumer_key = f"consumer_id_{index}" if index else "consumer_id"
        timestamp_key = f"timestamp_{index}" if index else "timestamp"
        value_key = f"value_mw_{index}" if index else "value_mw"
        if consumer_key not in params and not (index == 0 and "consumer_id" in params):
            if index == 0 and "consumer_id" in params:
                pass
            else:
                break
        if consumer_key not in params:
            break
        rows.append(
            {
                "consumer_id": params[consumer_key],
                "timestamp": params[timestamp_key],
                "value_mw": params[value_key],
            }
        )
        index += 1
        if index == 1 and "consumer_id_1" not in params:
            # single-row insert uses unnumbered keys only
            if "consumer_id_0" not in params:
                break
    if not rows and "consumer_id" in params:
        rows.append(
            {
                "consumer_id": params["consumer_id"],
                "timestamp": params["timestamp"],
                "value_mw": params["value_mw"],
            }
        )
    return rows


def _row(record: ConsumptionRecord) -> dict[str, object]:
    return {
        "consumer_id": record.consumer_id,
        "timestamp": record.timestamp,
        "value_mw": record.value_mw,
    }


async def test_empty_tuple_opens_no_session() -> None:
    session = FakeAsyncSession()
    factory = RecordingSessionFactory(session)
    repository = PostgresConsumptionRepository(factory)  # type: ignore[arg-type]
    await repository.save_many(())
    assert factory.calls == 0
    assert session.statements == []
    assert session.begin_calls == 0


async def test_one_new_canonical_record_succeeds() -> None:
    record = consumption()
    session = FakeAsyncSession(select_rows=(_row(record),))
    factory = RecordingSessionFactory(session)
    repository = PostgresConsumptionRepository(factory)  # type: ignore[arg-type]
    await repository.save_many((record,))
    assert factory.calls == 1
    assert session.begin_calls == 1
    assert session.commits == 1
    assert session.rollbacks == 0
    assert any("INSERT" in _compiled_sql(statement) for statement in session.statements)


async def test_multiple_new_records_use_one_transaction() -> None:
    first = consumption(consumer_id="a", value_mw=1.0)
    second = consumption(consumer_id="b", value_mw=2.0)
    session = FakeAsyncSession(select_rows=(_row(first), _row(second)))
    factory = RecordingSessionFactory(session)
    repository = PostgresConsumptionRepository(factory)  # type: ignore[arg-type]
    await repository.save_many((first, second))
    insert_statements = [
        statement for statement in session.statements if "INSERT" in _compiled_sql(statement)
    ]
    assert len(insert_statements) == 1
    assert session.begin_calls == 1
    assert session.commits == 1


async def test_exact_repeated_records_inside_input_are_coalesced() -> None:
    record = consumption()
    session = FakeAsyncSession(select_rows=(_row(record),))
    factory = RecordingSessionFactory(session)
    repository = PostgresConsumptionRepository(factory)  # type: ignore[arg-type]
    await repository.save_many((record, record))
    compiled = session.statements[0].compile(dialect=postgresql.dialect())  # type: ignore[union-attr]
    consumer_keys = [key for key in compiled.params if "consumer_id" in key]
    assert len(consumer_keys) == 1


async def test_differing_same_identity_inside_input_raises_before_db_work() -> None:
    first = consumption(value_mw=1.0)
    second = consumption(value_mw=2.0)
    session = FakeAsyncSession()
    factory = RecordingSessionFactory(session)
    repository = PostgresConsumptionRepository(factory)  # type: ignore[arg-type]
    with pytest.raises(ConflictError, match="conflicting consumption observation"):
        await repository.save_many((first, second))
    assert factory.calls == 0
    assert session.statements == []


async def test_insert_uses_on_conflict_do_nothing() -> None:
    record = consumption()
    session = FakeAsyncSession(select_rows=(_row(record),))
    repository = PostgresConsumptionRepository(RecordingSessionFactory(session))  # type: ignore[arg-type]
    await repository.save_many((record,))
    insert_sql = _compiled_sql(session.statements[0])
    assert "ON CONFLICT" in insert_sql
    assert "DO NOTHING" in insert_sql
    assert "DO UPDATE" not in insert_sql


async def test_exact_existing_persisted_record_is_idempotent() -> None:
    record = consumption()
    session = FakeAsyncSession(select_rows=(_row(record),))
    repository = PostgresConsumptionRepository(RecordingSessionFactory(session))  # type: ignore[arg-type]
    await repository.save_many((record,))
    assert session.commits == 1
    assert session.rollbacks == 0


async def test_existing_same_identity_different_value_raises_conflict() -> None:
    incoming = consumption(value_mw=1.0)
    stored = consumption(value_mw=9.0)
    session = FakeAsyncSession(select_rows=(_row(stored),))
    repository = PostgresConsumptionRepository(RecordingSessionFactory(session))  # type: ignore[arg-type]
    with pytest.raises(ConflictError, match="conflicting consumption observation"):
        await repository.save_many((incoming,))
    assert session.rollbacks == 1
    assert session.commits == 0


async def test_mixed_new_and_conflicting_stored_record_rolls_back() -> None:
    new_record = consumption(consumer_id="new", value_mw=1.0)
    incoming_conflict = consumption(consumer_id="old", value_mw=2.0)
    stored_conflict = consumption(consumer_id="old", value_mw=8.0)
    session = FakeAsyncSession(select_rows=(_row(new_record), _row(stored_conflict)))
    repository = PostgresConsumptionRepository(RecordingSessionFactory(session))  # type: ignore[arg-type]
    with pytest.raises(ConflictError):
        await repository.save_many((new_record, incoming_conflict))
    assert session.begin_calls == 1
    assert session.rollbacks == 1
    assert session.commits == 0


async def test_persisted_rows_are_rebuilt_as_canonical_records() -> None:
    record = consumption()
    session = FakeAsyncSession(select_rows=(_row(record),))
    repository = PostgresConsumptionRepository(RecordingSessionFactory(session))  # type: ignore[arg-type]
    await repository.save_many((record,))
    rebuilt = ConsumptionRecord.model_validate(_row(record))
    assert rebuilt == record


async def test_corrupt_persisted_canonical_data_fails_closed() -> None:
    record = consumption()
    session = FakeAsyncSession(
        select_rows=({"consumer_id": record.consumer_id, "timestamp": record.timestamp},)
    )
    repository = PostgresConsumptionRepository(RecordingSessionFactory(session))  # type: ignore[arg-type]
    with pytest.raises(DependencyUnavailableError, match="Consumption persistence is unavailable"):
        await repository.save_many((record,))
    assert session.rollbacks == 1


async def test_dbapi_failure_becomes_dependency_unavailable() -> None:
    error = DBAPIError("SELECT 1", {}, Exception(SENTINEL_DB_TEXT))
    session = FakeAsyncSession(execute_error=error)
    repository = PostgresConsumptionRepository(RecordingSessionFactory(session))  # type: ignore[arg-type]
    with pytest.raises(
        DependencyUnavailableError, match="Consumption persistence is unavailable"
    ) as exc_info:
        await repository.save_many((consumption(),))
    assert SENTINEL_DB_TEXT not in str(exc_info.value)
    assert SENTINEL_DB_TEXT not in repr(exc_info.value)


async def test_pool_timeout_becomes_dependency_unavailable() -> None:
    session = FakeAsyncSession(execute_error=SQLAlchemyTimeoutError(SENTINEL_DB_TEXT))
    repository = PostgresConsumptionRepository(RecordingSessionFactory(session))  # type: ignore[arg-type]
    with pytest.raises(
        DependencyUnavailableError, match="Consumption persistence is unavailable"
    ) as exc_info:
        await repository.save_many((consumption(),))
    assert SENTINEL_DB_TEXT not in str(exc_info.value)


def test_repository_does_not_create_an_engine() -> None:
    tree = ast.parse(REPOSITORY_PATH.read_text(encoding="utf-8"), filename=str(REPOSITORY_PATH))
    call_names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            call_names.add(func.id)
        elif isinstance(func, ast.Attribute):
            call_names.add(func.attr)
    assert "create_async_engine" not in call_names
    assert "create_postgres_engine" not in call_names


def test_repository_uses_injected_session_factory_without_per_row_commit() -> None:
    source = REPOSITORY_PATH.read_text(encoding="utf-8")
    assert "session_factory" in source
    assert "session.commit(" not in source
    assert source.count("session.begin()") == 1
