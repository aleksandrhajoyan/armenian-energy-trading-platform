"""Application-owned parallel ingestion fan-out plan contract."""

from __future__ import annotations

from dataclasses import MISSING, FrozenInstanceError, fields
from datetime import UTC, datetime, timedelta, timezone

import pytest

from energy_trading.application.agents.generation_availability import (
    GenerationAvailabilityRequest,
)
from energy_trading.application.agents.hydro_resources import HydroResourcesRequest
from energy_trading.application.agents.market_monitoring import MarketMonitoringRequest
from energy_trading.application.agents.news_intelligence import NewsIntelligenceRequest
from energy_trading.application.agents.weather_and_renewable_forecast import (
    WeatherAndRenewableForecastRequest,
)
from energy_trading.application.orchestration import ParallelIngestionPlan


def _weather_request(**overrides: object) -> WeatherAndRenewableForecastRequest:
    values: dict[str, object] = {
        "location_id": "loc-1",
        "horizon_start": datetime(2026, 10, 1, 0, tzinfo=UTC),
        "horizon_end": datetime(2026, 10, 2, 0, tzinfo=UTC),
    }
    values.update(overrides)
    return WeatherAndRenewableForecastRequest(**values)  # type: ignore[arg-type]


def _hydro_request(**overrides: object) -> HydroResourcesRequest:
    values: dict[str, object] = {
        "resource_id": "hydro-1",
        "horizon_start": datetime(2026, 10, 1, 0, tzinfo=UTC),
        "horizon_end": datetime(2026, 10, 2, 0, tzinfo=UTC),
    }
    values.update(overrides)
    return HydroResourcesRequest(**values)  # type: ignore[arg-type]


def _generation_request(**overrides: object) -> GenerationAvailabilityRequest:
    values: dict[str, object] = {
        "asset_id": "asset-1",
        "horizon_start": datetime(2026, 10, 1, 0, tzinfo=UTC),
        "horizon_end": datetime(2026, 10, 2, 0, tzinfo=UTC),
    }
    values.update(overrides)
    return GenerationAvailabilityRequest(**values)  # type: ignore[arg-type]


def _news_request(**overrides: object) -> NewsIntelligenceRequest:
    values: dict[str, object] = {
        "horizon_start": datetime(2026, 10, 1, 0, tzinfo=UTC),
        "horizon_end": datetime(2026, 10, 2, 0, tzinfo=UTC),
    }
    values.update(overrides)
    return NewsIntelligenceRequest(**values)  # type: ignore[arg-type]


def _market_request(**overrides: object) -> MarketMonitoringRequest:
    values: dict[str, object] = {
        "market_id": "market-1",
        "horizon_start": datetime(2026, 10, 1, 0, tzinfo=UTC),
        "horizon_end": datetime(2026, 10, 2, 0, tzinfo=UTC),
    }
    values.update(overrides)
    return MarketMonitoringRequest(**values)  # type: ignore[arg-type]


def _plan(**overrides: object) -> ParallelIngestionPlan:
    values: dict[str, object] = {
        "weather_and_renewable_forecast": _weather_request(),
        "hydro_resources": _hydro_request(),
        "generation_availability": _generation_request(),
        "news_intelligence": _news_request(),
        "market_monitoring": _market_request(),
    }
    values.update(overrides)
    return ParallelIngestionPlan(**values)  # type: ignore[arg-type]


def test_plan_can_be_constructed_from_existing_request_dtos() -> None:
    weather = _weather_request()
    hydro = _hydro_request()
    generation = _generation_request()
    news = _news_request()
    market = _market_request()
    plan = ParallelIngestionPlan(
        weather_and_renewable_forecast=weather,
        hydro_resources=hydro,
        generation_availability=generation,
        news_intelligence=news,
        market_monitoring=market,
    )
    assert isinstance(plan.weather_and_renewable_forecast, WeatherAndRenewableForecastRequest)
    assert isinstance(plan.hydro_resources, HydroResourcesRequest)
    assert isinstance(plan.generation_availability, GenerationAvailabilityRequest)
    assert isinstance(plan.news_intelligence, NewsIntelligenceRequest)
    assert isinstance(plan.market_monitoring, MarketMonitoringRequest)


def test_plan_preserves_supplied_request_objects_exactly() -> None:
    weather = _weather_request()
    hydro = _hydro_request()
    generation = _generation_request()
    news = _news_request()
    market = _market_request()
    plan = ParallelIngestionPlan(
        weather_and_renewable_forecast=weather,
        hydro_resources=hydro,
        generation_availability=generation,
        news_intelligence=news,
        market_monitoring=market,
    )
    assert plan.weather_and_renewable_forecast is weather
    assert plan.hydro_resources is hydro
    assert plan.generation_availability is generation
    assert plan.news_intelligence is news
    assert plan.market_monitoring is market


def test_plan_is_frozen_and_slotted() -> None:
    plan = _plan()
    assert hasattr(ParallelIngestionPlan, "__slots__")
    with pytest.raises(FrozenInstanceError):
        plan.market_monitoring = _market_request(market_id="mutated")  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        plan.weather_and_renewable_forecast = _weather_request(  # type: ignore[misc]
            location_id="mutated"
        )


def test_plan_public_fields_are_exactly_the_five_requests() -> None:
    field_names = tuple(item.name for item in fields(ParallelIngestionPlan))
    assert field_names == (
        "weather_and_renewable_forecast",
        "hydro_resources",
        "generation_availability",
        "news_intelligence",
        "market_monitoring",
    )


def test_plan_does_not_execute_anything() -> None:
    defined_methods = {
        name
        for name, value in vars(ParallelIngestionPlan).items()
        if callable(value) and not name.startswith("_")
    }
    assert defined_methods == set()
    forbidden = {
        "run",
        "execute",
        "fan_out",
        "fan_in",
        "gather",
        "invoke",
        "dispatch",
        "as_dict",
        "asdict",
        "to_dict",
        "items",
        "requests",
        "as_mapping",
    }
    assert forbidden.isdisjoint(dir(ParallelIngestionPlan))


def test_plan_preserves_distinct_request_scopes_and_horizons() -> None:
    weather = _weather_request(
        location_id="location-west",
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )
    hydro = _hydro_request(
        resource_id="reservoir-a",
        horizon_start=datetime(2026, 10, 1, 6, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 1, 18, tzinfo=UTC),
    )
    generation = _generation_request(
        asset_id="asset-north",
        horizon_start=datetime(2026, 9, 30, 22, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 2, tzinfo=UTC),
    )
    news = _news_request(
        horizon_start=datetime(2026, 10, 1, 12, tzinfo=timezone(timedelta(hours=4))),
        horizon_end=datetime(2026, 10, 1, 20, tzinfo=timezone(timedelta(hours=4))),
    )
    market = _market_request(
        market_id="market-alpha",
        horizon_start=datetime(2026, 10, 2, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 3, 0, tzinfo=UTC),
    )
    plan = ParallelIngestionPlan(
        weather_and_renewable_forecast=weather,
        hydro_resources=hydro,
        generation_availability=generation,
        news_intelligence=news,
        market_monitoring=market,
    )
    assert plan.weather_and_renewable_forecast.location_id == "location-west"
    assert plan.hydro_resources.resource_id == "reservoir-a"
    assert plan.generation_availability.asset_id == "asset-north"
    assert plan.market_monitoring.market_id == "market-alpha"
    assert plan.weather_and_renewable_forecast.horizon_start != plan.hydro_resources.horizon_start
    assert plan.hydro_resources.horizon_end != plan.generation_availability.horizon_end
    assert plan.news_intelligence.horizon_start != plan.market_monitoring.horizon_start
    assert plan.weather_and_renewable_forecast.horizon_end != plan.market_monitoring.horizon_end
    assert plan.weather_and_renewable_forecast is weather
    assert plan.hydro_resources is hydro
    assert plan.generation_availability is generation
    assert plan.news_intelligence is news
    assert plan.market_monitoring is market


def test_plan_does_not_invent_default_entity_ids_or_source_scopes() -> None:
    for item in fields(ParallelIngestionPlan):
        assert item.default is MISSING
        assert item.default_factory is MISSING
    with pytest.raises(TypeError):
        ParallelIngestionPlan()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        ParallelIngestionPlan(  # type: ignore[call-arg]
            weather_and_renewable_forecast=_weather_request(),
            hydro_resources=_hydro_request(),
            generation_availability=_generation_request(),
            news_intelligence=_news_request(),
        )


def test_plan_rejects_wrong_request_types() -> None:
    with pytest.raises(TypeError, match="weather_and_renewable_forecast must be a"):
        _plan(weather_and_renewable_forecast=_hydro_request())
    with pytest.raises(TypeError, match="market_monitoring must be a"):
        _plan(market_monitoring=_news_request())
