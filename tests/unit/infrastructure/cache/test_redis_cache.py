"""Unit tests for RedisCache against a fake Redis command surface.

No network, fakeredis, Docker, or live Redis process is used.
"""

from __future__ import annotations

import hashlib
import inspect
from datetime import timedelta

import pytest
from redis.exceptions import RedisError

from energy_trading.application.errors import DependencyUnavailableError, InvalidRequestError
from energy_trading.application.ports import CachePort
from energy_trading.domain.models import ConsumptionRecord
from energy_trading.infrastructure.cache.codec import CacheCodec, CacheCodecError
from energy_trading.infrastructure.cache.redis_cache import RedisCache
from tests.unit.domain._factories import consumption

KEY_SENTINEL = "raw-application-key-sentinel-chunk17"
PAYLOAD_SENTINEL = b"raw-cached-payload-sentinel-chunk17"
REDIS_ERROR_SENTINEL = "redis-error-sentinel-chunk17"
CODEC_ERROR_SENTINEL = "codec-error-sentinel-chunk17"


class _FakeRedisError(RedisError):
    """Test-only Redis failure carrying a sentinel message."""


class _FakeRedis:
    """In-memory Redis command double. Not fakeredis and not a production client."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []
        self.get_result: object = None
        self.set_result: object = True
        self.delete_result: object = 0
        self.get_error: Exception | None = None
        self.set_error: Exception | None = None
        self.delete_error: Exception | None = None

    async def get(self, name: object) -> object:
        self.calls.append(("get", (name,), {}))
        if self.get_error is not None:
            raise self.get_error
        return self.get_result

    async def set(self, name: object, value: object, **kwargs: object) -> object:
        self.calls.append(("set", (name, value), kwargs))
        if self.set_error is not None:
            raise self.set_error
        return self.set_result

    async def delete(self, *names: object) -> object:
        self.calls.append(("delete", names, {}))
        if self.delete_error is not None:
            raise self.delete_error
        return self.delete_result


class _ConsumptionRecordCodec:
    def encode(self, value: ConsumptionRecord) -> bytes:
        return value.model_dump_json().encode("utf-8")

    def decode(self, payload: bytes) -> ConsumptionRecord:
        return ConsumptionRecord.model_validate_json(payload)


class _FailingEncodeCodec:
    def encode(self, value: ConsumptionRecord) -> bytes:
        raise CacheCodecError(CODEC_ERROR_SENTINEL)

    def decode(self, payload: bytes) -> ConsumptionRecord:
        return ConsumptionRecord.model_validate_json(payload)


class _FailingDecodeCodec:
    def encode(self, value: ConsumptionRecord) -> bytes:
        return value.model_dump_json().encode("utf-8")

    def decode(self, payload: bytes) -> ConsumptionRecord:
        raise CacheCodecError(CODEC_ERROR_SENTINEL)


def _backend_key(application_key: str) -> str:
    digest = hashlib.sha256(application_key.encode("utf-8")).hexdigest()
    return f"energy-trading:cache:{digest}"


def _cache(
    redis: _FakeRedis | None = None,
    codec: CacheCodec[ConsumptionRecord] | None = None,
) -> tuple[_FakeRedis, RedisCache[ConsumptionRecord]]:
    client = redis or _FakeRedis()
    adapter = RedisCache(client, codec or _ConsumptionRecordCodec())
    return client, adapter


def _as_port(cache: RedisCache[ConsumptionRecord]) -> CachePort[ConsumptionRecord]:
    return cache


def test_redis_cache_structurally_satisfies_cache_port() -> None:
    _client, cache = _cache()
    port = _as_port(cache)
    assert inspect.iscoroutinefunction(port.get)
    assert inspect.iscoroutinefunction(port.set)
    assert inspect.iscoroutinefunction(port.delete)


async def test_missing_get_returns_none() -> None:
    _client, cache = _cache()
    assert await cache.get("canonical-consumption") is None


async def test_get_decodes_bytes_to_typed_value() -> None:
    record = consumption()
    client, cache = _cache()
    client.get_result = record.model_dump_json().encode("utf-8")
    loaded = await cache.get("canonical-consumption")
    assert loaded == record
    assert isinstance(loaded, ConsumptionRecord)


async def test_set_encodes_value_and_uses_hashed_backend_key() -> None:
    record = consumption()
    client, cache = _cache()
    await cache.set("canonical-consumption", record, ttl=timedelta(seconds=1))
    assert client.calls[0][0] == "set"
    name, value = client.calls[0][1]
    assert name == _backend_key("canonical-consumption")
    assert value == record.model_dump_json().encode("utf-8")
    assert client.calls[0][2]["px"] == 1000


async def test_raw_application_key_is_not_sent_to_redis() -> None:
    client, cache = _cache()
    await cache.set(KEY_SENTINEL, consumption(), ttl=timedelta(milliseconds=1))
    name = client.calls[0][1][0]
    assert name != KEY_SENTINEL
    assert KEY_SENTINEL not in str(name)
    assert name == _backend_key(KEY_SENTINEL)


async def test_surrounding_key_whitespace_normalizes_consistently() -> None:
    client, cache = _cache()
    await cache.set("  canonical-consumption  ", consumption(), ttl=timedelta(seconds=1))
    await cache.get("\tcanonical-consumption\n")
    await cache.delete(" canonical-consumption ")
    expected = _backend_key("canonical-consumption")
    assert client.calls[0][1][0] == expected
    assert client.calls[1][1][0] == expected
    assert client.calls[2][1][0] == expected


async def test_same_normalized_key_derives_the_same_backend_key() -> None:
    first = _backend_key("canonical-consumption")
    second = _backend_key("canonical-consumption")
    assert first == second
    client, cache = _cache()
    await cache.set("canonical-consumption", consumption(), ttl=timedelta(seconds=1))
    await cache.set("canonical-consumption", consumption(value_mw=2.0), ttl=timedelta(seconds=2))
    assert client.calls[0][1][0] == first
    assert client.calls[1][1][0] == first


async def test_set_uses_px_milliseconds() -> None:
    client, cache = _cache()
    await cache.set("canonical-consumption", consumption(), ttl=timedelta(milliseconds=5))
    kwargs = client.calls[0][2]
    assert "px" in kwargs
    assert "ex" not in kwargs
    assert kwargs["px"] == 5


@pytest.mark.parametrize(
    ("ttl", "expected_px"),
    [
        (timedelta(microseconds=1), 1),
        (timedelta(milliseconds=1), 1),
        (timedelta(microseconds=1500), 2),
        (timedelta(seconds=1), 1000),
    ],
)
async def test_ttl_converts_to_ceil_milliseconds(ttl: timedelta, expected_px: int) -> None:
    client, cache = _cache()
    await cache.set("canonical-consumption", consumption(), ttl=ttl)
    assert client.calls[0][2]["px"] == expected_px


async def test_overwrite_calls_set_again_with_new_ttl() -> None:
    client, cache = _cache()
    first = consumption(value_mw=1.0)
    second = consumption(value_mw=2.0)
    await cache.set("canonical-consumption", first, ttl=timedelta(seconds=1))
    await cache.set("canonical-consumption", second, ttl=timedelta(seconds=5))
    assert len([call for call in client.calls if call[0] == "set"]) == 2
    assert client.calls[1][1][1] == second.model_dump_json().encode("utf-8")
    assert client.calls[1][2]["px"] == 5000


async def test_delete_calls_one_backend_delete() -> None:
    client, cache = _cache()
    await cache.delete("canonical-consumption")
    assert len(client.calls) == 1
    assert client.calls[0][0] == "delete"
    assert client.calls[0][1] == (_backend_key("canonical-consumption"),)


async def test_backend_delete_zero_is_successful() -> None:
    client, cache = _cache()
    client.delete_result = 0
    await cache.delete("missing-key")


@pytest.mark.parametrize("key", ["", "   ", "\t", "\n"])
async def test_blank_key_raises_invalid_request_error(key: str) -> None:
    client, cache = _cache()
    with pytest.raises(InvalidRequestError, match="Cache key must be a non-empty string"):
        await cache.get(key)
    with pytest.raises(InvalidRequestError, match="Cache key must be a non-empty string"):
        await cache.set(key, consumption(), ttl=timedelta(seconds=1))
    with pytest.raises(InvalidRequestError, match="Cache key must be a non-empty string"):
        await cache.delete(key)
    assert client.calls == []


async def test_zero_ttl_raises_invalid_request_error() -> None:
    client, cache = _cache()
    with pytest.raises(InvalidRequestError, match="Cache TTL must be greater than zero"):
        await cache.set("canonical-consumption", consumption(), ttl=timedelta(0))
    assert client.calls == []


async def test_negative_ttl_raises_invalid_request_error() -> None:
    client, cache = _cache()
    with pytest.raises(InvalidRequestError, match="Cache TTL must be greater than zero"):
        await cache.set("canonical-consumption", consumption(), ttl=timedelta(seconds=-1))
    assert client.calls == []


async def test_redis_get_failure_is_sanitized_dependency_unavailable() -> None:
    client, cache = _cache()
    client.get_error = _FakeRedisError(REDIS_ERROR_SENTINEL)
    with pytest.raises(DependencyUnavailableError, match="Cache is unavailable") as exc_info:
        await cache.get("canonical-consumption")
    assert REDIS_ERROR_SENTINEL not in exc_info.value.message
    assert REDIS_ERROR_SENTINEL not in str(exc_info.value)


async def test_redis_set_failure_is_sanitized_dependency_unavailable() -> None:
    client, cache = _cache()
    client.set_error = _FakeRedisError(REDIS_ERROR_SENTINEL)
    with pytest.raises(DependencyUnavailableError, match="Cache is unavailable") as exc_info:
        await cache.set("canonical-consumption", consumption(), ttl=timedelta(seconds=1))
    assert REDIS_ERROR_SENTINEL not in exc_info.value.message


async def test_redis_delete_failure_is_sanitized_dependency_unavailable() -> None:
    client, cache = _cache()
    client.delete_error = _FakeRedisError(REDIS_ERROR_SENTINEL)
    with pytest.raises(DependencyUnavailableError, match="Cache is unavailable") as exc_info:
        await cache.delete("canonical-consumption")
    assert REDIS_ERROR_SENTINEL not in exc_info.value.message


async def test_codec_encode_failure_is_sanitized_and_skips_backend() -> None:
    client, cache = _cache(codec=_FailingEncodeCodec())
    with pytest.raises(DependencyUnavailableError, match="Cache is unavailable") as exc_info:
        await cache.set("canonical-consumption", consumption(), ttl=timedelta(seconds=1))
    assert CODEC_ERROR_SENTINEL not in exc_info.value.message
    assert client.calls == []


async def test_codec_decode_failure_is_sanitized() -> None:
    client, cache = _cache(codec=_FailingDecodeCodec())
    client.get_result = PAYLOAD_SENTINEL
    with pytest.raises(DependencyUnavailableError, match="Cache is unavailable") as exc_info:
        await cache.get("canonical-consumption")
    assert CODEC_ERROR_SENTINEL not in exc_info.value.message
    assert PAYLOAD_SENTINEL.decode("utf-8") not in exc_info.value.message


async def test_unexpected_non_byte_get_value_fails_closed() -> None:
    client, cache = _cache()
    client.get_result = "not-bytes"
    with pytest.raises(DependencyUnavailableError, match="Cache is unavailable"):
        await cache.get("canonical-consumption")


async def test_unexpected_unsuccessful_set_result_fails_closed() -> None:
    client, cache = _cache()
    client.set_result = False
    with pytest.raises(DependencyUnavailableError, match="Cache is unavailable"):
        await cache.set("canonical-consumption", consumption(), ttl=timedelta(seconds=1))


async def test_error_text_does_not_include_raw_key_or_payload() -> None:
    client, cache = _cache()
    client.get_error = _FakeRedisError(REDIS_ERROR_SENTINEL)
    with pytest.raises(DependencyUnavailableError) as exc_info:
        await cache.get(KEY_SENTINEL)
    message = exc_info.value.message
    assert KEY_SENTINEL not in message
    assert REDIS_ERROR_SENTINEL not in message
    assert PAYLOAD_SENTINEL.decode("utf-8") not in message
