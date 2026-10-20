"""Application-owned forecasting-success read Protocol.

These are contract-level tests against a test-only structural fake. They do
not prove production retrieval behavior: no concrete reader exists yet.
"""

from __future__ import annotations

import inspect
from collections.abc import Mapping
from datetime import date
from typing import Protocol, get_type_hints

import pytest

from energy_trading.application.errors import ResourceNotFoundError
from energy_trading.application.orchestration import (
    ForecastingSuccess,
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
)
from energy_trading.application.orchestration.forecasting_success_read import (
    ForecastingSuccessReadPort,
)
from energy_trading.domain.models.forecasting import LoadForecastPoint, PriceForecastPoint
from tests.unit.domain._factories import amd_price, utc

_MSG_SUCCESS_NOT_FOUND = "Forecasting success was not found."


class _StructuralForecastingSuccessReaderFake:
    """Test-only fake that structurally satisfies the read Protocol.

    Not a production reader. Does not inherit a production base class.
    Missing workflow identities fail closed instead of fabricating a result.
    """

    def __init__(self, successes: Mapping[str, ForecastingSuccess]) -> None:
        self._successes = dict(successes)
        self.received_workflow_ids: list[str] = []

    async def get_success(self, *, workflow_id: str) -> ForecastingSuccess:
        self.received_workflow_ids.append(workflow_id)
        try:
            return self._successes[workflow_id]
        except KeyError:
            raise ResourceNotFoundError(_MSG_SUCCESS_NOT_FOUND) from None


def _as_read_port(
    fake: _StructuralForecastingSuccessReaderFake,
) -> ForecastingSuccessReadPort:
    """Application-shaped call site: the port type is the only accepted argument."""

    return fake


def _load_point(value_mw: float = 3.25) -> LoadForecastPoint:
    return LoadForecastPoint.model_validate(
        {
            "forecast_run_id": "run-1",
            "consumer_id": "consumer-1",
            "generated_at": utc(),
            "target_timestamp": utc(hour=16),
            "value_mw": value_mw,
        }
    )


def _price_point(amount: str = "45.00") -> PriceForecastPoint:
    return PriceForecastPoint.model_validate(
        {
            "forecast_run_id": "run-1",
            "market_id": "market-1",
            "generated_at": utc(),
            "target_timestamp": utc(hour=16),
            "price": amd_price(amount),
        }
    )


def _success(value_mw: float = 3.25, amount: str = "45.00") -> ForecastingSuccess:
    return ForecastingSuccess(
        consumer_load_forecast=(_load_point(value_mw),),
        dam_price_forecast=(_price_point(amount),),
    )


def _state() -> WorkflowState:
    return WorkflowState(
        workflow_id="workflow-forecasting-1",
        portfolio_id="portfolio-1",
        delivery_date=date(2026, 10, 1),
        correlation_id="corr-1",
        phase=WorkflowPhase.RISK_AND_BID,
        status=WorkflowStatus.RUNNING,
    )


def test_read_port_is_nongeneric_typing_protocol() -> None:
    assert issubclass(ForecastingSuccessReadPort, Protocol)
    assert any(base.__name__ == "Protocol" for base in ForecastingSuccessReadPort.__bases__)
    assert ForecastingSuccessReadPort.__parameters__ == ()
    assert ForecastingSuccessReadPort.__type_params__ == ()


def test_reader_fake_does_not_inherit_production_base() -> None:
    assert ForecastingSuccessReadPort not in _StructuralForecastingSuccessReaderFake.__mro__
    assert not any(
        base.__name__ in {"ForecastingSuccessReadPort", "Protocol"}
        for base in _StructuralForecastingSuccessReaderFake.__bases__
    )


def test_read_port_exposes_exactly_one_async_operation() -> None:
    defined_methods = {
        name
        for name, value in vars(ForecastingSuccessReadPort).items()
        if callable(value) and not name.startswith("_")
    }
    assert defined_methods == {"get_success"}
    assert inspect.iscoroutinefunction(ForecastingSuccessReadPort.get_success)


def test_get_success_is_keyword_only_workflow_id_with_no_defaults() -> None:
    signature = inspect.signature(ForecastingSuccessReadPort.get_success)
    assert tuple(signature.parameters) == ("self", "workflow_id")
    parameter = signature.parameters["workflow_id"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is inspect.Parameter.empty
    hints = get_type_hints(ForecastingSuccessReadPort.get_success)
    assert hints["workflow_id"] is str
    assert hints["return"] is ForecastingSuccess


async def test_reader_fake_returns_exact_success_for_explicit_workflow_id() -> None:
    success = _success()
    fake = _StructuralForecastingSuccessReaderFake({"workflow-forecasting-1": success})
    port = _as_read_port(fake)
    assert inspect.iscoroutinefunction(port.get_success)
    resolved = await port.get_success(workflow_id="workflow-forecasting-1")
    assert resolved is success
    assert fake.received_workflow_ids == ["workflow-forecasting-1"]


async def test_reader_fake_preserves_forecast_tuples_without_reconstruction() -> None:
    success = _success()
    load_forecast = success.consumer_load_forecast
    dam_forecast = success.dam_price_forecast
    port = _as_read_port(_StructuralForecastingSuccessReaderFake({"workflow-1": success}))
    resolved = await port.get_success(workflow_id="workflow-1")
    assert resolved.consumer_load_forecast is load_forecast
    assert resolved.dam_price_forecast is dam_forecast
    assert resolved.consumer_load_forecast[0] is load_forecast[0]
    assert resolved.dam_price_forecast[0] is dam_forecast[0]


async def test_reader_fake_keeps_independent_workflow_identities_distinct() -> None:
    first = _success(value_mw=3.25, amount="45.00")
    second = _success(value_mw=7.5, amount="-12.00")
    fake = _StructuralForecastingSuccessReaderFake({"workflow-a": first, "workflow-b": second})
    port = _as_read_port(fake)
    resolved_a = await port.get_success(workflow_id="workflow-a")
    resolved_b = await port.get_success(workflow_id="workflow-b")
    assert resolved_a is first
    assert resolved_b is second
    assert resolved_a is not resolved_b
    assert fake.received_workflow_ids == ["workflow-a", "workflow-b"]


async def test_read_needs_only_workflow_identity_and_leaves_workflow_state_unchanged() -> None:
    state = _state()
    success = _success()
    port = _as_read_port(_StructuralForecastingSuccessReaderFake({state.workflow_id: success}))
    original_workflow_id = state.workflow_id
    original_phase = state.phase
    original_status = state.status
    original_diagnostics = state.diagnostics
    resolved = await port.get_success(workflow_id=state.workflow_id)
    assert resolved is success
    assert state.workflow_id is original_workflow_id
    assert state.phase is original_phase
    assert state.status is original_status
    assert state.diagnostics is original_diagnostics
    assert "forecasting_success" not in state.__slots__
    assert "consumer_load_forecast" not in state.__slots__
    assert "dam_price_forecast" not in state.__slots__


async def test_reader_fake_fails_closed_on_missing_success_without_fabrication() -> None:
    fake = _StructuralForecastingSuccessReaderFake({"workflow-a": _success()})
    port = _as_read_port(fake)
    with pytest.raises(ResourceNotFoundError) as exc_info:
        await port.get_success(workflow_id="workflow-missing")
    assert exc_info.value.message == _MSG_SUCCESS_NOT_FOUND
    assert exc_info.value.__cause__ is None
    assert fake.received_workflow_ids == ["workflow-missing"]
