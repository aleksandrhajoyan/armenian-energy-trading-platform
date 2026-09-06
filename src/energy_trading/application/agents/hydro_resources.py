"""Hydro Resources Agent application boundary.

This module is the second concrete application agent. It consumes a typed
request, calls an injected canonical hydro source port once, and returns
canonical ``HydroRecord`` values. Raw telemetry never enters here.

Ownership:

* Application: owns the request/result DTOs and the concrete agent.
* Injected ``HydroRecordSourcePort``: supplies already-canonical records.
* Future infrastructure adapter: implements that port. Provider acquisition
  remains outside this module.
* LangGraph, failure-policy execution, persistence, retry, fallback,
  hydrological calculation, Generation Availability coupling, ML, and LLM
  remain deferred.

The agent satisfies ``AgentPort`` structurally. It does not inherit a base
class and is not registered in a factory.
"""

from dataclasses import dataclass
from datetime import datetime

from energy_trading.application.agents.base import AgentName
from energy_trading.application.ports.hydro_records import HydroRecordSourcePort
from energy_trading.domain.models.observations import HydroRecord
from energy_trading.domain.value_objects.time import to_utc


@dataclass(frozen=True, slots=True)
class HydroResourcesRequest:
    """Immutable agent request: resource plus an explicit UTC horizon.

    This is an application DTO, not a domain entity and not a workflow
    snapshot. It carries no provider, cadence, retry, or payload fields.
    """

    resource_id: str
    horizon_start: datetime
    horizon_end: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "resource_id", _require_non_empty("resource_id", self.resource_id))
        start = _require_aware_utc("horizon_start", self.horizon_start)
        end = _require_aware_utc("horizon_end", self.horizon_end)
        if end <= start:
            msg = "horizon_end must be later than horizon_start"
            raise ValueError(msg)
        object.__setattr__(self, "horizon_start", start)
        object.__setattr__(self, "horizon_end", end)


@dataclass(frozen=True, slots=True)
class HydroResourcesResult:
    """Immutable agent result wrapping canonical hydro records.

    An empty tuple is valid. Ordering is the source tuple order. This DTO
    carries no diagnostics, provider metadata, or degraded flags. Optional
    canonical hydro fields are passed through unchanged; they are not
    calculated here.
    """

    records: tuple[HydroRecord, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "records", _require_hydro_records(self.records))


class HydroResourcesAgent:
    """Thin application agent over a canonical hydro source port.

    ``run`` calls ``HydroRecordSourcePort.fetch`` exactly once and wraps
    the returned tuple. It does not sort, interpolate, persist, retry, or
    calculate hydro values.
    """

    def __init__(self, source: HydroRecordSourcePort) -> None:
        self._source = source

    @property
    def name(self) -> AgentName:
        return AgentName.HYDRO_RESOURCES

    async def run(self, request: HydroResourcesRequest) -> HydroResourcesResult:
        records = await self._source.fetch(
            resource_id=request.resource_id,
            horizon_start=request.horizon_start,
            horizon_end=request.horizon_end,
        )
        return HydroResourcesResult(records=records)


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


def _require_hydro_records(value: object) -> tuple[HydroRecord, ...]:
    if not isinstance(value, tuple):
        msg = "records must be an immutable tuple"
        raise TypeError(msg)
    if not all(isinstance(item, HydroRecord) for item in value):
        msg = "records must contain HydroRecord values"
        raise TypeError(msg)
    return value
