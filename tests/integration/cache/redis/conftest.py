"""Fixtures for the opt-in live Redis cache suite.

These tests require the Compose ``redis`` profile and
``ENERGY_RUN_REDIS_INTEGRATION=1``. They use the production
``RedisSettings`` / client factory / ``RedisCache`` stack.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
from redis.asyncio import Redis

from energy_trading.infrastructure.cache.codec import CacheCodec, CacheCodecError
from energy_trading.infrastructure.cache.redis_cache import RedisCache
from energy_trading.infrastructure.cache.redis_client import create_redis_client
from energy_trading.shared.config.redis import RedisSettings, load_redis_settings

OPT_IN_ENV = "ENERGY_RUN_REDIS_INTEGRATION"
LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost"})

pytestmark = pytest.mark.redis_integration


def redis_integration_enabled() -> bool:
    return os.environ.get(OPT_IN_ENV) == "1"


class _Utf8StringCodec:
    """Test-only UTF-8 string codec. Not a production serializer."""

    def encode(self, value: str) -> bytes:
        if not isinstance(value, str):
            raise CacheCodecError("expected str")
        return value.encode("utf-8")

    def decode(self, payload: bytes) -> str:
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CacheCodecError("unable to decode utf-8 string") from exc


def _as_string_codec(codec: _Utf8StringCodec) -> CacheCodec[str]:
    return codec


@pytest.fixture
def redis_settings() -> RedisSettings:
    if not redis_integration_enabled():
        pytest.skip(f"{OPT_IN_ENV}=1 is required")
    settings = load_redis_settings()
    host = settings.host.strip().lower()
    if host not in LOCAL_HOSTS:
        pytest.fail("Redis live tests accept only 127.0.0.1 or localhost as REDIS_HOST.")
    if settings.password is None:
        pytest.fail("Local Compose Redis live tests require a non-empty REDIS_PASSWORD.")
    if settings.ssl:
        pytest.fail("Local Compose Redis live tests require REDIS_SSL=false.")
    return settings


@pytest.fixture
async def redis_client(redis_settings: RedisSettings) -> AsyncIterator[Redis]:
    client = create_redis_client(redis_settings)
    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture
def string_codec() -> CacheCodec[str]:
    return _as_string_codec(_Utf8StringCodec())


@pytest.fixture
def cache(redis_client: Redis, string_codec: CacheCodec[str]) -> RedisCache[str]:
    return RedisCache(redis_client, string_codec)


@pytest.fixture
async def owned_keys(cache: RedisCache[str]) -> AsyncIterator[list[str]]:
    keys: list[str] = []
    try:
        yield keys
    finally:
        for key in keys:
            await cache.delete(key)
