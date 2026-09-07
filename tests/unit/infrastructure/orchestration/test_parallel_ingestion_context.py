"""Process-local in-memory ParallelIngestionWorkflowContextPort adapter."""

from __future__ import annotations

import asyncio
import inspect
from datetime import UTC, datetime
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
from energy_trading.application.errors import ConflictError, ResourceNotFoundError
from energy_trading.application.orchestration import (
    ParallelIngestionPlan,
    ParallelIngestionSuccess,
    ParallelIngestionWorkflowContextPort,
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
from energy_trading.infrastructure.orchestration.parallel_ingestion_context import (
    InMemoryParallelIngestionWorkflowContext,
)

_WORKFLOW_ID = "workflow-1"
_MISSING_WORKFLOW_ID = "workflow-id-sentinel-MUST-NOT-LEAK"
_OTHER_WORKFLOW_ID = "workflow-2"


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


def _other_plan() -> ParallelIngestionPlan:
    return ParallelIngestionPlan(
        weather_and_renewable_forecast=WeatherAndRenewableForecastRequest(
            location_id="loc-2",
            horizon_start=datetime(2026, 11, 1, 0, tzinfo=UTC),
            horizon_end=datetime(2026, 11, 2, 0, tzinfo=UTC),
        ),
        hydro_resources=_hydro_request(),
        generation_availability=_generation_request(),
        news_intelligence=_news_request(),
        market_monitoring=_market_request(),
    )


def _weather_result() -> WeatherAndRenewableForecastResult:
    return WeatherAndRenewableForecastResult(
        records=(
            WeatherRecord.model_validate(
                {
                    "location_id": "loc-1",
                    "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
                    "temperature_c": 12.5,
                }
            ),
        )
    )


def _hydro_result() -> HydroResourcesResult:
    return HydroResourcesResult(
        records=(
            HydroRecord.model_validate(
                {
                    "resource_id": "hydro-1",
                    "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
                }
            ),
        )
    )


def _generation_result() -> GenerationAvailabilityResult:
    return GenerationAvailabilityResult(
        records=(
            GenerationAvailabilityRecord.model_validate(
                {
                    "asset_id": "asset-1",
                    "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
                    "status": GenerationStatus.AVAILABLE,
                    "available_capacity_mw": 100.0,
                }
            ),
        )
    )


def _news_result() -> NewsIntelligenceResult:
    return NewsIntelligenceResult(
        records=(
            NewsEvent.model_validate(
                {
                    "event_id": "evt-1",
                    "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
                    "headline": "Unit outage announced",
                    "summary": "A generating unit is scheduled offline.",
                }
            ),
        )
    )


def _market_result(*, amount: str = "45.00") -> MarketMonitoringResult:
    return MarketMonitoringResult(
        records=(
            MarketPriceRecord.model_validate(
                {
                    "market_id": "market-1",
                    "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
                    "price": EnergyPrice(amount_per_mwh=Decimal(amount), currency="EUR"),
                }
            ),
        )
    )


def _success(*, amount: str = "45.00") -> ParallelIngestionSuccess:
    return ParallelIngestionSuccess(
        weather_and_renewable_forecast=_weather_result(),
        hydro_resources=_hydro_result(),
        generation_availability=_generation_result(),
        news_intelligence=_news_result(),
        market_monitoring=_market_result(amount=amount),
    )


def _as_context_port(
    context: InMemoryParallelIngestionWorkflowContext,
) -> ParallelIngestionWorkflowContextPort:
    """Application-shaped call site: the port type is the only accepted argument."""

    return context


def _context(
    plans: dict[str, ParallelIngestionPlan] | None = None,
) -> InMemoryParallelIngestionWorkflowContext:
    prepared = {_WORKFLOW_ID: _plan()} if plans is None else plans
    return InMemoryParallelIngestionWorkflowContext(prepared)


def test_in_memory_context_does_not_inherit_production_base() -> None:
    assert ParallelIngestionWorkflowContextPort not in (
        InMemoryParallelIngestionWorkflowContext.__mro__
    )
    assert not any(
        base.__name__
        in {
            "ParallelIngestionWorkflowContextPort",
            "Protocol",
            "ABC",
        }
        for base in InMemoryParallelIngestionWorkflowContext.__bases__
    )


def test_in_memory_context_structurally_satisfies_port() -> None:
    context = _context()
    port = _as_context_port(context)
    assert inspect.iscoroutinefunction(port.resolve_plan)
    assert inspect.iscoroutinefunction(port.record_success)
    resolve_parameters = inspect.signature(port.resolve_plan).parameters
    assert tuple(resolve_parameters) == ("workflow_id",)
    record_parameters = inspect.signature(port.record_success).parameters
    assert tuple(record_parameters) == ("workflow_id", "success")


async def test_known_workflow_returns_exact_plan_object() -> None:
    plan = _plan()
    context = InMemoryParallelIngestionWorkflowContext({_WORKFLOW_ID: plan})
    port = _as_context_port(context)
    resolved = await port.resolve_plan(_WORKFLOW_ID)
    assert resolved is plan


async def test_unknown_workflow_raises_sanitized_not_found() -> None:
    context = _context()
    port = _as_context_port(context)
    with pytest.raises(ResourceNotFoundError) as captured:
        await port.resolve_plan(_MISSING_WORKFLOW_ID)
    assert captured.value.code == "resource_not_found"
    assert captured.value.message == "Parallel-ingestion plan was not found."
    assert _MISSING_WORKFLOW_ID not in captured.value.message
    assert _MISSING_WORKFLOW_ID not in str(captured.value)


async def test_caller_plan_mapping_mutation_does_not_affect_context() -> None:
    plan = _plan()
    extra = _other_plan()
    plans = {_WORKFLOW_ID: plan}
    context = InMemoryParallelIngestionWorkflowContext(plans)
    port = _as_context_port(context)
    plans[_OTHER_WORKFLOW_ID] = extra
    del plans[_WORKFLOW_ID]
    resolved = await port.resolve_plan(_WORKFLOW_ID)
    assert resolved is plan
    with pytest.raises(ResourceNotFoundError):
        await port.resolve_plan(_OTHER_WORKFLOW_ID)


async def test_first_record_success_returns_none() -> None:
    context = _context()
    port = _as_context_port(context)
    result = await port.record_success(_WORKFLOW_ID, _success())
    assert result is None


async def test_same_object_retry_is_idempotent() -> None:
    context = _context()
    port = _as_context_port(context)
    original = _success()
    conflicting = _success(amount="99.00")
    first = await port.record_success(_WORKFLOW_ID, original)
    retry = await port.record_success(_WORKFLOW_ID, original)
    assert first is None
    assert retry is None
    with pytest.raises(ConflictError):
        await port.record_success(_WORKFLOW_ID, conflicting)
    assert await port.record_success(_WORKFLOW_ID, original) is None


async def test_value_equal_retry_does_not_replace_original() -> None:
    context = _context()
    port = _as_context_port(context)
    original = _success()
    equal_retry = _success()
    conflicting = _success(amount="99.00")
    assert original == equal_retry
    assert original is not equal_retry
    await port.record_success(_WORKFLOW_ID, original)
    assert await port.record_success(_WORKFLOW_ID, equal_retry) is None
    with pytest.raises(ConflictError):
        await port.record_success(_WORKFLOW_ID, conflicting)
    assert await port.record_success(_WORKFLOW_ID, original) is None
    with pytest.raises(ConflictError):
        await port.record_success(_WORKFLOW_ID, conflicting)


async def test_conflicting_success_raises_and_leaves_original_authoritative() -> None:
    context = _context()
    port = _as_context_port(context)
    original = _success()
    conflicting = _success(amount="12.00")
    await port.record_success(_WORKFLOW_ID, original)
    with pytest.raises(ConflictError) as captured:
        await port.record_success(_WORKFLOW_ID, conflicting)
    assert captured.value.code == "conflict"
    assert (
        captured.value.message == "Parallel-ingestion success conflicts with the recorded result."
    )
    assert _WORKFLOW_ID not in captured.value.message
    assert _WORKFLOW_ID not in str(captured.value)
    assert "12.00" not in captured.value.message
    assert await port.record_success(_WORKFLOW_ID, original) is None
    with pytest.raises(ConflictError):
        await port.record_success(_WORKFLOW_ID, conflicting)


async def test_independent_workflow_identities_do_not_conflict() -> None:
    first_plan = _plan()
    second_plan = _other_plan()
    context = InMemoryParallelIngestionWorkflowContext(
        {_WORKFLOW_ID: first_plan, _OTHER_WORKFLOW_ID: second_plan}
    )
    port = _as_context_port(context)
    first = _success()
    second = _success(amount="70.00")
    assert await port.record_success(_WORKFLOW_ID, first) is None
    assert await port.record_success(_OTHER_WORKFLOW_ID, second) is None
    assert await port.record_success(_WORKFLOW_ID, first) is None
    assert await port.record_success(_OTHER_WORKFLOW_ID, second) is None
    with pytest.raises(ConflictError):
        await port.record_success(_WORKFLOW_ID, second)
    with pytest.raises(ConflictError):
        await port.record_success(_OTHER_WORKFLOW_ID, first)


async def test_concurrent_equal_retries_all_succeed() -> None:
    context = _context()
    port = _as_context_port(context)
    successes = [_success() for _ in range(8)]
    assert all(item == successes[0] for item in successes)

    async with asyncio.TaskGroup() as group:
        for item in successes:
            group.create_task(port.record_success(_WORKFLOW_ID, item))

    conflicting = _success(amount="88.00")
    with pytest.raises(ConflictError):
        await port.record_success(_WORKFLOW_ID, conflicting)
    assert await port.record_success(_WORKFLOW_ID, successes[0]) is None
