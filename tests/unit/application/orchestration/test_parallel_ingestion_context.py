"""Application-owned parallel-ingestion workflow-context Protocol."""

from __future__ import annotations

import inspect
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import get_type_hints

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
    ParallelIngestionPlan,
    ParallelIngestionSuccess,
    ParallelIngestionWorkflowContextPort,
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
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


class _StructuralParallelIngestionWorkflowContextFake:
    """Test-only fake that structurally satisfies the context Protocol.

    Not a production context implementation. Does not inherit a production
    base class.
    """

    def __init__(
        self,
        plan: ParallelIngestionPlan,
        recorded: list[tuple[str, ParallelIngestionSuccess]] | None = None,
    ) -> None:
        self._plan = plan
        self.received_resolve_workflow_id: str | None = None
        self.received_record_workflow_id: str | None = None
        self.received_success: ParallelIngestionSuccess | None = None
        self.recorded = recorded if recorded is not None else []

    async def resolve_plan(self, workflow_id: str) -> ParallelIngestionPlan:
        self.received_resolve_workflow_id = workflow_id
        return self._plan

    async def record_success(self, workflow_id: str, success: ParallelIngestionSuccess) -> None:
        self.received_record_workflow_id = workflow_id
        self.received_success = success
        self.recorded.append((workflow_id, success))


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


def _market_result() -> MarketMonitoringResult:
    return MarketMonitoringResult(
        records=(
            MarketPriceRecord.model_validate(
                {
                    "market_id": "market-1",
                    "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
                    "price": EnergyPrice(amount_per_mwh=Decimal("45.00"), currency="EUR"),
                }
            ),
        )
    )


def _success() -> ParallelIngestionSuccess:
    return ParallelIngestionSuccess(
        weather_and_renewable_forecast=_weather_result(),
        hydro_resources=_hydro_result(),
        generation_availability=_generation_result(),
        news_intelligence=_news_result(),
        market_monitoring=_market_result(),
    )


def _as_context_port(
    fake: _StructuralParallelIngestionWorkflowContextFake,
) -> ParallelIngestionWorkflowContextPort:
    """Application-shaped call site: the port type is the only accepted argument."""

    return fake


def test_context_fake_does_not_inherit_production_base() -> None:
    assert (
        ParallelIngestionWorkflowContextPort
        not in _StructuralParallelIngestionWorkflowContextFake.__mro__
    )
    assert not any(
        base.__name__ in {"ParallelIngestionWorkflowContextPort", "Protocol"}
        for base in _StructuralParallelIngestionWorkflowContextFake.__bases__
    )


def test_context_port_exposes_exactly_two_async_operations() -> None:
    defined_methods = {
        name
        for name, value in vars(ParallelIngestionWorkflowContextPort).items()
        if callable(value) and not name.startswith("_")
    }
    assert defined_methods == {"resolve_plan", "record_success"}
    assert inspect.iscoroutinefunction(ParallelIngestionWorkflowContextPort.resolve_plan)
    assert inspect.iscoroutinefunction(ParallelIngestionWorkflowContextPort.record_success)
    resolve_parameters = inspect.signature(
        ParallelIngestionWorkflowContextPort.resolve_plan
    ).parameters
    assert tuple(resolve_parameters) == ("self", "workflow_id")
    record_parameters = inspect.signature(
        ParallelIngestionWorkflowContextPort.record_success
    ).parameters
    assert tuple(record_parameters) == ("self", "workflow_id", "success")


def test_workflow_id_annotation_matches_workflow_state() -> None:
    state_workflow_id_type = get_type_hints(WorkflowState)["workflow_id"]
    resolve_hints = get_type_hints(ParallelIngestionWorkflowContextPort.resolve_plan)
    record_hints = get_type_hints(ParallelIngestionWorkflowContextPort.record_success)
    assert resolve_hints["workflow_id"] is state_workflow_id_type
    assert record_hints["workflow_id"] is state_workflow_id_type
    assert resolve_hints["return"] is ParallelIngestionPlan
    assert record_hints["success"] is ParallelIngestionSuccess
    assert record_hints["return"] is type(None)


async def test_context_fake_satisfies_port_preserving_plan_and_workflow_id() -> None:
    plan = _plan()
    fake = _StructuralParallelIngestionWorkflowContextFake(plan)
    port = _as_context_port(fake)
    assert inspect.iscoroutinefunction(port.resolve_plan)
    assert inspect.iscoroutinefunction(port.record_success)
    workflow_id = "workflow-context-1"
    resolved = await port.resolve_plan(workflow_id)
    assert resolved is plan
    assert fake.received_resolve_workflow_id is workflow_id
    assert isinstance(resolved, ParallelIngestionPlan)


async def test_record_success_preserves_workflow_id_and_success_identity() -> None:
    plan = _plan()
    success = _success()
    fake = _StructuralParallelIngestionWorkflowContextFake(plan)
    port = _as_context_port(fake)
    workflow_id = "workflow-context-1"
    result = await port.record_success(workflow_id, success)
    assert result is None
    assert fake.received_record_workflow_id is workflow_id
    assert fake.received_success is success
    assert fake.recorded == [(workflow_id, success)]
    assert fake.recorded[0][1] is success


async def test_context_fake_does_not_transform_plan_or_success() -> None:
    weather_request = _weather_request()
    hydro_request = _hydro_request()
    generation_request = _generation_request()
    news_request = _news_request()
    market_request = _market_request()
    plan = ParallelIngestionPlan(
        weather_and_renewable_forecast=weather_request,
        hydro_resources=hydro_request,
        generation_availability=generation_request,
        news_intelligence=news_request,
        market_monitoring=market_request,
    )
    weather_result = _weather_result()
    hydro_result = _hydro_result()
    generation_result = _generation_result()
    news_result = _news_result()
    market_result = _market_result()
    success = ParallelIngestionSuccess(
        weather_and_renewable_forecast=weather_result,
        hydro_resources=hydro_result,
        generation_availability=generation_result,
        news_intelligence=news_result,
        market_monitoring=market_result,
    )
    fake = _StructuralParallelIngestionWorkflowContextFake(plan)
    port = _as_context_port(fake)
    workflow_id = "workflow-context-1"
    resolved = await port.resolve_plan(workflow_id)
    recorded = await port.record_success(workflow_id, success)
    assert resolved is plan
    assert recorded is None
    assert resolved.weather_and_renewable_forecast is weather_request
    assert resolved.hydro_resources is hydro_request
    assert resolved.generation_availability is generation_request
    assert resolved.news_intelligence is news_request
    assert resolved.market_monitoring is market_request
    assert fake.received_success is success
    assert success.weather_and_renewable_forecast is weather_result
    assert success.hydro_resources is hydro_result
    assert success.generation_availability is generation_result
    assert success.news_intelligence is news_result
    assert success.market_monitoring is market_result


async def test_context_accepts_workflow_state_identity_without_live_services() -> None:
    plan = _plan()
    success = _success()
    fake = _StructuralParallelIngestionWorkflowContextFake(plan)
    port = _as_context_port(fake)
    state = WorkflowState(
        workflow_id="workflow-from-state",
        portfolio_id="portfolio-1",
        delivery_date=date(2026, 10, 1),
        correlation_id="corr-1",
        phase=WorkflowPhase.INGESTION,
        status=WorkflowStatus.RUNNING,
    )
    resolved = await port.resolve_plan(state.workflow_id)
    recorded = await port.record_success(state.workflow_id, success)
    assert resolved is plan
    assert recorded is None
    assert fake.received_resolve_workflow_id is state.workflow_id
    assert fake.received_record_workflow_id is state.workflow_id
    assert fake.received_success is success
    assert "parallel_ingestion_plan" not in state.__slots__
    assert "parallel_ingestion_success" not in state.__slots__
