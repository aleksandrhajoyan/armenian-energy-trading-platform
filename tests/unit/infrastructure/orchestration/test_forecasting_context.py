"""Process-local in-memory ForecastingWorkflowContextPort adapter."""

from __future__ import annotations

import asyncio
import inspect
from datetime import date

import pytest

from energy_trading.application.errors import ConflictError, ResourceNotFoundError
from energy_trading.application.orchestration import (
    ForecastingPlan,
    ForecastingSuccess,
    ForecastingWorkflowContextPort,
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
)
from energy_trading.application.ports.consumer_load_forecast_model import (
    ConsumerLoadForecastModelRequest,
)
from energy_trading.application.ports.dam_price_forecast_model import (
    DAMPriceForecastModelRequest,
)
from energy_trading.domain.models.forecasting import LoadForecastPoint, PriceForecastPoint
from energy_trading.domain.models.ingestion import AdapterDiagnostic, DiagnosticSeverity
from energy_trading.domain.models.observations import MarketPriceRecord
from energy_trading.infrastructure.orchestration.forecasting_context import (
    InMemoryForecastingWorkflowContext,
)
from tests.unit.domain._factories import amd_price, consumption, utc

_WORKFLOW_ID = "workflow-forecasting-1"
_MISSING_WORKFLOW_ID = "workflow-id-sentinel-MUST-NOT-LEAK"
_OTHER_WORKFLOW_ID = "workflow-forecasting-2"


def _load_request(*, consumer_id: str = "consumer-1") -> ConsumerLoadForecastModelRequest:
    return ConsumerLoadForecastModelRequest(
        forecast_run_id="run-1",
        generated_at=utc(),
        consumer_id=consumer_id,
        history=(consumption(consumer_id=consumer_id),),
        target_timestamps=(utc(hour=16),),
    )


def _dam_request(*, market_id: str = "market-1") -> DAMPriceForecastModelRequest:
    market = MarketPriceRecord.model_validate(
        {
            "market_id": market_id,
            "timestamp": utc(),
            "price": amd_price(),
        }
    )
    return DAMPriceForecastModelRequest(
        market_id=market_id,
        currency="AMD",
        history=(market,),
        target_timestamps=(utc(hour=16),),
    )


def _plan(*, consumer_id: str = "consumer-1") -> ForecastingPlan:
    return ForecastingPlan(
        consumer_load_request=_load_request(consumer_id=consumer_id),
        dam_price_request=_dam_request(),
    )


def _other_plan() -> ForecastingPlan:
    return ForecastingPlan(
        consumer_load_request=_load_request(consumer_id="consumer-2"),
        dam_price_request=_dam_request(market_id="market-2"),
    )


def _load_point(*, value_mw: float = 3.25) -> LoadForecastPoint:
    return LoadForecastPoint.model_validate(
        {
            "forecast_run_id": "run-1",
            "consumer_id": "consumer-1",
            "generated_at": utc(),
            "target_timestamp": utc(hour=16),
            "value_mw": value_mw,
        }
    )


def _price_point(*, amount: str = "45.00") -> PriceForecastPoint:
    return PriceForecastPoint.model_validate(
        {
            "forecast_run_id": "run-1",
            "market_id": "market-1",
            "generated_at": utc(),
            "target_timestamp": utc(hour=16),
            "price": amd_price(amount),
        }
    )


def _success(*, amount: str = "45.00", value_mw: float = 3.25) -> ForecastingSuccess:
    return ForecastingSuccess(
        consumer_load_forecast=(_load_point(value_mw=value_mw),),
        dam_price_forecast=(_price_point(amount=amount),),
    )


def _state(
    *,
    workflow_id: str = _WORKFLOW_ID,
    diagnostics: tuple[AdapterDiagnostic, ...] = (),
    phase: WorkflowPhase = WorkflowPhase.FORECASTING,
    status: WorkflowStatus = WorkflowStatus.RUNNING,
) -> WorkflowState:
    return WorkflowState(
        workflow_id=workflow_id,
        portfolio_id="portfolio-1",
        delivery_date=date(2026, 10, 1),
        correlation_id="corr-1",
        phase=phase,
        status=status,
        diagnostics=diagnostics,
    )


def _as_context_port(
    context: InMemoryForecastingWorkflowContext,
) -> ForecastingWorkflowContextPort:
    """Application-shaped call site: the port type is the only accepted argument."""

    return context


def _context(
    plans: dict[str, ForecastingPlan] | None = None,
) -> InMemoryForecastingWorkflowContext:
    prepared = {_WORKFLOW_ID: _plan()} if plans is None else plans
    return InMemoryForecastingWorkflowContext(prepared)


def test_in_memory_context_does_not_inherit_production_base() -> None:
    assert ForecastingWorkflowContextPort not in InMemoryForecastingWorkflowContext.__mro__
    assert not any(
        base.__name__
        in {
            "ForecastingWorkflowContextPort",
            "Protocol",
            "ABC",
        }
        for base in InMemoryForecastingWorkflowContext.__bases__
    )


def test_in_memory_context_structurally_satisfies_port() -> None:
    context = _context()
    port = _as_context_port(context)
    assert inspect.iscoroutinefunction(port.resolve_plan)
    assert inspect.iscoroutinefunction(port.record_success)
    resolve_parameters = inspect.signature(port.resolve_plan).parameters
    assert tuple(resolve_parameters) == ("state",)
    assert resolve_parameters["state"].kind is inspect.Parameter.KEYWORD_ONLY
    record_parameters = inspect.signature(port.record_success).parameters
    assert tuple(record_parameters) == ("state", "success")
    assert record_parameters["state"].kind is inspect.Parameter.KEYWORD_ONLY
    assert record_parameters["success"].kind is inspect.Parameter.KEYWORD_ONLY


async def test_known_workflow_returns_exact_plan_object() -> None:
    plan = _plan()
    context = InMemoryForecastingWorkflowContext({_WORKFLOW_ID: plan})
    port = _as_context_port(context)
    resolved = await port.resolve_plan(state=_state())
    assert resolved is plan


async def test_unknown_workflow_raises_sanitized_not_found() -> None:
    context = _context()
    port = _as_context_port(context)
    missing_state = _state(workflow_id=_MISSING_WORKFLOW_ID)
    with pytest.raises(ResourceNotFoundError) as captured:
        await port.resolve_plan(state=missing_state)
    assert captured.value.code == "resource_not_found"
    assert captured.value.message == "Forecasting plan was not found."
    assert _MISSING_WORKFLOW_ID not in captured.value.message
    assert _MISSING_WORKFLOW_ID not in str(captured.value)


async def test_caller_plan_mapping_mutation_does_not_affect_context() -> None:
    plan = _plan()
    extra = _other_plan()
    plans = {_WORKFLOW_ID: plan}
    context = InMemoryForecastingWorkflowContext(plans)
    port = _as_context_port(context)
    plans[_OTHER_WORKFLOW_ID] = extra
    del plans[_WORKFLOW_ID]
    resolved = await port.resolve_plan(state=_state())
    assert resolved is plan
    with pytest.raises(ResourceNotFoundError):
        await port.resolve_plan(state=_state(workflow_id=_OTHER_WORKFLOW_ID))


async def test_first_record_success_returns_none() -> None:
    context = _context()
    port = _as_context_port(context)
    result = await port.record_success(state=_state(), success=_success())
    assert result is None


async def test_same_object_retry_is_idempotent() -> None:
    context = _context()
    port = _as_context_port(context)
    original = _success()
    conflicting = _success(amount="99.00")
    first = await port.record_success(state=_state(), success=original)
    retry = await port.record_success(state=_state(), success=original)
    assert first is None
    assert retry is None
    with pytest.raises(ConflictError):
        await port.record_success(state=_state(), success=conflicting)
    assert await port.record_success(state=_state(), success=original) is None


async def test_value_equal_retry_does_not_replace_original() -> None:
    context = _context()
    port = _as_context_port(context)
    original = _success()
    equal_retry = _success()
    conflicting = _success(amount="99.00")
    assert original == equal_retry
    assert original is not equal_retry
    await port.record_success(state=_state(), success=original)
    assert await port.record_success(state=_state(), success=equal_retry) is None
    with pytest.raises(ConflictError):
        await port.record_success(state=_state(), success=conflicting)
    assert await port.record_success(state=_state(), success=original) is None
    with pytest.raises(ConflictError):
        await port.record_success(state=_state(), success=conflicting)


async def test_conflicting_success_raises_and_leaves_original_authoritative() -> None:
    context = _context()
    port = _as_context_port(context)
    original = _success()
    conflicting = _success(amount="12.00")
    await port.record_success(state=_state(), success=original)
    with pytest.raises(ConflictError) as captured:
        await port.record_success(state=_state(), success=conflicting)
    assert captured.value.code == "conflict"
    assert captured.value.message == "Forecasting success conflicts with the recorded result."
    assert _WORKFLOW_ID not in captured.value.message
    assert _WORKFLOW_ID not in str(captured.value)
    assert "12.00" not in captured.value.message
    assert await port.record_success(state=_state(), success=original) is None
    with pytest.raises(ConflictError):
        await port.record_success(state=_state(), success=conflicting)


async def test_independent_workflow_identities_do_not_conflict() -> None:
    first_plan = _plan()
    second_plan = _other_plan()
    context = InMemoryForecastingWorkflowContext(
        {_WORKFLOW_ID: first_plan, _OTHER_WORKFLOW_ID: second_plan}
    )
    port = _as_context_port(context)
    first = _success()
    second = _success(amount="70.00")
    assert await port.record_success(state=_state(), success=first) is None
    assert (
        await port.record_success(state=_state(workflow_id=_OTHER_WORKFLOW_ID), success=second)
        is None
    )
    assert await port.record_success(state=_state(), success=first) is None
    assert (
        await port.record_success(state=_state(workflow_id=_OTHER_WORKFLOW_ID), success=second)
        is None
    )
    with pytest.raises(ConflictError):
        await port.record_success(state=_state(), success=second)
    with pytest.raises(ConflictError):
        await port.record_success(state=_state(workflow_id=_OTHER_WORKFLOW_ID), success=first)


async def test_recording_one_workflow_does_not_overwrite_another() -> None:
    context = InMemoryForecastingWorkflowContext(
        {_WORKFLOW_ID: _plan(), _OTHER_WORKFLOW_ID: _other_plan()}
    )
    port = _as_context_port(context)
    first = _success(amount="45.00")
    second = _success(amount="70.00")
    await port.record_success(state=_state(), success=first)
    await port.record_success(state=_state(workflow_id=_OTHER_WORKFLOW_ID), success=second)
    assert await port.record_success(state=_state(), success=first) is None
    with pytest.raises(ConflictError):
        await port.record_success(state=_state(), success=second)
    assert (
        await port.record_success(state=_state(workflow_id=_OTHER_WORKFLOW_ID), success=second)
        is None
    )
    with pytest.raises(ConflictError):
        await port.record_success(state=_state(workflow_id=_OTHER_WORKFLOW_ID), success=first)


async def test_plan_resolution_and_success_recording_do_not_mutate_workflow_state() -> None:
    plan = _plan()
    context = InMemoryForecastingWorkflowContext({_WORKFLOW_ID: plan})
    port = _as_context_port(context)
    diagnostic = AdapterDiagnostic(
        code="SCHEMA_AMBIGUOUS",
        message="header mapping was ambiguous",
        severity=DiagnosticSeverity.WARNING,
        field_name="timestamp",
    )
    state = _state(diagnostics=(diagnostic,))
    original_workflow_id = state.workflow_id
    original_phase = state.phase
    original_status = state.status
    original_diagnostics = state.diagnostics
    resolved = await port.resolve_plan(state=state)
    recorded = await port.record_success(state=state, success=_success())
    assert resolved is plan
    assert recorded is None
    assert state.workflow_id is original_workflow_id
    assert state.phase is original_phase
    assert state.status is original_status
    assert state.diagnostics is original_diagnostics
    assert state.diagnostics[0] is diagnostic
    assert "forecasting_plan" not in state.__slots__
    assert "forecasting_success" not in state.__slots__
    assert "payload" not in state.__slots__
    assert "artifacts" not in state.__slots__


async def test_diagnostics_and_phase_are_irrelevant_to_workflow_id_key() -> None:
    plan = _plan()
    context = InMemoryForecastingWorkflowContext({_WORKFLOW_ID: plan})
    port = _as_context_port(context)
    diagnostic = AdapterDiagnostic(
        code="SCHEMA_AMBIGUOUS",
        message="header mapping was ambiguous",
        severity=DiagnosticSeverity.WARNING,
        field_name="timestamp",
    )
    keyed_state = _state(
        diagnostics=(diagnostic,),
        phase=WorkflowPhase.INGESTION,
        status=WorkflowStatus.PENDING,
    )
    resolved = await port.resolve_plan(state=keyed_state)
    assert resolved is plan
    original = _success()
    await port.record_success(state=keyed_state, success=original)
    forecasting_running = _state()
    assert await port.record_success(state=forecasting_running, success=original) is None
    with pytest.raises(ConflictError):
        await port.record_success(state=forecasting_running, success=_success(amount="88.00"))


async def test_concurrent_equal_retries_all_succeed() -> None:
    context = _context()
    port = _as_context_port(context)
    successes = [_success() for _ in range(8)]
    assert all(item == successes[0] for item in successes)
    state = _state()

    async with asyncio.TaskGroup() as group:
        for item in successes:
            group.create_task(port.record_success(state=state, success=item))

    conflicting = _success(amount="88.00")
    with pytest.raises(ConflictError):
        await port.record_success(state=state, success=conflicting)
    assert await port.record_success(state=state, success=successes[0]) is None
