"""Weather & Renewable Forecast Agent application boundary.

This module is the first concrete application agent. It consumes a typed
request, calls an injected canonical weather source port once, and returns
canonical ``WeatherRecord`` values. Raw provider payloads never enter here.

Ownership:

* Application: owns the request/result DTOs and the concrete agent.
* Injected ``WeatherRecordSourcePort``: supplies already-canonical records.
* Future infrastructure adapter: implements that port. Provider acquisition
  remains outside this module.
* LangGraph, failure-policy execution, persistence, retry, fallback, ML, and
  LLM calculation remain deferred.

The agent satisfies ``AgentPort`` structurally. It does not inherit a base
class and is not registered in a factory.
"""

from dataclasses import dataclass
from datetime import datetime

from energy_trading.application.agents.base import AgentName
from energy_trading.application.ports.weather_records import WeatherRecordSourcePort
from energy_trading.domain.models.observations import WeatherRecord
from energy_trading.domain.value_objects.time import to_utc


@dataclass(frozen=True, slots=True)
class WeatherAndRenewableForecastRequest:
    """Immutable agent request: location plus an explicit UTC horizon.

    This is an application DTO, not a domain entity and not a workflow
    snapshot. It carries no provider, cadence, retry, or payload fields.
    """

    location_id: str
    horizon_start: datetime
    horizon_end: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "location_id", _require_non_empty("location_id", self.location_id))
        start = _require_aware_utc("horizon_start", self.horizon_start)
        end = _require_aware_utc("horizon_end", self.horizon_end)
        if end <= start:
            msg = "horizon_end must be later than horizon_start"
            raise ValueError(msg)
        object.__setattr__(self, "horizon_start", start)
        object.__setattr__(self, "horizon_end", end)


@dataclass(frozen=True, slots=True)
class WeatherAndRenewableForecastResult:
    """Immutable agent result wrapping canonical weather records.

    An empty tuple is valid. Ordering is the source tuple order. This DTO
    carries no diagnostics, provider metadata, or degraded flags.
    """

    records: tuple[WeatherRecord, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "records", _require_weather_records(self.records))


class WeatherAndRenewableForecastAgent:
    """Thin application agent over a canonical weather source port.

    ``run`` calls ``WeatherRecordSourcePort.fetch`` exactly once and wraps
    the returned tuple. It does not sort, interpolate, persist, retry, or
    calculate weather values.
    """

    def __init__(self, source: WeatherRecordSourcePort) -> None:
        self._source = source

    @property
    def name(self) -> AgentName:
        return AgentName.WEATHER_AND_RENEWABLE_FORECAST

    async def run(
        self, request: WeatherAndRenewableForecastRequest
    ) -> WeatherAndRenewableForecastResult:
        records = await self._source.fetch(
            location_id=request.location_id,
            horizon_start=request.horizon_start,
            horizon_end=request.horizon_end,
        )
        return WeatherAndRenewableForecastResult(records=records)


def _require_non_empty(field_name: str, value: object) -> str:
    if not isinstance(value, str):
        msg = f"{field_name} must be a string"
        raise TypeError(msg)
    cleaned = value.strip()
    if not cleaned:
        msg = f"{field_name} must be a non-empty string"
        raise ValueError(msg)
    return cleaned


def _require_aware_utc(field_name: str, value: object) -> datetime:
    if not isinstance(value, datetime):
        msg = f"{field_name} must be a datetime"
        raise TypeError(msg)
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        msg = f"{field_name} must be timezone-aware"
        raise ValueError(msg)
    return to_utc(value)


def _require_weather_records(value: object) -> tuple[WeatherRecord, ...]:
    if not isinstance(value, tuple):
        msg = "records must be an immutable tuple"
        raise TypeError(msg)
    if not all(isinstance(item, WeatherRecord) for item in value):
        msg = "records must contain WeatherRecord values"
        raise TypeError(msg)
    return value
