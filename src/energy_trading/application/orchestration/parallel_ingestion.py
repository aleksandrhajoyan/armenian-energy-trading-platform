"""Application-owned parallel Phase 2 ingestion fan-out plan.

This module defines one typed composition object that carries the five
already-published Phase 2 ingestion-agent request DTOs. A future executor
may consume this plan without deriving agent-specific scope from
``WorkflowState`` and without a generic payload bag.

Ownership:

* Application: owns ``ParallelIngestionPlan``.
* Existing agent request DTOs: reused as-is. This module does not shadow
  or replace them.
* Future execution: a separately reviewed chunk may fan out from this
  plan. This module does not execute agents.

``ParallelIngestionPlan`` is a frozen composition DTO. It does not equalize
horizons, derive ``location_id`` / ``resource_id`` / ``asset_id`` /
``market_id`` from ``portfolio_id``, or define fan-in/result semantics.
"""

from dataclasses import dataclass

from energy_trading.application.agents.generation_availability import (
    GenerationAvailabilityRequest,
)
from energy_trading.application.agents.hydro_resources import HydroResourcesRequest
from energy_trading.application.agents.market_monitoring import MarketMonitoringRequest
from energy_trading.application.agents.news_intelligence import NewsIntelligenceRequest
from energy_trading.application.agents.weather_and_renewable_forecast import (
    WeatherAndRenewableForecastRequest,
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


def _require_type(field_name: str, value: object, expected: type[object]) -> None:
    if not isinstance(value, expected):
        msg = f"{field_name} must be a {expected.__name__}"
        raise TypeError(msg)
