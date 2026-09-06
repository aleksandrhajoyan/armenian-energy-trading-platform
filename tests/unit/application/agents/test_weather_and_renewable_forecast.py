"""Weather & Renewable Forecast Agent application contract."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime, timedelta, timezone

import pytest

from energy_trading.application.agents.base import AgentName, AgentPort
from energy_trading.application.agents.weather_and_renewable_forecast import (
    WeatherAndRenewableForecastAgent,
    WeatherAndRenewableForecastRequest,
    WeatherAndRenewableForecastResult,
)
from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.domain.models.observations import WeatherRecord


class _FakeWeatherRecordSource:
    """Test-only source fake. Not a production adapter."""

    def __init__(
        self,
        records: tuple[WeatherRecord, ...] = (),
        *,
        error: Exception | None = None,
    ) -> None:
        self.records = records
        self.error = error
        self.calls: list[tuple[str, datetime, datetime]] = []

    async def fetch(
        self,
        *,
        location_id: str,
        horizon_start: datetime,
        horizon_end: datetime,
    ) -> tuple[WeatherRecord, ...]:
        self.calls.append((location_id, horizon_start, horizon_end))
        if self.error is not None:
            raise self.error
        return self.records


def _as_agent_port(
    agent: WeatherAndRenewableForecastAgent,
) -> AgentPort[WeatherAndRenewableForecastRequest, WeatherAndRenewableForecastResult]:
    """Mypy-visible structural assignment to the shared agent port."""

    return agent


def _weather(**overrides: object) -> WeatherRecord:
    values: dict[str, object] = {
        "location_id": "loc-1",
        "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
        "temperature_c": 12.5,
    }
    values.update(overrides)
    return WeatherRecord.model_validate(values)


def _request(**overrides: object) -> WeatherAndRenewableForecastRequest:
    values: dict[str, object] = {
        "location_id": "loc-1",
        "horizon_start": datetime(2026, 10, 1, 0, tzinfo=UTC),
        "horizon_end": datetime(2026, 10, 2, 0, tzinfo=UTC),
    }
    values.update(overrides)
    return WeatherAndRenewableForecastRequest(**values)  # type: ignore[arg-type]


def test_request_accepts_location_and_utc_horizon() -> None:
    request = _request()
    assert request.location_id == "loc-1"
    assert request.horizon_start == datetime(2026, 10, 1, 0, tzinfo=UTC)
    assert request.horizon_end == datetime(2026, 10, 2, 0, tzinfo=UTC)
    assert request.horizon_start.tzinfo is UTC
    assert request.horizon_end.tzinfo is UTC


def test_request_strips_location_whitespace() -> None:
    request = _request(location_id="  loc-1  ")
    assert request.location_id == "loc-1"


def test_request_normalizes_aware_non_utc_horizons_to_utc() -> None:
    offset = timezone(timedelta(hours=4))
    request = _request(
        horizon_start=datetime(2026, 10, 1, 4, tzinfo=offset),
        horizon_end=datetime(2026, 10, 1, 8, tzinfo=offset),
    )
    assert request.horizon_start == datetime(2026, 10, 1, 0, tzinfo=UTC)
    assert request.horizon_end == datetime(2026, 10, 1, 4, tzinfo=UTC)
    assert request.horizon_start.tzinfo is UTC
    assert request.horizon_end.tzinfo is UTC


def test_request_rejects_naive_horizon_start() -> None:
    with pytest.raises(ValueError, match="horizon_start must be timezone-aware"):
        _request(horizon_start=datetime(2026, 10, 1, 0))


def test_request_rejects_naive_horizon_end() -> None:
    with pytest.raises(ValueError, match="horizon_end must be timezone-aware"):
        _request(horizon_end=datetime(2026, 10, 2, 0))


def test_request_rejects_equal_horizon_bounds() -> None:
    instant = datetime(2026, 10, 1, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="horizon_end must be later than horizon_start"):
        _request(horizon_start=instant, horizon_end=instant)


def test_request_rejects_reversed_horizon() -> None:
    with pytest.raises(ValueError, match="horizon_end must be later than horizon_start"):
        _request(
            horizon_start=datetime(2026, 10, 2, 0, tzinfo=UTC),
            horizon_end=datetime(2026, 10, 1, 0, tzinfo=UTC),
        )


def test_request_is_frozen_and_slotted() -> None:
    request = _request()
    assert hasattr(WeatherAndRenewableForecastRequest, "__slots__")
    with pytest.raises(FrozenInstanceError):
        request.location_id = "mutated"  # type: ignore[misc]
    field_names = tuple(item.name for item in fields(WeatherAndRenewableForecastRequest))
    assert field_names == ("location_id", "horizon_start", "horizon_end")


def test_request_rejects_unrequested_fields() -> None:
    with pytest.raises(TypeError):
        WeatherAndRenewableForecastRequest(
            location_id="loc-1",
            horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
            horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
            provider="open-meteo",  # type: ignore[call-arg]
        )


def test_result_empty_tuple_is_valid() -> None:
    result = WeatherAndRenewableForecastResult(records=())
    assert result.records == ()
    assert isinstance(result.records, tuple)


def test_result_accepts_one_weather_record() -> None:
    record = _weather()
    result = WeatherAndRenewableForecastResult(records=(record,))
    assert result.records == (record,)


def test_result_preserves_multiple_record_order() -> None:
    first = _weather(timestamp=datetime(2026, 10, 1, 11, tzinfo=UTC))
    second = _weather(timestamp=datetime(2026, 10, 1, 10, tzinfo=UTC), temperature_c=9.0)
    result = WeatherAndRenewableForecastResult(records=(first, second))
    assert result.records == (first, second)


def test_result_rejects_mutable_records_collection() -> None:
    with pytest.raises(TypeError, match="records must be an immutable tuple"):
        WeatherAndRenewableForecastResult(records=[_weather()])  # type: ignore[arg-type]


def test_result_rejects_non_weather_record_values() -> None:
    with pytest.raises(TypeError, match="records must contain WeatherRecord values"):
        WeatherAndRenewableForecastResult(records=("not-weather",))  # type: ignore[arg-type]


def test_result_is_frozen() -> None:
    result = WeatherAndRenewableForecastResult(records=())
    assert hasattr(WeatherAndRenewableForecastResult, "__slots__")
    with pytest.raises(FrozenInstanceError):
        result.records = ()  # type: ignore[misc]


def test_agent_does_not_inherit_agent_port() -> None:
    assert AgentPort not in WeatherAndRenewableForecastAgent.__mro__
    assert not any(
        base.__name__ == "AgentPort" for base in WeatherAndRenewableForecastAgent.__bases__
    )


def test_agent_name_is_canonical_weather_identity() -> None:
    agent = WeatherAndRenewableForecastAgent(_FakeWeatherRecordSource())
    port = _as_agent_port(agent)
    assert port.name is AgentName.WEATHER_AND_RENEWABLE_FORECAST
    assert port.name.value == "Weather & Renewable Forecast Agent"


async def test_run_invokes_source_once_with_normalized_values() -> None:
    source = _FakeWeatherRecordSource()
    agent = WeatherAndRenewableForecastAgent(source)
    offset = timezone(timedelta(hours=4))
    result = await _as_agent_port(agent).run(
        WeatherAndRenewableForecastRequest(
            location_id="  loc-1  ",
            horizon_start=datetime(2026, 10, 1, 4, tzinfo=offset),
            horizon_end=datetime(2026, 10, 1, 8, tzinfo=offset),
        )
    )
    assert result.records == ()
    assert len(source.calls) == 1
    location_id, horizon_start, horizon_end = source.calls[0]
    assert location_id == "loc-1"
    assert horizon_start == datetime(2026, 10, 1, 0, tzinfo=UTC)
    assert horizon_end == datetime(2026, 10, 1, 4, tzinfo=UTC)


async def test_run_wraps_source_tuple_without_reordering() -> None:
    first = _weather(timestamp=datetime(2026, 10, 1, 12, tzinfo=UTC))
    second = _weather(timestamp=datetime(2026, 10, 1, 8, tzinfo=UTC), temperature_c=4.0)
    source = _FakeWeatherRecordSource((first, second))
    result = await WeatherAndRenewableForecastAgent(source).run(_request())
    assert result.records == (first, second)
    assert result.records is source.records or result.records == source.records
    assert len(source.calls) == 1


async def test_run_empty_source_result_is_valid() -> None:
    result = await WeatherAndRenewableForecastAgent(_FakeWeatherRecordSource()).run(_request())
    assert result == WeatherAndRenewableForecastResult(records=())


async def test_run_propagates_dependency_unavailable_without_retry() -> None:
    error = DependencyUnavailableError("weather source unavailable")
    source = _FakeWeatherRecordSource(error=error)
    agent = WeatherAndRenewableForecastAgent(source)
    with pytest.raises(DependencyUnavailableError, match="weather source unavailable") as caught:
        await agent.run(_request())
    assert caught.value is error
    assert len(source.calls) == 1
