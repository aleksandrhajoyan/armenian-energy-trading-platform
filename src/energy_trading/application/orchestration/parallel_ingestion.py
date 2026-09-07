"""Application-owned parallel Phase 2 ingestion plan and successful fan-in.

This module defines two typed composition objects:

* ``ParallelIngestionPlan`` carries the five already-published Phase 2
  ingestion-agent request DTOs.
* ``ParallelIngestionSuccess`` carries the five already-published Phase 2
  ingestion-agent result DTOs for the unambiguous all-branches-succeeded
  case.

A future executor may consume the plan and later produce the success
aggregate without deriving agent-specific scope from ``WorkflowState``
and without a generic payload bag.

Ownership:

* Application: owns ``ParallelIngestionPlan`` and ``ParallelIngestionSuccess``.
* Existing agent request/result DTOs: reused as-is. This module does not
  shadow or replace them.
* Future execution: a separately reviewed chunk may fan out from the plan
  and join successful results. This module does not execute agents.

Neither DTO equalizes horizons, derives ``location_id`` / ``resource_id`` /
``asset_id`` / ``market_id`` from ``portfolio_id``, or defines
partial/failure/degraded fan-in semantics.
"""

from dataclasses import dataclass

from energy_trading.application.agents.generation_availability import (
    GenerationAvailabilityRequest,
    GenerationAvailabilityResult,
)
from energy_trading.application.agents.hydro_resources import (
    HydroResourcesRequest,
    HydroResourcesResult,
)
from energy_trading.application.agents.market_monitoring import (
    MarketMonitoringRequest,
    MarketMonitoringResult,
)
from energy_trading.application.agents.news_intelligence import (
    NewsIntelligenceRequest,
    NewsIntelligenceResult,
)
from energy_trading.application.agents.weather_and_renewable_forecast import (
    WeatherAndRenewableForecastRequest,
    WeatherAndRenewableForecastResult,
)


@dataclass(frozen=True, slots=True)
class ParallelIngestionPlan:
    """Immutable fan-out plan for the five Phase 2 ingestion agents.

    This is an application orchestration DTO, not ``WorkflowState``, not a
    domain contract, and not a graph runtime object. Supplied request
    objects are preserved exactly. The plan does not execute agents.
    """

    weather_and_renewable_forecast: WeatherAndRenewableForecastRequest
    hydro_resources: HydroResourcesRequest
    generation_availability: GenerationAvailabilityRequest
    news_intelligence: NewsIntelligenceRequest
    market_monitoring: MarketMonitoringRequest

    def __post_init__(self) -> None:
        _require_type(
            "weather_and_renewable_forecast",
            self.weather_and_renewable_forecast,
            WeatherAndRenewableForecastRequest,
        )
        _require_type("hydro_resources", self.hydro_resources, HydroResourcesRequest)
        _require_type(
            "generation_availability",
            self.generation_availability,
            GenerationAvailabilityRequest,
        )
        _require_type("news_intelligence", self.news_intelligence, NewsIntelligenceRequest)
        _require_type("market_monitoring", self.market_monitoring, MarketMonitoringRequest)


@dataclass(frozen=True, slots=True)
class ParallelIngestionSuccess:
    """Immutable all-five-success fan-in aggregate for Phase 2 ingestion.

    This is an application orchestration DTO, not ``WorkflowState``, not a
    domain contract, and not a graph runtime object. It represents only
    the case where all five branches have already produced their existing
    typed result DTOs. Supplied result objects are preserved exactly. The
    aggregate does not execute agents and does not encode failure,
    degraded, or partial-completion semantics.
    """

    weather_and_renewable_forecast: WeatherAndRenewableForecastResult
    hydro_resources: HydroResourcesResult
    generation_availability: GenerationAvailabilityResult
    news_intelligence: NewsIntelligenceResult
    market_monitoring: MarketMonitoringResult

    def __post_init__(self) -> None:
        _require_type(
            "weather_and_renewable_forecast",
            self.weather_and_renewable_forecast,
            WeatherAndRenewableForecastResult,
        )
        _require_type("hydro_resources", self.hydro_resources, HydroResourcesResult)
        _require_type(
            "generation_availability",
            self.generation_availability,
            GenerationAvailabilityResult,
        )
        _require_type("news_intelligence", self.news_intelligence, NewsIntelligenceResult)
        _require_type("market_monitoring", self.market_monitoring, MarketMonitoringResult)


def _require_type(field_name: str, value: object, expected: type[object]) -> None:
    if not isinstance(value, expected):
        msg = f"{field_name} must be a {expected.__name__}"
        raise TypeError(msg)
