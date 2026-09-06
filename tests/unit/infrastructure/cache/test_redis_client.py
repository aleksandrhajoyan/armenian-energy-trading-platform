"""Unit tests for the async Redis client factory.

No live Redis process is required. Tests must not issue GET/SET/DELETE/PING.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from redis.asyncio import Redis
from redis.asyncio.connection import Connection, SSLConnection

from energy_trading.infrastructure.cache.redis_client import create_redis_client
from energy_trading.shared.config.redis import RedisSettings
from tests.architecture.import_inspection import SRC_ROOT

SENTINEL_PASSWORD = "sentinel-redis-password-chunk17"
CLIENT_PATH = SRC_ROOT / "energy_trading" / "infrastructure" / "cache" / "redis_client.py"
PACKAGE_INIT_PATH = CLIENT_PATH.with_name("__init__.py")


@pytest.fixture(autouse=True)
def clear_redis_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "REDIS_HOST",
        "REDIS_PORT",
        "REDIS_DB",
        "REDIS_PASSWORD",
        "REDIS_SSL",
        "REDIS_SOCKET_TIMEOUT_SECONDS",
        "REDIS_MAX_CONNECTIONS",
    ):
        monkeypatch.delenv(key, raising=False)


def _settings(**overrides: object) -> RedisSettings:
    payload: dict[str, object] = {
        "host": "cache.example.invalid",
        "port": 6379,
        "db": 0,
        "ssl": False,
        "socket_timeout_seconds": 5.0,
        "max_connections": 10,
    }
    payload.update(overrides)
    return RedisSettings(_env_file=None, **payload)


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


async def test_factory_returns_async_redis_without_network_command() -> None:
    client = create_redis_client(_settings())
    try:
        assert isinstance(client, Redis)
        assert client.connection_pool._available_connections == []
        assert client.connection_pool._in_use_connections == set()
    finally:
        await client.aclose()


async def test_factory_carries_host_port_and_db() -> None:
    client = create_redis_client(_settings(host="redis.internal", port=6380, db=4))
    try:
        kwargs = client.connection_pool.connection_kwargs
        assert kwargs["host"] == "redis.internal"
        assert kwargs["port"] == 6380
        assert kwargs["db"] == 4
    finally:
        await client.aclose()


async def test_password_is_supplied_internally() -> None:
    client = create_redis_client(_settings(password=SENTINEL_PASSWORD))
    try:
        assert client.connection_pool.connection_kwargs["password"] == SENTINEL_PASSWORD
        source = CLIENT_PATH.read_text(encoding="utf-8")
        assert "print(" not in source
        assert "get_secret_value()" in source
    finally:
        await client.aclose()


async def test_ssl_setting_is_propagated() -> None:
    plain = create_redis_client(_settings(ssl=False))
    secured = create_redis_client(_settings(ssl=True))
    try:
        assert issubclass(plain.connection_pool.connection_class, Connection)
        assert not issubclass(plain.connection_pool.connection_class, SSLConnection)
        assert issubclass(secured.connection_pool.connection_class, SSLConnection)
    finally:
        await plain.aclose()
        await secured.aclose()


async def test_timeouts_are_propagated() -> None:
    client = create_redis_client(_settings(socket_timeout_seconds=2.25))
    try:
        kwargs = client.connection_pool.connection_kwargs
        assert kwargs["socket_timeout"] == 2.25
        assert kwargs["socket_connect_timeout"] == 2.25
    finally:
        await client.aclose()


async def test_max_connections_are_propagated() -> None:
    client = create_redis_client(_settings(max_connections=7))
    try:
        assert client.connection_pool.max_connections == 7
    finally:
        await client.aclose()


async def test_decode_responses_is_false() -> None:
    client = create_redis_client(_settings())
    try:
        assert client.connection_pool.connection_kwargs["decode_responses"] is False
    finally:
        await client.aclose()


def test_no_module_global_redis_client_is_created() -> None:
    client_calls = _module_level_call_names(CLIENT_PATH)
    package_calls = _module_level_call_names(PACKAGE_INIT_PATH)
    forbidden = {"Redis", "create_redis_client"}
    assert client_calls.isdisjoint(forbidden)
    assert package_calls.isdisjoint(forbidden)
