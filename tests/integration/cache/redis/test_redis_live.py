"""Live Redis server and RedisCache tests against the Compose redis profile."""

from __future__ import annotations

import asyncio
import time
from datetime import timedelta
from uuid import uuid4

import pytest
from redis.asyncio import Redis
from redis.exceptions import AuthenticationError

from energy_trading.infrastructure.cache.redis_cache import RedisCache
from energy_trading.shared.config.redis import RedisSettings
from tests.integration.cache.redis.conftest import redis_integration_enabled

pytestmark = [
    pytest.mark.redis_integration,
    pytest.mark.skipif(
        not redis_integration_enabled(),
        reason="ENERGY_RUN_REDIS_INTEGRATION=1 is required",
    ),
]

EXPECTED_REDIS_VERSION = "8.2.9"
EXPIRY_TTL = timedelta(milliseconds=250)
EXPIRY_TIMEOUT_SECONDS = 3.0
LONG_TTL = timedelta(seconds=30)


def _unique_key() -> str:
    return f"chunk18-live-{uuid4()}"


def _info_value(info: dict[object, object], name: str) -> str:
    raw = info.get(name, info.get(name.encode("utf-8")))
    if isinstance(raw, bytes):
        return raw.decode("utf-8")
    if isinstance(raw, str):
        return raw
    msg = f"missing Redis INFO field {name}"
    raise AssertionError(msg)


def _config_value(mapping: dict[object, object], name: str) -> str:
    raw = mapping.get(name, mapping.get(name.encode("utf-8")))
    if isinstance(raw, bytes):
        return raw.decode("utf-8")
    if isinstance(raw, str):
        return raw
    msg = f"missing Redis CONFIG field {name}"
    raise AssertionError(msg)


async def _wait_until_missing(cache: RedisCache[str], key: str) -> None:
    deadline = time.monotonic() + EXPIRY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if await cache.get(key) is None:
            return
        await asyncio.sleep(0.05)
    raise AssertionError("cache entry did not expire within the bounded timeout")


async def test_authenticated_ping_returns_pong(redis_client: Redis) -> None:
    # redis-py maps the Redis protocol PONG reply to True.
    result = await redis_client.ping()
    assert result is True


async def test_exact_redis_server_version(redis_client: Redis) -> None:
    info = await redis_client.info("server")
    assert isinstance(info, dict)
    assert _info_value(info, "redis_version") == EXPECTED_REDIS_VERSION


async def test_unauthenticated_command_is_rejected(redis_settings: RedisSettings) -> None:
    unauthenticated = Redis(
        host=redis_settings.host,
        port=redis_settings.port,
        db=redis_settings.db,
        password=None,
        ssl=False,
        decode_responses=False,
    )
    try:
        with pytest.raises(AuthenticationError) as captured:
            await unauthenticated.ping()
        message = str(captured.value)
        secret = redis_settings.password
        assert secret is not None
        assert secret.get_secret_value() not in message
    finally:
        await unauthenticated.aclose()


async def test_appendonly_is_disabled(redis_client: Redis) -> None:
    mapping = await redis_client.config_get("appendonly")
    assert isinstance(mapping, dict)
    assert _config_value(mapping, "appendonly") == "no"


async def test_rdb_snapshot_save_is_disabled(redis_client: Redis) -> None:
    mapping = await redis_client.config_get("save")
    assert isinstance(mapping, dict)
    assert _config_value(mapping, "save") == ""


async def test_set_get_round_trip(
    cache: RedisCache[str],
    owned_keys: list[str],
) -> None:
    key = _unique_key()
    owned_keys.append(key)
    await cache.set(key, "chunk-18-value", ttl=LONG_TTL)
    assert await cache.get(key) == "chunk-18-value"


async def test_missing_key_returns_none(cache: RedisCache[str]) -> None:
    assert await cache.get(_unique_key()) is None


async def test_overwrite_returns_new_value(
    cache: RedisCache[str],
    owned_keys: list[str],
) -> None:
    key = _unique_key()
    owned_keys.append(key)
    await cache.set(key, "first", ttl=LONG_TTL)
    await cache.set(key, "second", ttl=LONG_TTL)
    assert await cache.get(key) == "second"


async def test_overwrite_resets_ttl(
    cache: RedisCache[str],
    owned_keys: list[str],
) -> None:
    key = _unique_key()
    owned_keys.append(key)
    await cache.set(key, "long-lived", ttl=LONG_TTL)
    await cache.set(key, "short-lived", ttl=EXPIRY_TTL)
    await _wait_until_missing(cache, key)
    assert await cache.get(key) is None


async def test_delete_removes_entry(
    cache: RedisCache[str],
    owned_keys: list[str],
) -> None:
    key = _unique_key()
    owned_keys.append(key)
    await cache.set(key, "to-delete", ttl=LONG_TTL)
    await cache.delete(key)
    assert await cache.get(key) is None


async def test_delete_missing_key_succeeds(cache: RedisCache[str]) -> None:
    await cache.delete(_unique_key())


async def test_expired_entry_returns_none(
    cache: RedisCache[str],
    owned_keys: list[str],
) -> None:
    key = _unique_key()
    owned_keys.append(key)
    await cache.set(key, "ephemeral", ttl=EXPIRY_TTL)
    assert await cache.get(key) == "ephemeral"
    await _wait_until_missing(cache, key)
    assert await cache.get(key) is None


async def test_values_are_isolated_by_application_key(
    cache: RedisCache[str],
    owned_keys: list[str],
) -> None:
    first = _unique_key()
    second = _unique_key()
    owned_keys.extend((first, second))
    await cache.set(first, "alpha", ttl=LONG_TTL)
    await cache.set(second, "beta", ttl=LONG_TTL)
    assert await cache.get(first) == "alpha"
    assert await cache.get(second) == "beta"


async def test_surrounding_key_whitespace_is_normalized(
    cache: RedisCache[str],
    owned_keys: list[str],
) -> None:
    logical = _unique_key()
    owned_keys.append(logical)
    await cache.set(f"  {logical}  ", "padded", ttl=LONG_TTL)
    assert await cache.get(logical) == "padded"
    assert await cache.get(f" {logical}") == "padded"
