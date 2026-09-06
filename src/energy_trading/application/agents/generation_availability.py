"""Generation Availability Agent application boundary.

This module is the third concrete application agent. It consumes a typed
request, calls an injected canonical generation-availability source port
once, and returns canonical ``GenerationAvailabilityRecord`` values. Raw
outage or plant-availability payloads never enter here.

Ownership:

* Application: owns the request/result DTOs and the concrete agent.
* Injected ``GenerationAvailabilityRecordSourcePort``: supplies already-canonical
  records.
* Future infrastructure adapter: implements that port. Provider acquisition
  remains outside this module.
* LangGraph, failure-policy execution, persistence, retry, fallback,
  capacity calculation, status inference, fleet-completeness policy,
  Hydro coupling, ML, and LLM remain deferred.

The agent satisfies ``AgentPort`` structurally. It does not inherit a base
class and is not registered in a factory.
"""

from dataclasses import dataclass
from datetime import datetime

from energy_trading.application.agents.base import AgentName
from energy_trading.application.ports.generation_availability_records import (
    GenerationAvailabilityRecordSourcePort,
)
from energy_trading.domain.models.observations import GenerationAvailabilityRecord
from energy_trading.domain.value_objects.time import to_utc


@dataclass(frozen=True, slots=True)
class GenerationAvailabilityRequest:
    """Immutable agent request: asset plus an explicit UTC horizon.

    This is an application DTO, not a domain entity and not a workflow
    snapshot. It carries no provider, cadence, retry, fleet, Hydro, or
    payload fields.
    """

    asset_id: str
    horizon_start: datetime
    horizon_end: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "asset_id", _require_non_empty("asset_id", self.asset_id))
        start = _require_aware_utc("horizon_start", self.horizon_start)
        end = _require_aware_utc("horizon_end", self.horizon_end)
        if end <= start:
            msg = "horizon_end must be later than horizon_start"
            raise ValueError(msg)
        object.__setattr__(self, "horizon_start", start)
        object.__setattr__(self, "horizon_end", end)


@dataclass(frozen=True, slots=True)
class GenerationAvailabilityResult:
    """Immutable agent result wrapping canonical generation availability records.

    An empty tuple is valid. Ordering is the source tuple order. This DTO
    carries no diagnostics, provider metadata, fleet completeness, or
    degraded flags. Canonical status and capacity fields are passed through
    unchanged; they are not calculated here.
    """

    records: tuple[GenerationAvailabilityRecord, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "records", _require_generation_availability_records(self.records))


class GenerationAvailabilityAgent:
    """Thin application agent over a canonical generation availability source port.

    ``run`` calls ``GenerationAvailabilityRecordSourcePort.fetch`` exactly
    once and wraps the returned tuple. It does not sort, interpolate,
    persist, retry, infer status, calculate capacity, or derive records
    from Hydro.
    """

    def __init__(self, source: GenerationAvailabilityRecordSourcePort) -> None:
        self._source = source

    @property
    def name(self) -> AgentName:
        return AgentName.GENERATION_AVAILABILITY

    async def run(self, request: GenerationAvailabilityRequest) -> GenerationAvailabilityResult:
        records = await self._source.fetch(
            asset_id=request.asset_id,
            horizon_start=request.horizon_start,
            horizon_end=request.horizon_end,
        )
        return GenerationAvailabilityResult(records=records)


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


def _require_generation_availability_records(
    value: object,
) -> tuple[GenerationAvailabilityRecord, ...]:
    if not isinstance(value, tuple):
        msg = "records must be an immutable tuple"
        raise TypeError(msg)
    if not all(isinstance(item, GenerationAvailabilityRecord) for item in value):
        msg = "records must contain GenerationAvailabilityRecord values"
        raise TypeError(msg)
    return value
