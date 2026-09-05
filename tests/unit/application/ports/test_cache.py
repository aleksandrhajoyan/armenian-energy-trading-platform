"""Application-owned cache port contract."""

from __future__ import annotations

import inspect
from datetime import UTC, datetime, timedelta

import pytest

from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.ports import CachePort
from energy_trading.domain.models import ConsumptionRecord
from tests.unit.domain._factories import consumption


class _DeterministicClock:
    """Test-only controllable clock. Does not sleep on the wall clock."""

    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def advance(self, delta: timedelta) -> None:
        self.now += delta


class _InMemoryCacheFake[TValue]:
    """Test-only in-memory fake that structurally satisfies ``CachePort``.

    Not a production cache. Not exported from application or infrastructure.
    """

    def __init__(self, clock: _DeterministicClock) -> None:
        self._clock = clock
        self._entries: dict[str, tuple[TValue, datetime]] = {}

    def _normalize_key(self, key: str) -> str:
        cleaned = key.strip()
        if not cleaned:
            raise InvalidRequestError("Cache key must be a non-empty string.")
        return cleaned

    def _require_positive_ttl(self, ttl: timedelta) -> None:
        if ttl <= timedelta(0):
            raise InvalidRequestError("Cache TTL must be greater than zero.")

    def _live_entry(self, key: str) -> tuple[TValue, datetime] | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if self._clock() >= expires_at:
            del self._entries[key]
            return None
        return value, expires_at

    async def get(self, key: str) -> TValue | None:
        normalized = self._normalize_key(key)
        entry = self._live_entry(normalized)
        if entry is None:
            return None
        return entry[0]

    async def set(self, key: str, value: TValue, *, ttl: timedelta) -> None:
        normalized = self._normalize_key(key)
        self._require_positive_ttl(ttl)
        expires_at = self._clock() + ttl
        self._entries[normalized] = (value, expires_at)

    async def delete(self, key: str) -> None:
        normalized = self._normalize_key(key)
        self._entries.pop(normalized, None)


def _as_cache_port(cache: _InMemoryCacheFake[ConsumptionRecord]) -> CachePort[ConsumptionRecord]:
    """Application-shaped call site: the port type is the only accepted argument."""

    return cache


def _cache(
    clock: _DeterministicClock | None = None,
) -> tuple[_DeterministicClock, CachePort[ConsumptionRecord]]:
    resolved = clock or _DeterministicClock(datetime(2026, 1, 1, 12, 0, tzinfo=UTC))
    return resolved, _as_cache_port(_InMemoryCacheFake[ConsumptionRecord](resolved))


def test_fake_structurally_satisfies_cache_port() -> None:
    _clock, port = _cache()
    typed: CachePort[ConsumptionRecord] = port
    assert inspect.iscoroutinefunction(typed.get)
    assert inspect.iscoroutinefunction(typed.set)
    assert inspect.iscoroutinefunction(typed.delete)


async def test_get_returns_none_on_cache_miss() -> None:
    _clock, port = _cache()
    assert await port.get("canonical-consumption") is None


async def test_typed_consumption_record_round_trips() -> None:
    _clock, port = _cache()
    record = consumption()
    await port.set("canonical-consumption", record, ttl=timedelta(minutes=5))
    loaded = await port.get("canonical-consumption")
    assert loaded == record
    assert isinstance(loaded, ConsumptionRecord)
    assert loaded.consumer_id == "consumer-1"
    assert loaded.value_mw == 1.5


async def test_set_replaces_existing_value() -> None:
    _clock, port = _cache()
    first = consumption(value_mw=1.0)
    second = consumption(value_mw=2.5)
    await port.set("canonical-consumption", first, ttl=timedelta(hours=1))
    await port.set("canonical-consumption", second, ttl=timedelta(hours=1))
    loaded = await port.get("canonical-consumption")
    assert loaded == second
    assert loaded is not None
    assert loaded.value_mw == 2.5


async def test_replacement_uses_new_ttl() -> None:
    clock, port = _cache()
    first = consumption(value_mw=1.0)
    second = consumption(value_mw=2.0)
    await port.set("canonical-consumption", first, ttl=timedelta(seconds=10))
    clock.advance(timedelta(seconds=6))
    await port.set("canonical-consumption", second, ttl=timedelta(seconds=10))
    clock.advance(timedelta(seconds=6))
    loaded = await port.get("canonical-consumption")
    assert loaded == second
    clock.advance(timedelta(seconds=4))
    assert await port.get("canonical-consumption") is None


async def test_expired_values_behave_as_missing() -> None:
    clock, port = _cache()
    record = consumption()
    await port.set("canonical-consumption", record, ttl=timedelta(seconds=5))
    assert await port.get("canonical-consumption") == record
    clock.advance(timedelta(seconds=5))
    assert await port.get("canonical-consumption") is None


async def test_delete_removes_existing_entry() -> None:
    _clock, port = _cache()
    record = consumption()
    await port.set("canonical-consumption", record, ttl=timedelta(hours=1))
    await port.delete("canonical-consumption")
    assert await port.get("canonical-consumption") is None


async def test_delete_of_absent_key_is_successful_noop() -> None:
    _clock, port = _cache()
    await port.delete("missing-key")
    await port.delete("missing-key")
    assert await port.get("missing-key") is None


@pytest.mark.parametrize("key", ["", "   ", "\t", "\n"])
async def test_blank_keys_fail_with_invalid_request_error(key: str) -> None:
    _clock, port = _cache()
    record = consumption()
    with pytest.raises(InvalidRequestError, match="Cache key must be a non-empty string"):
        await port.get(key)
    with pytest.raises(InvalidRequestError, match="Cache key must be a non-empty string"):
        await port.set(key, record, ttl=timedelta(seconds=1))
    with pytest.raises(InvalidRequestError, match="Cache key must be a non-empty string"):
        await port.delete(key)


async def test_whitespace_around_key_is_ignored() -> None:
    _clock, port = _cache()
    record = consumption()
    await port.set("  canonical-consumption  ", record, ttl=timedelta(minutes=1))
    assert await port.get("canonical-consumption") == record
    assert await port.get("\tcanonical-consumption\n") == record


async def test_zero_ttl_fails_with_invalid_request_error() -> None:
    _clock, port = _cache()
    with pytest.raises(InvalidRequestError, match="Cache TTL must be greater than zero"):
        await port.set("canonical-consumption", consumption(), ttl=timedelta(0))


async def test_negative_ttl_fails_with_invalid_request_error() -> None:
    _clock, port = _cache()
    with pytest.raises(InvalidRequestError, match="Cache TTL must be greater than zero"):
        await port.set("canonical-consumption", consumption(), ttl=timedelta(seconds=-1))
