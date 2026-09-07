"""Application-owned parallel ingestion plan, execution port, and success contracts."""

from __future__ import annotations

import inspect
from dataclasses import MISSING, FrozenInstanceError, fields
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest

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
from energy_trading.application.orchestration import (
    ParallelIngestionExecutionPort,
    ParallelIngestionPlan,
    ParallelIngestionSuccess,
)
from energy_trading.domain.models.observations import (
    GenerationAvailabilityRecord,
    GenerationStatus,
    HydroRecord,
    MarketPriceRecord,
    NewsEvent,
    WeatherRecord,
)
from energy_trading.domain.value_objects.money import EnergyPrice


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


def _weather_record(**overrides: object) -> WeatherRecord:
    values: dict[str, object] = {
        "location_id": "loc-1",
        "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
        "temperature_c": 12.5,
    }
    values.update(overrides)
    return WeatherRecord.model_validate(values)


def _hydro_record(**overrides: object) -> HydroRecord:
    values: dict[str, object] = {
        "resource_id": "hydro-1",
        "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
    }
    values.update(overrides)
    return HydroRecord.model_validate(values)


def _generation_record(**overrides: object) -> GenerationAvailabilityRecord:
    values: dict[str, object] = {
        "asset_id": "asset-1",
        "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
        "status": GenerationStatus.AVAILABLE,
        "available_capacity_mw": 100.0,
    }
    values.update(overrides)
    return GenerationAvailabilityRecord.model_validate(values)


def _news_record(**overrides: object) -> NewsEvent:
    values: dict[str, object] = {
        "event_id": "evt-1",
        "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
        "headline": "Unit outage announced",
        "summary": "A generating unit is scheduled offline.",
    }
    values.update(overrides)
    return NewsEvent.model_validate(values)


def _market_record(**overrides: object) -> MarketPriceRecord:
    values: dict[str, object] = {
        "market_id": "market-1",
        "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
        "price": EnergyPrice(amount_per_mwh=Decimal("45.00"), currency="EUR"),
    }
    values.update(overrides)
    return MarketPriceRecord.model_validate(values)


def _weather_result(
    records: tuple[WeatherRecord, ...] | None = None,
) -> WeatherAndRenewableForecastResult:
    return WeatherAndRenewableForecastResult(records=() if records is None else records)


def _hydro_result(records: tuple[HydroRecord, ...] | None = None) -> HydroResourcesResult:
    return HydroResourcesResult(records=() if records is None else records)


def _generation_result(
    records: tuple[GenerationAvailabilityRecord, ...] | None = None,
) -> GenerationAvailabilityResult:
    return GenerationAvailabilityResult(records=() if records is None else records)


def _news_result(records: tuple[NewsEvent, ...] | None = None) -> NewsIntelligenceResult:
    return NewsIntelligenceResult(records=() if records is None else records)


def _market_result(
    records: tuple[MarketPriceRecord, ...] | None = None,
) -> MarketMonitoringResult:
    return MarketMonitoringResult(records=() if records is None else records)


def _success(**overrides: object) -> ParallelIngestionSuccess:
    values: dict[str, object] = {
        "weather_and_renewable_forecast": _weather_result(),
        "hydro_resources": _hydro_result(),
        "generation_availability": _generation_result(),
        "news_intelligence": _news_result(),
        "market_monitoring": _market_result(),
    }
    values.update(overrides)
    return ParallelIngestionSuccess(**values)  # type: ignore[arg-type]


def test_success_can_be_constructed_from_existing_result_dtos() -> None:
    weather = _weather_result()
    hydro = _hydro_result()
    generation = _generation_result()
    news = _news_result()
    market = _market_result()
    success = ParallelIngestionSuccess(
        weather_and_renewable_forecast=weather,
        hydro_resources=hydro,
        generation_availability=generation,
        news_intelligence=news,
        market_monitoring=market,
    )
    assert isinstance(success.weather_and_renewable_forecast, WeatherAndRenewableForecastResult)
    assert isinstance(success.hydro_resources, HydroResourcesResult)
    assert isinstance(success.generation_availability, GenerationAvailabilityResult)
    assert isinstance(success.news_intelligence, NewsIntelligenceResult)
    assert isinstance(success.market_monitoring, MarketMonitoringResult)


def test_success_preserves_supplied_result_objects_exactly() -> None:
    weather = _weather_result(records=(_weather_record(),))
    hydro = _hydro_result(records=(_hydro_record(),))
    generation = _generation_result(records=(_generation_record(),))
    news = _news_result(records=(_news_record(),))
    market = _market_result(records=(_market_record(),))
    success = ParallelIngestionSuccess(
        weather_and_renewable_forecast=weather,
        hydro_resources=hydro,
        generation_availability=generation,
        news_intelligence=news,
        market_monitoring=market,
    )
    assert success.weather_and_renewable_forecast is weather
    assert success.hydro_resources is hydro
    assert success.generation_availability is generation
    assert success.news_intelligence is news
    assert success.market_monitoring is market


def test_success_is_frozen_and_slotted() -> None:
    success = _success()
    assert hasattr(ParallelIngestionSuccess, "__slots__")
    with pytest.raises(FrozenInstanceError):
        success.market_monitoring = _market_result()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        success.weather_and_renewable_forecast = _weather_result()  # type: ignore[misc]


def test_success_public_fields_are_exactly_the_five_results() -> None:
    field_names = tuple(item.name for item in fields(ParallelIngestionSuccess))
    assert field_names == (
        "weather_and_renewable_forecast",
        "hydro_resources",
        "generation_availability",
        "news_intelligence",
        "market_monitoring",
    )


def test_success_rejects_wrong_result_types() -> None:
    with pytest.raises(TypeError, match="weather_and_renewable_forecast must be a"):
        _success(weather_and_renewable_forecast=_hydro_result())
    with pytest.raises(TypeError, match="market_monitoring must be a"):
        _success(market_monitoring=_news_result())
    with pytest.raises(TypeError, match="hydro_resources must be a"):
        _success(hydro_resources=_hydro_request())


def test_success_allows_empty_record_tuples_on_legitimate_results() -> None:
    success = _success()
    assert success.weather_and_renewable_forecast.records == ()
    assert success.hydro_resources.records == ()
    assert success.generation_availability.records == ()
    assert success.news_intelligence.records == ()
    assert success.market_monitoring.records == ()


def test_success_preserves_distinct_result_scopes() -> None:
    weather = _weather_result(records=(_weather_record(location_id="location-west"),))
    hydro = _hydro_result(records=(_hydro_record(resource_id="reservoir-a"),))
    generation = _generation_result(records=(_generation_record(asset_id="asset-north"),))
    news = _news_result(records=(_news_record(event_id="evt-west"),))
    market = _market_result(records=(_market_record(market_id="market-alpha"),))
    success = ParallelIngestionSuccess(
        weather_and_renewable_forecast=weather,
        hydro_resources=hydro,
        generation_availability=generation,
        news_intelligence=news,
        market_monitoring=market,
    )
    assert success.weather_and_renewable_forecast.records[0].location_id == "location-west"
    assert success.hydro_resources.records[0].resource_id == "reservoir-a"
    assert success.generation_availability.records[0].asset_id == "asset-north"
    assert success.news_intelligence.records[0].event_id == "evt-west"
    assert success.market_monitoring.records[0].market_id == "market-alpha"
    assert success.weather_and_renewable_forecast is weather
    assert success.hydro_resources is hydro
    assert success.generation_availability is generation
    assert success.news_intelligence is news
    assert success.market_monitoring is market
    assert weather.records[0].location_id != hydro.records[0].resource_id
    assert generation.records[0].asset_id != market.records[0].market_id


def test_success_does_not_execute_anything() -> None:
    defined_methods = {
        name
        for name, value in vars(ParallelIngestionSuccess).items()
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
        "join",
        "aggregate",
    }
    assert forbidden.isdisjoint(dir(ParallelIngestionSuccess))


def test_success_exposes_no_generic_status_failure_or_degraded_fields() -> None:
    field_names = {item.name for item in fields(ParallelIngestionSuccess)}
    forbidden = {
        "status",
        "failed",
        "failure",
        "error",
        "errors",
        "degraded",
        "skipped",
        "partial",
        "outcome",
        "diagnostics",
        "retry_count",
        "fallback",
    }
    assert forbidden.isdisjoint(field_names)
    assert forbidden.isdisjoint(dir(ParallelIngestionSuccess))


def test_success_construction_does_not_invoke_agents_or_graph() -> None:
    weather = _weather_result()
    hydro = _hydro_result()
    generation = _generation_result()
    news = _news_result()
    market = _market_result()
    success = ParallelIngestionSuccess(
        weather_and_renewable_forecast=weather,
        hydro_resources=hydro,
        generation_availability=generation,
        news_intelligence=news,
        market_monitoring=market,
    )
    assert success.weather_and_renewable_forecast is weather
    assert "run" not in vars(ParallelIngestionSuccess)
    assert not hasattr(ParallelIngestionSuccess, "build_workflow_graph")
    assert not hasattr(success, "_source")


class _StructuralParallelIngestionExecutionFake:
    """Test-only fake that structurally satisfies ``ParallelIngestionExecutionPort``.

    Not a production executor. Does not inherit a production base class.
    """

    def __init__(self, success: ParallelIngestionSuccess) -> None:
        self._success = success
        self.received: ParallelIngestionPlan | None = None

    async def execute(self, plan: ParallelIngestionPlan) -> ParallelIngestionSuccess:
        self.received = plan
        return self._success


def _as_execution_port(
    fake: _StructuralParallelIngestionExecutionFake,
) -> ParallelIngestionExecutionPort:
    """Application-shaped call site: the port type is the only accepted argument."""

    return fake


def test_execution_fake_does_not_inherit_production_base() -> None:
    assert ParallelIngestionExecutionPort not in _StructuralParallelIngestionExecutionFake.__mro__
    assert not any(
        base.__name__ in {"ParallelIngestionExecutionPort", "Protocol"}
        for base in _StructuralParallelIngestionExecutionFake.__bases__
    )


async def test_execution_fake_satisfies_port_with_real_plan_and_success() -> None:
    plan = _plan()
    success = _success()
    fake = _StructuralParallelIngestionExecutionFake(success)
    port = _as_execution_port(fake)
    execute_parameters = inspect.signature(ParallelIngestionExecutionPort.execute).parameters
    assert tuple(execute_parameters) == ("self", "plan")
    assert inspect.iscoroutinefunction(ParallelIngestionExecutionPort.execute)
    assert inspect.iscoroutinefunction(port.execute)
    result = await port.execute(plan)
    assert result is success
    assert fake.received is plan
    assert isinstance(result, ParallelIngestionSuccess)
    assert isinstance(plan, ParallelIngestionPlan)


async def test_execution_fake_allows_empty_record_tuples_to_flow_through() -> None:
    plan = _plan()
    success = _success()
    result = await _as_execution_port(_StructuralParallelIngestionExecutionFake(success)).execute(
        plan
    )
    assert result is success
    assert result.weather_and_renewable_forecast.records == ()
    assert result.hydro_resources.records == ()
    assert result.generation_availability.records == ()
    assert result.news_intelligence.records == ()
    assert result.market_monitoring.records == ()


def test_execution_port_exposes_only_async_execute() -> None:
    defined_methods = {
        name
        for name, value in vars(ParallelIngestionExecutionPort).items()
        if callable(value) and not name.startswith("_")
    }
    assert defined_methods == {"execute"}
    execute = ParallelIngestionExecutionPort.execute
    assert inspect.iscoroutinefunction(execute)
    forbidden = {
        "run",
        "fan_out",
        "fan_in",
        "gather",
        "join",
        "invoke",
        "dispatch",
        "retry",
        "fallback",
        "cancel",
        "close",
        "start",
        "stop",
    }
    assert forbidden.isdisjoint(dir(ParallelIngestionExecutionPort))


async def test_execution_fake_returns_supplied_success_without_transformation() -> None:
    weather = _weather_result()
    hydro = _hydro_result()
    generation = _generation_result()
    news = _news_result()
    market = _market_result()
    success = ParallelIngestionSuccess(
        weather_and_renewable_forecast=weather,
        hydro_resources=hydro,
        generation_availability=generation,
        news_intelligence=news,
        market_monitoring=market,
    )
    plan = _plan()
    result = await _as_execution_port(_StructuralParallelIngestionExecutionFake(success)).execute(
        plan
    )
    assert result is success
    assert result.weather_and_renewable_forecast is weather
    assert result.hydro_resources is hydro
    assert result.generation_availability is generation
    assert result.news_intelligence is news
    assert result.market_monitoring is market
    assert result.weather_and_renewable_forecast.records == weather.records
    assert result.hydro_resources.records == hydro.records
