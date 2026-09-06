"""Concrete Redis adapter for the application-owned cache port.

``RedisCache[TValue]`` structurally satisfies ``CachePort[TValue]``. It does
not inherit the protocol, own the shared Redis client, or close that client.
"""

from __future__ import annotations

from datetime import timedelta
from hashlib import sha256

from redis.asyncio import Redis
from redis.exceptions import RedisError

from energy_trading.application.errors import DependencyUnavailableError, InvalidRequestError
from energy_trading.infrastructure.cache.codec import CacheCodec, CacheCodecError

_MSG_INVALID_KEY = "Cache key must be a non-empty string."
_MSG_INVALID_TTL = "Cache TTL must be greater than zero."
_MSG_UNAVAILABLE = "Cache is unavailable"
_BACKEND_KEY_PREFIX = "energy-trading:cache:"


class RedisCache[TValue]:
    """Ordinary TTL-bound Redis cache. Not orchestration state or a lock."""

    def __init__(self, client: Redis, codec: CacheCodec[TValue]) -> None:
        self._client = client
        self._codec = codec

    async def get(self, key: str) -> TValue | None:
        """Return the typed cached value, or ``None`` on miss/expiry."""

        backend_key = _backend_key(_normalize_key(key))
        try:
            payload = await self._client.get(backend_key)
        except RedisError as exc:
            raise DependencyUnavailableError(_MSG_UNAVAILABLE) from exc
        if payload is None:
            return None
        if not isinstance(payload, (bytes, bytearray)):
            raise DependencyUnavailableError(_MSG_UNAVAILABLE)
        try:
            return self._codec.decode(bytes(payload))
        except CacheCodecError as exc:
            raise DependencyUnavailableError(_MSG_UNAVAILABLE) from exc

    async def set(self, key: str, value: TValue, *, ttl: timedelta) -> None:
        """Store ``value`` under ``key`` with millisecond Redis ``PX`` expiry."""

        backend_key = _backend_key(_normalize_key(key))
        px_milliseconds = _ttl_to_px_milliseconds(ttl)
        try:
            payload = self._codec.encode(value)
        except CacheCodecError as exc:
            raise DependencyUnavailableError(_MSG_UNAVAILABLE) from exc
        if not isinstance(payload, (bytes, bytearray)):
            raise DependencyUnavailableError(_MSG_UNAVAILABLE)
        try:
            result = await self._client.set(
                backend_key,
                bytes(payload),
                px=px_milliseconds,
            )
        except RedisError as exc:
            raise DependencyUnavailableError(_MSG_UNAVAILABLE) from exc
        if result is not True:
            raise DependencyUnavailableError(_MSG_UNAVAILABLE)

    async def delete(self, key: str) -> None:
        """Remove ``key`` if present. Missing keys are a successful no-op."""

        backend_key = _backend_key(_normalize_key(key))
        try:
            await self._client.delete(backend_key)
        except RedisError as exc:
            raise DependencyUnavailableError(_MSG_UNAVAILABLE) from exc


def _normalize_key(key: object) -> str:
    if not isinstance(key, str):
        raise InvalidRequestError(_MSG_INVALID_KEY)
    cleaned = key.strip()
    if not cleaned:
        raise InvalidRequestError(_MSG_INVALID_KEY)
    return cleaned


def _backend_key(normalized_key: str) -> str:
    digest = sha256(normalized_key.encode("utf-8")).hexdigest()
    return f"{_BACKEND_KEY_PREFIX}{digest}"


def _ttl_to_px_milliseconds(ttl: object) -> int:
    if not isinstance(ttl, timedelta) or ttl <= timedelta(0):
        raise InvalidRequestError(_MSG_INVALID_TTL)
    total_microseconds = ttl // timedelta(microseconds=1)
    milliseconds, remainder = divmod(total_microseconds, 1000)
    if remainder:
        milliseconds += 1
    return milliseconds
