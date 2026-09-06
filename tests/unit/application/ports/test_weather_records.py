"""Canonical weather source application-port contract."""

from __future__ import annotations

import inspect
from datetime import UTC, datetime

import pytest

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.ports import WeatherRecordSourcePort
from energy_trading.domain.models.observations import WeatherRecord


class _FakeWeatherRecordSource:
    """Test-only fake that structurally satisfies ``WeatherRecordSourcePort``.

    Not a production adapter. Does not inherit a production or infrastructure
    base class.
    """

    def __init__(
        self,
        records: tuple[WeatherRecord, ...] = (),
        *,
        unavailable: bool = False,
    ) -> None:
        self.records = records
        self.unavailable = unavailable
        self.calls: list[tuple[str, datetime, datetime]] = []

    async def fetch(
        self,
        *,
        location_id: str,
        horizon_start: datetime,
        horizon_end: datetime,
    ) -> tuple[WeatherRecord, ...]:
        self.calls.append((location_id, horizon_start, horizon_end))
        if self.unavailable:
            msg = "weather source unavailable"
            raise DependencyUnavailableError(msg)
        return self.records


def _as_weather_source(source: _FakeWeatherRecordSource) -> WeatherRecordSourcePort:
    return source


def _weather(**overrides: object) -> WeatherRecord:
    values: dict[str, object] = {
        "location_id": "loc-1",
        "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
        "temperature_c": 12.5,
    }
    values.update(overrides)
    return WeatherRecord.model_validate(values)


def test_structural_fake_does_not_inherit_production_base() -> None:
    assert WeatherRecordSourcePort not in _FakeWeatherRecordSource.__mro__
    assert not any(
        base.__name__ in {"WeatherRecordSourcePort", "Protocol"}
        for base in _FakeWeatherRecordSource.__bases__
    )


def test_fake_provides_async_fetch() -> None:
    fake = _FakeWeatherRecordSource()
    port = _as_weather_source(fake)
    assert inspect.iscoroutinefunction(port.fetch)
    parameters = inspect.signature(_FakeWeatherRecordSource.fetch).parameters
    assert tuple(parameters) == ("self", "location_id", "horizon_start", "horizon_end")
    assert parameters["location_id"].kind is inspect.Parameter.KEYWORD_ONLY


async def test_empty_tuple_is_valid() -> None:
    port = _as_weather_source(_FakeWeatherRecordSource())
    result = await port.fetch(
        location_id="loc-1",
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )
    assert result == ()
    assert isinstance(result, tuple)


async def test_one_canonical_record_is_valid() -> None:
    record = _weather()
    port = _as_weather_source(_FakeWeatherRecordSource((record,)))
    result = await port.fetch(
        location_id="loc-1",
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )
    assert result == (record,)
    assert all(isinstance(item, WeatherRecord) for item in result)


async def test_multiple_canonical_records_preserve_order() -> None:
    first = _weather(timestamp=datetime(2026, 10, 1, 10, tzinfo=UTC))
    second = _weather(timestamp=datetime(2026, 10, 1, 11, tzinfo=UTC), temperature_c=13.0)
    port = _as_weather_source(_FakeWeatherRecordSource((first, second)))
    result = await port.fetch(
        location_id="loc-1",
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )
    assert result == (first, second)


async def test_fake_can_represent_dependency_unavailable() -> None:
    fake = _FakeWeatherRecordSource(unavailable=True)
    port = _as_weather_source(fake)
    with pytest.raises(DependencyUnavailableError, match="weather source unavailable"):
        await port.fetch(
            location_id="loc-1",
            horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
            horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
        )
    assert len(fake.calls) == 1
