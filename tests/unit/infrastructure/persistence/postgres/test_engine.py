"""Unit tests for async PostgreSQL engine and session factories.

No live PostgreSQL process is required.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from energy_trading.infrastructure.persistence.postgres.engine import (
    build_postgres_url,
    create_postgres_engine,
    create_session_factory,
)
from energy_trading.shared.config.database import DatabaseSettings
from tests.architecture.import_inspection import SRC_ROOT

SENTINEL_PASSWORD = "sentinel-db-password-chunk13"
ENGINE_PATH = (
    SRC_ROOT / "energy_trading" / "infrastructure" / "persistence" / "postgres" / "engine.py"
)
PACKAGE_INIT_PATH = ENGINE_PATH.with_name("__init__.py")


@pytest.fixture(autouse=True)
def clear_database_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "ENERGY_DB_HOST",
        "ENERGY_DB_PORT",
        "ENERGY_DB_DATABASE",
        "ENERGY_DB_USERNAME",
        "ENERGY_DB_PASSWORD",
        "ENERGY_DB_POOL_SIZE",
        "ENERGY_DB_MAX_OVERFLOW",
        "ENERGY_DB_POOL_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(key, raising=False)


def _settings(**overrides: object) -> DatabaseSettings:
    payload: dict[str, object] = {
        "host": "db.example.invalid",
        "port": 5432,
        "database": "energy_trading",
        "username": "energy_trading",
        "password": SENTINEL_PASSWORD,
        "pool_size": 7,
        "max_overflow": 2,
        "pool_timeout_seconds": 11.5,
    }
    payload.update(overrides)
    return DatabaseSettings(_env_file=None, **payload)


def test_build_postgres_url_uses_psycopg_driver() -> None:
    url = build_postgres_url(_settings())
    assert isinstance(url, URL)
    assert url.drivername == "postgresql+psycopg"


def test_build_postgres_url_contains_connection_semantics() -> None:
    url = build_postgres_url(_settings(host="timescale.internal", port=6543, database="market"))
    assert url.host == "timescale.internal"
    assert url.port == 6543
    assert url.database == "market"
    assert url.username == "energy_trading"


def test_build_postgres_url_keeps_password_for_connection() -> None:
    url = build_postgres_url(_settings())
    assert url.password == SENTINEL_PASSWORD


def test_build_postgres_url_safe_representation_hides_password() -> None:
    url = build_postgres_url(_settings())
    safe = url.render_as_string(hide_password=True)
    assert SENTINEL_PASSWORD not in safe
    assert SENTINEL_PASSWORD not in repr(url)
    assert SENTINEL_PASSWORD not in str(url)


async def test_create_postgres_engine_returns_async_engine_without_connecting() -> None:
    engine = create_postgres_engine(_settings())
    try:
        assert isinstance(engine, AsyncEngine)
        assert engine.pool.checkedout() == 0
    finally:
        await engine.dispose()


def test_create_postgres_engine_enables_pool_pre_ping() -> None:
    tree = ast.parse(ENGINE_PATH.read_text(encoding="utf-8"), filename=str(ENGINE_PATH))
    found = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = ""
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        if name != "create_async_engine":
            continue
        for keyword in node.keywords:
            if keyword.arg == "pool_pre_ping" and isinstance(keyword.value, ast.Constant):
                found = keyword.value.value is True
    assert found is True


async def test_create_postgres_engine_uses_pool_settings() -> None:
    engine = create_postgres_engine(_settings())
    try:
        pool = engine.sync_engine.pool
        assert pool.size() == 7
        max_overflow = getattr(pool, "_max_overflow", None)
        if max_overflow is not None:
            assert max_overflow == 2
        pre_ping = getattr(pool, "_pre_ping", None)
        if pre_ping is not None:
            assert pre_ping is True
    finally:
        await engine.dispose()


async def test_session_factory_produces_async_sessions_without_expire_on_commit() -> None:
    engine = create_postgres_engine(_settings())
    try:
        factory = create_session_factory(engine)
        assert isinstance(factory, async_sessionmaker)
        assert factory.kw["expire_on_commit"] is False
        session = factory()
        try:
            assert isinstance(session, AsyncSession)
            assert session.sync_session.expire_on_commit is False
        finally:
            await session.close()
    finally:
        await engine.dispose()


def _module_level_call_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            func = child.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                names.add(func.attr)
    return names


def test_no_module_global_engine_is_created() -> None:
    engine_calls = _module_level_call_names(ENGINE_PATH)
    package_calls = _module_level_call_names(PACKAGE_INIT_PATH)
    forbidden = {"create_async_engine", "create_postgres_engine", "create_session_factory"}
    assert engine_calls.isdisjoint(forbidden)
    assert package_calls.isdisjoint(forbidden)
