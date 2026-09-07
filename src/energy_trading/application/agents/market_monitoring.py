"""Market Monitoring Agent application boundary.

This module is the fifth concrete application agent. It consumes a typed
request, calls an injected canonical market-price source port once, and
returns canonical ``MarketPriceRecord`` values. Raw operator reports and
vendor payloads never enter here.

Ownership:

* Application: owns the request/result DTOs and the concrete agent.
* Injected ``MarketPriceRecordSourcePort``: supplies already-canonical records.
* Future infrastructure adapter: implements that port. Provider acquisition
  remains outside this module.
* LangGraph, failure-policy execution, persistence, retry, fallback,
  market-status objects, currency conversion, interval/cadence inference,
  market clearing, price forecasting, ML, and LLM remain deferred.

The agent satisfies ``AgentPort`` structurally. It does not inherit a base
class and is not registered in a factory.
"""

from dataclasses import dataclass
from datetime import datetime

from energy_trading.application.agents.base import AgentName
from energy_trading.application.ports.market_price_records import MarketPriceRecordSourcePort
from energy_trading.domain.models.observations import MarketPriceRecord
from energy_trading.domain.value_objects.time import to_utc


@dataclass(frozen=True, slots=True)
class MarketMonitoringRequest:
    """Immutable agent request: market plus an explicit UTC horizon.

    This is an application DTO, not a domain entity and not a workflow
    snapshot. It carries no provider, currency, cadence, product, retry, or
    payload fields. Currency belongs on canonical ``EnergyPrice``.
    """

    market_id: str
    horizon_start: datetime
    horizon_end: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "market_id", _require_non_empty("market_id", self.market_id))
        start = _require_aware_utc("horizon_start", self.horizon_start)
        end = _require_aware_utc("horizon_end", self.horizon_end)
        if end <= start:
            msg = "horizon_end must be later than horizon_start"
            raise ValueError(msg)
        object.__setattr__(self, "horizon_start", start)
        object.__setattr__(self, "horizon_end", end)


@dataclass(frozen=True, slots=True)
class MarketMonitoringResult:
    """Immutable agent result wrapping canonical observed market prices.

    An empty tuple is valid. Ordering is the source tuple order. This DTO
    carries no diagnostics, aggregates, forecasts, status, currency, or
    degraded flags. Canonical ``EnergyPrice`` and optional volume are
    passed through unchanged; they are not calculated here.
    """

    records: tuple[MarketPriceRecord, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "records", _require_market_price_records(self.records))


class MarketMonitoringAgent:
    """Thin application agent over a canonical market price source port.

    ``run`` calls ``MarketPriceRecordSourcePort.fetch`` exactly once and
    wraps the returned tuple. It does not sort, interpolate, aggregate,
    persist, retry, convert currency, forecast prices, or clear the market.
    """

    def __init__(self, source: MarketPriceRecordSourcePort) -> None:
        self._source = source

    @property
    def name(self) -> AgentName:
        return AgentName.MARKET_MONITORING

    async def run(self, request: MarketMonitoringRequest) -> MarketMonitoringResult:
        records = await self._source.fetch(
            market_id=request.market_id,
            horizon_start=request.horizon_start,
            horizon_end=request.horizon_end,
        )
        return MarketMonitoringResult(records=records)


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


def _require_market_price_records(value: object) -> tuple[MarketPriceRecord, ...]:
    if not isinstance(value, tuple):
        msg = "records must be an immutable tuple"
        raise TypeError(msg)
    if not all(isinstance(item, MarketPriceRecord) for item in value):
        msg = "records must contain MarketPriceRecord values"
        raise TypeError(msg)
    return value
