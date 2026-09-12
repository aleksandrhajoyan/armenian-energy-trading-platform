"""Application-owned forecasting workflow-context Protocol."""

from __future__ import annotations

import inspect
from datetime import date
from typing import Protocol, get_type_hints

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
from energy_trading.domain.models.observations import MarketPriceRecord
from tests.unit.domain._factories import amd_price, consumption, utc


class _StructuralForecastingWorkflowContextFake:
    """Test-only fake that structurally satisfies the context Protocol.

    Not a production context implementation. Does not inherit a production
    base class.
    """

    def __init__(
        self,
        plan: ForecastingPlan,
        recorded: list[tuple[WorkflowState, ForecastingSuccess]] | None = None,
    ) -> None:
        self._plan = plan
        self.received_resolve_state: WorkflowState | None = None
        self.received_record_state: WorkflowState | None = None
        self.received_success: ForecastingSuccess | None = None
        self.recorded = recorded if recorded is not None else []

    async def resolve_plan(self, *, state: WorkflowState) -> ForecastingPlan:
        self.received_resolve_state = state
        return self._plan

    async def record_success(
        self,
        *,
        state: WorkflowState,
        success: ForecastingSuccess,
    ) -> None:
        self.received_record_state = state
        self.received_success = success
        self.recorded.append((state, success))


def _load_request() -> ConsumerLoadForecastModelRequest:
    return ConsumerLoadForecastModelRequest(
        consumer_id="consumer-1",
        history=(consumption(),),
        target_timestamps=(utc(hour=16),),
    )


def _dam_request() -> DAMPriceForecastModelRequest:
    market = MarketPriceRecord.model_validate(
        {
            "market_id": "market-1",
            "timestamp": utc(),
            "price": amd_price(),
        }
    )
    return DAMPriceForecastModelRequest(
        market_id="market-1",
        currency="AMD",
        history=(market,),
        target_timestamps=(utc(hour=16),),
    )


def _plan() -> ForecastingPlan:
    return ForecastingPlan(
        consumer_load_request=_load_request(),
        dam_price_request=_dam_request(),
    )


def _load_point() -> LoadForecastPoint:
    return LoadForecastPoint.model_validate(
        {
            "forecast_run_id": "run-1",
            "consumer_id": "consumer-1",
            "generated_at": utc(),
            "target_timestamp": utc(hour=16),
            "value_mw": 3.25,
        }
    )


def _price_point() -> PriceForecastPoint:
    return PriceForecastPoint.model_validate(
        {
            "forecast_run_id": "run-1",
            "market_id": "market-1",
            "generated_at": utc(),
            "target_timestamp": utc(hour=16),
            "price": amd_price("45.00"),
        }
    )


def _success() -> ForecastingSuccess:
    return ForecastingSuccess(
        consumer_load_forecast=(_load_point(),),
        dam_price_forecast=(_price_point(),),
    )


def _state() -> WorkflowState:
    return WorkflowState(
        workflow_id="workflow-forecasting-1",
        portfolio_id="portfolio-1",
        delivery_date=date(2026, 10, 1),
        correlation_id="corr-1",
        phase=WorkflowPhase.FORECASTING,
        status=WorkflowStatus.RUNNING,
    )


def _as_context_port(
    fake: _StructuralForecastingWorkflowContextFake,
) -> ForecastingWorkflowContextPort:
    """Application-shaped call site: the port type is the only accepted argument."""

    return fake


def test_forecasting_workflow_context_port_exists_and_is_a_protocol() -> None:
    assert issubclass(ForecastingWorkflowContextPort, Protocol)


def test_context_port_is_typing_protocol() -> None:
    bases = ForecastingWorkflowContextPort.__bases__
    assert any(base.__name__ == "Protocol" for base in bases)
    assert ForecastingWorkflowContextPort.__type_params__ == ()
    assert ForecastingWorkflowContextPort.__parameters__ == ()


def test_context_fake_does_not_inherit_production_base() -> None:
    assert ForecastingWorkflowContextPort not in _StructuralForecastingWorkflowContextFake.__mro__
    assert not any(
        base.__name__ in {"ForecastingWorkflowContextPort", "Protocol"}
        for base in _StructuralForecastingWorkflowContextFake.__bases__
    )


def test_context_port_exposes_exactly_two_async_operations() -> None:
    defined_methods = {
        name
        for name, value in vars(ForecastingWorkflowContextPort).items()
        if callable(value) and not name.startswith("_")
    }
    assert defined_methods == {"resolve_plan", "record_success"}
    assert inspect.iscoroutinefunction(ForecastingWorkflowContextPort.resolve_plan)
    assert inspect.iscoroutinefunction(ForecastingWorkflowContextPort.record_success)
    forbidden = {
        "execute",
        "run",
        "forecast",
        "get_plan",
        "load_plan",
        "save_success",
        "store_success",
        "resolve_request",
        "record_result",
    }
    assert forbidden.isdisjoint(defined_methods)


def test_resolve_plan_is_keyword_only_state_with_no_defaults() -> None:
    signature = inspect.signature(ForecastingWorkflowContextPort.resolve_plan)
    assert tuple(signature.parameters) == ("self", "state")
    state_parameter = signature.parameters["state"]
    assert state_parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert state_parameter.default is inspect.Parameter.empty
    assert state_parameter.annotation is WorkflowState
    assert signature.return_annotation is ForecastingPlan
    assert not any(
        parameter.kind is inspect.Parameter.VAR_POSITIONAL
        for parameter in signature.parameters.values()
    )
    assert not any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )


def test_record_success_is_keyword_only_state_and_success_with_no_defaults() -> None:
    signature = inspect.signature(ForecastingWorkflowContextPort.record_success)
    assert tuple(signature.parameters) == ("self", "state", "success")
    state_parameter = signature.parameters["state"]
    success_parameter = signature.parameters["success"]
    assert state_parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert success_parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert state_parameter.default is inspect.Parameter.empty
    assert success_parameter.default is inspect.Parameter.empty
    assert state_parameter.annotation is WorkflowState
    assert success_parameter.annotation is ForecastingSuccess
    assert signature.return_annotation is None
    assert not any(
        parameter.kind is inspect.Parameter.VAR_POSITIONAL
        for parameter in signature.parameters.values()
    )
    assert not any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )


def test_resolved_annotations_reuse_published_types() -> None:
    resolve_hints = get_type_hints(ForecastingWorkflowContextPort.resolve_plan)
    record_hints = get_type_hints(ForecastingWorkflowContextPort.record_success)
    assert resolve_hints["state"] is WorkflowState
    assert resolve_hints["return"] is ForecastingPlan
    assert record_hints["state"] is WorkflowState
    assert record_hints["success"] is ForecastingSuccess
    assert record_hints["return"] is type(None)


def test_context_port_has_no_generic_type_parameters() -> None:
    assert ForecastingWorkflowContextPort.__parameters__ == ()
    assert ForecastingWorkflowContextPort.__type_params__ == ()


async def test_context_fake_satisfies_port_preserving_plan_and_state_identity() -> None:
    plan = _plan()
    fake = _StructuralForecastingWorkflowContextFake(plan)
    port = _as_context_port(fake)
    state = _state()
    resolved = await port.resolve_plan(state=state)
    assert inspect.iscoroutinefunction(port.resolve_plan)
    assert resolved is plan
    assert fake.received_resolve_state is state
    assert isinstance(resolved, ForecastingPlan)


async def test_record_success_preserves_state_and_success_identity() -> None:
    plan = _plan()
    success = _success()
    fake = _StructuralForecastingWorkflowContextFake(plan)
    port = _as_context_port(fake)
    state = _state()
    recorded = await port.record_success(state=state, success=success)
    assert recorded is None
    assert fake.received_record_state is state
    assert fake.received_success is success
    assert fake.recorded == [(state, success)]
    assert fake.recorded[0][0] is state
    assert fake.recorded[0][1] is success


async def test_context_does_not_mutate_workflow_state_or_use_generic_payloads() -> None:
    plan = _plan()
    success = _success()
    fake = _StructuralForecastingWorkflowContextFake(plan)
    port = _as_context_port(fake)
    state = _state()
    original_workflow_id = state.workflow_id
    original_phase = state.phase
    original_status = state.status
    original_diagnostics = state.diagnostics
    resolved = await port.resolve_plan(state=state)
    recorded = await port.record_success(state=state, success=success)
    assert resolved is plan
    assert recorded is None
    assert state.workflow_id is original_workflow_id
    assert state.phase is original_phase
    assert state.status is original_status
    assert state.diagnostics is original_diagnostics
    assert "forecasting_plan" not in state.__slots__
    assert "forecasting_success" not in state.__slots__
    assert "consumer_load_request" not in state.__slots__
    assert "dam_price_request" not in state.__slots__
    assert "payload" not in state.__slots__
    assert "data" not in state.__slots__
    assert "context" not in state.__slots__
    assert "artifacts" not in state.__slots__
    assert fake.received_resolve_state is state
    assert fake.received_record_state is state
    assert fake.received_success is success
