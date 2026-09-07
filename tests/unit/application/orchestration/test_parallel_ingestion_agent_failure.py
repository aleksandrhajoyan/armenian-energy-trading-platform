"""Phase 2 executor preserves canonical failing-agent attribution."""

from __future__ import annotations

import asyncio
import inspect

import pytest

from energy_trading.application.agents import AgentName
from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.orchestration import (
    ParallelIngestionAgentFailure,
    ParallelIngestionSuccess,
)
from tests.unit.application.orchestration.test_parallel_ingestion_executor import (
    _executor_from_sources,
    _GatedSource,
    _generation_record,
    _hydro_record,
    _ImmediateSource,
    _market_record,
    _news_record,
    _plan,
    _weather_record,
)

_SENTINEL_TEXT = "sentinel-agent-failure-text-not-for-clients"
_PHASE2_AGENT_NAMES = (
    AgentName.WEATHER_AND_RENEWABLE_FORECAST,
    AgentName.HYDRO_RESOURCES,
    AgentName.GENERATION_AVAILABILITY,
    AgentName.NEWS_INTELLIGENCE,
    AgentName.MARKET_MONITORING,
)


def _attributed_failures(
    group: BaseExceptionGroup[Exception],
) -> tuple[ParallelIngestionAgentFailure, ...]:
    return tuple(
        item for item in group.exceptions if isinstance(item, ParallelIngestionAgentFailure)
    )


def test_parallel_ingestion_agent_failure_requires_canonical_agent_name() -> None:
    with pytest.raises(TypeError, match="agent_name must be an AgentName"):
        ParallelIngestionAgentFailure("Weather & Renewable Forecast Agent")  # type: ignore[arg-type]


@pytest.mark.parametrize("agent_name", _PHASE2_AGENT_NAMES)
def test_parallel_ingestion_agent_failure_preserves_agent_and_sanitized_message(
    agent_name: AgentName,
) -> None:
    failure = ParallelIngestionAgentFailure(agent_name)
    expected = f"Parallel ingestion agent failed: {agent_name.value}."
    assert failure.agent_name is agent_name
    assert str(failure) == expected
    assert _SENTINEL_TEXT not in str(failure)
    assert "traceback" not in str(failure).lower()
    public_fields = {name for name in vars(failure) if not name.startswith("_")}
    assert public_fields == {"agent_name"}
    assert failure.__cause__ is None
    signature = inspect.signature(ParallelIngestionAgentFailure.__init__)
    assert tuple(signature.parameters) == ("self", "agent_name")


def _sources_for_failing_agent(
    failing: AgentName,
    error: Exception,
) -> tuple[object, object, object, object, object]:
    ok = {
        AgentName.WEATHER_AND_RENEWABLE_FORECAST: _ImmediateSource((_weather_record(),)),
        AgentName.HYDRO_RESOURCES: _ImmediateSource((_hydro_record(),)),
        AgentName.GENERATION_AVAILABILITY: _ImmediateSource((_generation_record(),)),
        AgentName.NEWS_INTELLIGENCE: _ImmediateSource((_news_record(),)),
        AgentName.MARKET_MONITORING: _ImmediateSource((_market_record(),)),
    }
    ok[failing] = _ImmediateSource(error=error)
    return (
        ok[AgentName.WEATHER_AND_RENEWABLE_FORECAST],
        ok[AgentName.HYDRO_RESOURCES],
        ok[AgentName.GENERATION_AVAILABILITY],
        ok[AgentName.NEWS_INTELLIGENCE],
        ok[AgentName.MARKET_MONITORING],
    )


async def test_success_path_still_returns_exact_five_typed_results() -> None:
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
    result = await executor.execute(_plan())
    assert isinstance(result, ParallelIngestionSuccess)
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


async def test_weather_failure_is_attributed_without_exposing_sentinel_text() -> None:
    weather_started = asyncio.Event()
    hydro_started = asyncio.Event()
    generation_started = asyncio.Event()
    news_started = asyncio.Event()
    market_started = asyncio.Event()
    fail_now = asyncio.Event()
    hold = asyncio.Event()
    error = RuntimeError(_SENTINEL_TEXT)
    weather_source = _GatedSource(weather_started, fail_now, error=error)
    hydro_source = _GatedSource(hydro_started, hold)
    generation_source = _GatedSource(generation_started, hold)
    news_source = _GatedSource(news_started, hold)
    market_source = _GatedSource(market_started, hold)
    executor, _weather, _hydro, _generation, _news, _market = _executor_from_sources(
        weather_source,
        hydro_source,
        generation_source,
        news_source,
        market_source,
    )
    execute_task = asyncio.create_task(executor.execute(_plan()))
    await weather_started.wait()
    await hydro_started.wait()
    await generation_started.wait()
    await news_started.wait()
    await market_started.wait()
    fail_now.set()
    with pytest.raises(ExceptionGroup) as caught:
        await execute_task
    leaves = _attributed_failures(caught.value)
    assert len(leaves) == 1
    leaf = leaves[0]
    assert type(leaf) is ParallelIngestionAgentFailure
    assert leaf.agent_name is AgentName.WEATHER_AND_RENEWABLE_FORECAST
    assert leaf.__cause__ is error
    assert _SENTINEL_TEXT not in str(leaf)
    assert str(leaf) == "Parallel ingestion agent failed: Weather & Renewable Forecast Agent."
    assert hydro_source.cancelled
    assert generation_source.cancelled
    assert news_source.cancelled
    assert market_source.cancelled
    assert not any(isinstance(item, asyncio.CancelledError) for item in caught.value.exceptions)
    assert not any(
        isinstance(item, ParallelIngestionAgentFailure)
        and item.agent_name is not AgentName.WEATHER_AND_RENEWABLE_FORECAST
        for item in caught.value.exceptions
    )


@pytest.mark.parametrize("failing", _PHASE2_AGENT_NAMES)
async def test_each_phase2_agent_failure_maps_to_canonical_agent_name(
    failing: AgentName,
) -> None:
    error = RuntimeError(_SENTINEL_TEXT)
    executor, *_agents = _executor_from_sources(*_sources_for_failing_agent(failing, error))
    with pytest.raises(ExceptionGroup) as caught:
        await executor.execute(_plan())
    leaves = _attributed_failures(caught.value)
    assert len(leaves) == 1
    leaf = leaves[0]
    assert leaf.agent_name is failing
    assert leaf.__cause__ is error
    assert _SENTINEL_TEXT not in str(leaf)
    assert str(leaf) == f"Parallel ingestion agent failed: {failing.value}."


async def test_sibling_cancellation_is_not_reclassified_as_agent_failure() -> None:
    started = [asyncio.Event() for _ in range(5)]
    fail_now = asyncio.Event()
    hold = asyncio.Event()
    error = DependencyUnavailableError("hydro source unavailable")
    hydro_source = _GatedSource(started[1], fail_now, error=error)
    weather_source = _GatedSource(started[0], hold)
    generation_source = _GatedSource(started[2], hold)
    news_source = _GatedSource(started[3], hold)
    market_source = _GatedSource(started[4], hold)
    executor, *_agents = _executor_from_sources(
        weather_source,
        hydro_source,
        generation_source,
        news_source,
        market_source,
    )
    execute_task = asyncio.create_task(executor.execute(_plan()))
    for event in started:
        await event.wait()
    fail_now.set()
    with pytest.raises(ExceptionGroup) as caught:
        await execute_task
    leaves = _attributed_failures(caught.value)
    assert tuple(item.agent_name for item in leaves) == (AgentName.HYDRO_RESOURCES,)
    assert leaves[0].__cause__ is error
    assert weather_source.cancelled
    assert generation_source.cancelled
    assert news_source.cancelled
    assert market_source.cancelled
    cancelled_as_agent_failure = [
        item
        for item in leaves
        if item.agent_name
        in {
            AgentName.WEATHER_AND_RENEWABLE_FORECAST,
            AgentName.GENERATION_AVAILABILITY,
            AgentName.NEWS_INTELLIGENCE,
            AgentName.MARKET_MONITORING,
        }
    ]
    assert cancelled_as_agent_failure == []


async def test_two_real_failures_retain_independent_attribution() -> None:
    started = [asyncio.Event() for _ in range(5)]
    proceed = asyncio.Event()
    weather_error = RuntimeError("weather-sentinel-not-for-clients")
    market_error = RuntimeError("market-sentinel-not-for-clients")
    weather_source = _GatedSource(started[0], proceed, error=weather_error)
    hydro_source = _GatedSource(started[1], proceed, records=(_hydro_record(),))
    generation_source = _GatedSource(started[2], proceed, records=(_generation_record(),))
    news_source = _GatedSource(started[3], proceed, records=(_news_record(),))
    market_source = _GatedSource(started[4], proceed, error=market_error)
    executor, *_agents = _executor_from_sources(
        weather_source,
        hydro_source,
        generation_source,
        news_source,
        market_source,
    )
    execute_task = asyncio.create_task(executor.execute(_plan()))
    for event in started:
        await event.wait()
    proceed.set()
    with pytest.raises(ExceptionGroup) as caught:
        await execute_task
    leaves = _attributed_failures(caught.value)
    by_name = {leaf.agent_name: leaf for leaf in leaves}
    assert set(by_name) == {
        AgentName.WEATHER_AND_RENEWABLE_FORECAST,
        AgentName.MARKET_MONITORING,
    }
    assert by_name[AgentName.WEATHER_AND_RENEWABLE_FORECAST].__cause__ is weather_error
    assert by_name[AgentName.MARKET_MONITORING].__cause__ is market_error
    assert "weather-sentinel-not-for-clients" not in str(
        by_name[AgentName.WEATHER_AND_RENEWABLE_FORECAST]
    )
    assert "market-sentinel-not-for-clients" not in str(by_name[AgentName.MARKET_MONITORING])
