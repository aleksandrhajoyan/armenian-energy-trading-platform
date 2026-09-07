"""Concurrent parallel-ingestion executor over the five Phase 2 application agents."""

from __future__ import annotations

import asyncio
import inspect
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from energy_trading.application.agents.generation_availability import (
    GenerationAvailabilityAgent,
    GenerationAvailabilityRequest,
    GenerationAvailabilityResult,
)
from energy_trading.application.agents.hydro_resources import (
    HydroResourcesAgent,
    HydroResourcesRequest,
    HydroResourcesResult,
)
from energy_trading.application.agents.market_monitoring import (
    MarketMonitoringAgent,
    MarketMonitoringRequest,
    MarketMonitoringResult,
)
from energy_trading.application.agents.news_intelligence import (
    NewsIntelligenceAgent,
    NewsIntelligenceRequest,
    NewsIntelligenceResult,
)
from energy_trading.application.agents.weather_and_renewable_forecast import (
    WeatherAndRenewableForecastAgent,
    WeatherAndRenewableForecastRequest,
    WeatherAndRenewableForecastResult,
)
from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.orchestration import (
    ConcurrentParallelIngestionExecutor,
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


class _RecordingWeatherAgent(WeatherAndRenewableForecastAgent):
    def __init__(self, source: object) -> None:
        super().__init__(source)  # type: ignore[arg-type]
        self.calls = 0
        self.received_request: WeatherAndRenewableForecastRequest | None = None
        self.last_result: WeatherAndRenewableForecastResult | None = None

    async def run(
        self, request: WeatherAndRenewableForecastRequest
    ) -> WeatherAndRenewableForecastResult:
        self.calls += 1
        self.received_request = request
        result = await super().run(request)
        self.last_result = result
        return result


class _RecordingHydroAgent(HydroResourcesAgent):
    def __init__(self, source: object) -> None:
        super().__init__(source)  # type: ignore[arg-type]
        self.calls = 0
        self.received_request: HydroResourcesRequest | None = None
        self.last_result: HydroResourcesResult | None = None

    async def run(self, request: HydroResourcesRequest) -> HydroResourcesResult:
        self.calls += 1
        self.received_request = request
        result = await super().run(request)
        self.last_result = result
        return result


class _RecordingGenerationAgent(GenerationAvailabilityAgent):
    def __init__(self, source: object) -> None:
        super().__init__(source)  # type: ignore[arg-type]
        self.calls = 0
        self.received_request: GenerationAvailabilityRequest | None = None
        self.last_result: GenerationAvailabilityResult | None = None

    async def run(self, request: GenerationAvailabilityRequest) -> GenerationAvailabilityResult:
        self.calls += 1
        self.received_request = request
        result = await super().run(request)
        self.last_result = result
        return result


class _RecordingNewsAgent(NewsIntelligenceAgent):
    def __init__(self, source: object) -> None:
        super().__init__(source)  # type: ignore[arg-type]
        self.calls = 0
        self.received_request: NewsIntelligenceRequest | None = None
        self.last_result: NewsIntelligenceResult | None = None

    async def run(self, request: NewsIntelligenceRequest) -> NewsIntelligenceResult:
        self.calls += 1
        self.received_request = request
        result = await super().run(request)
        self.last_result = result
        return result


class _RecordingMarketAgent(MarketMonitoringAgent):
    def __init__(self, source: object) -> None:
        super().__init__(source)  # type: ignore[arg-type]
        self.calls = 0
        self.received_request: MarketMonitoringRequest | None = None
        self.last_result: MarketMonitoringResult | None = None

    async def run(self, request: MarketMonitoringRequest) -> MarketMonitoringResult:
        self.calls += 1
        self.received_request = request
        result = await super().run(request)
        self.last_result = result
        return result


class _GatedSource:
    """Test-only source fake. Not a production adapter."""

    def __init__(
        self,
        started: asyncio.Event,
        proceed: asyncio.Event,
        records: tuple[object, ...] = (),
        error: Exception | None = None,
    ) -> None:
        self.started = started
        self.proceed = proceed
        self.records = records
        self.error = error
        self.calls = 0
        self.completed = False
        self.cancelled = False

    async def fetch(self, **_kwargs: object) -> tuple[object, ...]:
        self.calls += 1
        self.started.set()
        try:
            await self.proceed.wait()
            if self.error is not None:
                raise self.error
            self.completed = True
            return self.records
        except asyncio.CancelledError:
            self.cancelled = True
            raise


class _ImmediateSource:
    """Test-only source fake. Not a production adapter."""

    def __init__(self, records: tuple[object, ...] = (), error: Exception | None = None) -> None:
        self.records = records
        self.error = error
        self.calls = 0

    async def fetch(self, **_kwargs: object) -> tuple[object, ...]:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.records


def _weather_request() -> WeatherAndRenewableForecastRequest:
    return WeatherAndRenewableForecastRequest(
        location_id="loc-1",
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )


def _hydro_request() -> HydroResourcesRequest:
    return HydroResourcesRequest(
        resource_id="hydro-1",
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )


def _generation_request() -> GenerationAvailabilityRequest:
    return GenerationAvailabilityRequest(
        asset_id="asset-1",
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )


def _news_request() -> NewsIntelligenceRequest:
    return NewsIntelligenceRequest(
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )


def _market_request() -> MarketMonitoringRequest:
    return MarketMonitoringRequest(
        market_id="market-1",
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )


def _plan() -> ParallelIngestionPlan:
    return ParallelIngestionPlan(
        weather_and_renewable_forecast=_weather_request(),
        hydro_resources=_hydro_request(),
        generation_availability=_generation_request(),
        news_intelligence=_news_request(),
        market_monitoring=_market_request(),
    )


def _weather_record() -> WeatherRecord:
    return WeatherRecord.model_validate(
        {
            "location_id": "loc-1",
            "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
            "temperature_c": 12.5,
        }
    )


def _hydro_record() -> HydroRecord:
    return HydroRecord.model_validate(
        {
            "resource_id": "hydro-1",
            "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
        }
    )


def _generation_record() -> GenerationAvailabilityRecord:
    return GenerationAvailabilityRecord.model_validate(
        {
            "asset_id": "asset-1",
            "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
            "status": GenerationStatus.AVAILABLE,
            "available_capacity_mw": 100.0,
        }
    )


def _news_record() -> NewsEvent:
    return NewsEvent.model_validate(
        {
            "event_id": "evt-1",
            "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
            "headline": "Unit outage announced",
            "summary": "A generating unit is scheduled offline.",
        }
    )


def _market_record() -> MarketPriceRecord:
    return MarketPriceRecord.model_validate(
        {
            "market_id": "market-1",
            "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
            "price": EnergyPrice(amount_per_mwh=Decimal("45.00"), currency="EUR"),
        }
    )


def _as_execution_port(
    executor: ConcurrentParallelIngestionExecutor,
) -> ParallelIngestionExecutionPort:
    return executor


def _executor_from_sources(
    weather_source: object,
    hydro_source: object,
    generation_source: object,
    news_source: object,
    market_source: object,
) -> tuple[
    ConcurrentParallelIngestionExecutor,
    _RecordingWeatherAgent,
    _RecordingHydroAgent,
    _RecordingGenerationAgent,
    _RecordingNewsAgent,
    _RecordingMarketAgent,
]:
    weather_agent = _RecordingWeatherAgent(weather_source)
    hydro_agent = _RecordingHydroAgent(hydro_source)
    generation_agent = _RecordingGenerationAgent(generation_source)
    news_agent = _RecordingNewsAgent(news_source)
    market_agent = _RecordingMarketAgent(market_source)
    executor = ConcurrentParallelIngestionExecutor(
        weather_and_renewable_forecast=weather_agent,
        hydro_resources=hydro_agent,
        generation_availability=generation_agent,
        news_intelligence=news_agent,
        market_monitoring=market_agent,
    )
    return executor, weather_agent, hydro_agent, generation_agent, news_agent, market_agent


def test_executor_does_not_inherit_protocol() -> None:
    assert ParallelIngestionExecutionPort not in ConcurrentParallelIngestionExecutor.__mro__
    assert not any(
        base.__name__ in {"ParallelIngestionExecutionPort", "Protocol"}
        for base in ConcurrentParallelIngestionExecutor.__bases__
    )


def test_executor_public_surface_is_async_execute() -> None:
    defined_methods = {
        name
        for name, value in vars(ConcurrentParallelIngestionExecutor).items()
        if callable(value) and not name.startswith("_")
    }
    assert defined_methods == {"execute"}
    assert inspect.iscoroutinefunction(ConcurrentParallelIngestionExecutor.execute)
    parameters = inspect.signature(ConcurrentParallelIngestionExecutor.execute).parameters
    assert tuple(parameters) == ("self", "plan")
    constructor = inspect.signature(ConcurrentParallelIngestionExecutor.__init__).parameters
    assert tuple(constructor) == (
        "self",
        "weather_and_renewable_forecast",
        "hydro_resources",
        "generation_availability",
        "news_intelligence",
        "market_monitoring",
    )


def test_executor_constructor_does_not_accept_failure_policy() -> None:
    constructor = inspect.signature(ConcurrentParallelIngestionExecutor.__init__).parameters
    forbidden = {
        "failure_policy",
        "failure_policy_port",
        "policy",
        "retry",
        "fallback",
        "graph",
        "registry",
        "factory",
    }
    assert forbidden.isdisjoint(constructor)


async def test_executor_structurally_satisfies_port_and_returns_success() -> None:
    weather_records = (_weather_record(),)
    hydro_records = (_hydro_record(),)
    generation_records = (_generation_record(),)
    news_records = (_news_record(),)
    market_records = (_market_record(),)
    executor, weather_agent, hydro_agent, generation_agent, news_agent, market_agent = (
        _executor_from_sources(
            _ImmediateSource(weather_records),
            _ImmediateSource(hydro_records),
            _ImmediateSource(generation_records),
            _ImmediateSource(news_records),
            _ImmediateSource(market_records),
        )
    )
    plan = _plan()
    result = await _as_execution_port(executor).execute(plan)
    assert isinstance(result, ParallelIngestionSuccess)
    assert weather_agent.calls == 1
    assert hydro_agent.calls == 1
    assert generation_agent.calls == 1
    assert news_agent.calls == 1
    assert market_agent.calls == 1
    assert weather_agent.received_request is plan.weather_and_renewable_forecast
    assert hydro_agent.received_request is plan.hydro_resources
    assert generation_agent.received_request is plan.generation_availability
    assert news_agent.received_request is plan.news_intelligence
    assert market_agent.received_request is plan.market_monitoring
    assert result.weather_and_renewable_forecast is weather_agent.last_result
    assert result.hydro_resources is hydro_agent.last_result
    assert result.generation_availability is generation_agent.last_result
    assert result.news_intelligence is news_agent.last_result
    assert result.market_monitoring is market_agent.last_result
    assert result.weather_and_renewable_forecast.records is weather_records
    assert result.hydro_resources.records is hydro_records
    assert result.generation_availability.records is generation_records
    assert result.news_intelligence.records is news_records
    assert result.market_monitoring.records is market_records


async def test_executor_allows_empty_result_tuples() -> None:
    executor, *_agents = _executor_from_sources(
        _ImmediateSource(),
        _ImmediateSource(),
        _ImmediateSource(),
        _ImmediateSource(),
        _ImmediateSource(),
    )
    result = await executor.execute(_plan())
    assert result.weather_and_renewable_forecast.records == ()
    assert result.hydro_resources.records == ()
    assert result.generation_availability.records == ()
    assert result.news_intelligence.records == ()
    assert result.market_monitoring.records == ()


async def test_executor_starts_all_five_branches_before_any_is_released() -> None:
    weather_started = asyncio.Event()
    hydro_started = asyncio.Event()
    generation_started = asyncio.Event()
    news_started = asyncio.Event()
    market_started = asyncio.Event()
    proceed = asyncio.Event()
    weather_records = (_weather_record(),)
    hydro_records = (_hydro_record(),)
    generation_records = (_generation_record(),)
    news_records = (_news_record(),)
    market_records = (_market_record(),)
    executor, weather_agent, hydro_agent, generation_agent, news_agent, market_agent = (
        _executor_from_sources(
            _GatedSource(weather_started, proceed, weather_records),
            _GatedSource(hydro_started, proceed, hydro_records),
            _GatedSource(generation_started, proceed, generation_records),
            _GatedSource(news_started, proceed, news_records),
            _GatedSource(market_started, proceed, market_records),
        )
    )
    plan = _plan()
    execute_task = asyncio.create_task(executor.execute(plan))
    await weather_started.wait()
    await hydro_started.wait()
    await generation_started.wait()
    await news_started.wait()
    await market_started.wait()
    assert weather_agent.calls == 1
    assert hydro_agent.calls == 1
    assert generation_agent.calls == 1
    assert news_agent.calls == 1
    assert market_agent.calls == 1
    assert not execute_task.done()
    proceed.set()
    result = await execute_task
    assert isinstance(result, ParallelIngestionSuccess)
    assert weather_agent.received_request is plan.weather_and_renewable_forecast
    assert hydro_agent.received_request is plan.hydro_resources
    assert generation_agent.received_request is plan.generation_availability
    assert news_agent.received_request is plan.news_intelligence
    assert market_agent.received_request is plan.market_monitoring
    assert result.weather_and_renewable_forecast is weather_agent.last_result
    assert result.hydro_resources is hydro_agent.last_result
    assert result.generation_availability is generation_agent.last_result
    assert result.news_intelligence is news_agent.last_result
    assert result.market_monitoring is market_agent.last_result


async def test_single_branch_failure_does_not_return_success_or_retry() -> None:
    weather_started = asyncio.Event()
    hydro_started = asyncio.Event()
    generation_started = asyncio.Event()
    news_started = asyncio.Event()
    market_started = asyncio.Event()
    fail_now = asyncio.Event()
    hold = asyncio.Event()
    error = DependencyUnavailableError("weather source unavailable")
    weather_source = _GatedSource(weather_started, fail_now, error=error)
    hydro_source = _GatedSource(hydro_started, hold)
    generation_source = _GatedSource(generation_started, hold)
    news_source = _GatedSource(news_started, hold)
    market_source = _GatedSource(market_started, hold)
    executor, weather_agent, hydro_agent, generation_agent, news_agent, market_agent = (
        _executor_from_sources(
            weather_source,
            hydro_source,
            generation_source,
            news_source,
            market_source,
        )
    )
    execute_task = asyncio.create_task(executor.execute(_plan()))
    await weather_started.wait()
    await hydro_started.wait()
    await generation_started.wait()
    await news_started.wait()
    await market_started.wait()
    assert not execute_task.done()
    fail_now.set()
    with pytest.raises(ExceptionGroup) as exc_info:
        await execute_task
    assert any(isinstance(item, DependencyUnavailableError) for item in exc_info.value.exceptions)
    assert weather_agent.calls == 1
    assert hydro_agent.calls == 1
    assert generation_agent.calls == 1
    assert news_agent.calls == 1
    assert market_agent.calls == 1
    assert weather_source.calls == 1
    assert hydro_source.calls == 1
    assert generation_source.calls == 1
    assert news_source.calls == 1
    assert market_source.calls == 1
    assert hydro_source.cancelled
    assert generation_source.cancelled
    assert news_source.cancelled
    assert market_source.cancelled
    assert not hydro_source.completed
    assert not generation_source.completed
    assert not news_source.completed
    assert not market_source.completed
    assert weather_agent.last_result is None
    assert hydro_agent.last_result is None
    assert generation_agent.last_result is None
    assert news_agent.last_result is None
    assert market_agent.last_result is None
    assert not hasattr(exc_info.value, "weather_and_renewable_forecast")
    assert type(exc_info.value) is ExceptionGroup


async def test_executor_does_not_fabricate_partial_success_on_failure() -> None:
    error = DependencyUnavailableError("market source unavailable")
    executor, weather_agent, hydro_agent, generation_agent, news_agent, market_agent = (
        _executor_from_sources(
            _ImmediateSource((_weather_record(),)),
            _ImmediateSource((_hydro_record(),)),
            _ImmediateSource((_generation_record(),)),
            _ImmediateSource((_news_record(),)),
            _ImmediateSource(error=error),
        )
    )
    with pytest.raises(ExceptionGroup) as exc_info:
        await executor.execute(_plan())
    assert any(isinstance(item, DependencyUnavailableError) for item in exc_info.value.exceptions)
    assert market_agent.calls == 1
    assert weather_agent.calls == 1
    assert hydro_agent.calls == 1
    assert generation_agent.calls == 1
    assert news_agent.calls == 1
    assert market_agent.last_result is None
    assert not isinstance(exc_info.value, ParallelIngestionSuccess)
