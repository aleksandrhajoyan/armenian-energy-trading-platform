"""Process-local in-memory ForecastingSuccessReadPort adapter."""

from __future__ import annotations

import inspect
from datetime import date

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
from energy_trading.infrastructure.orchestration.forecasting_success_reader import (
    InMemoryForecastingSuccessReader,
)
from tests.unit.domain._factories import amd_price, utc

_WORKFLOW_ID = "workflow-forecasting-1"
_OTHER_WORKFLOW_ID = "workflow-forecasting-2"
_MISSING_WORKFLOW_ID = "workflow-id-sentinel-MUST-NOT-LEAK"


def _load_point(*, value_mw: float = 3.25, consumer_id: str = "consumer-1") -> LoadForecastPoint:
    return LoadForecastPoint.model_validate(
        {
            "forecast_run_id": "run-1",
            "consumer_id": consumer_id,
            "generated_at": utc(),
            "target_timestamp": utc(hour=16),
            "value_mw": value_mw,
        }
    )


def _price_point(*, amount: str = "45.00", market_id: str = "market-1") -> PriceForecastPoint:
    return PriceForecastPoint.model_validate(
        {
            "forecast_run_id": "run-1",
            "market_id": market_id,
            "generated_at": utc(),
            "target_timestamp": utc(hour=16),
            "price": amd_price(amount),
        }
    )


def _success() -> ForecastingSuccess:
    return ForecastingSuccess(
        consumer_load_forecast=(_load_point(),),
        dam_price_forecast=(_price_point(),),
    )


def _other_success() -> ForecastingSuccess:
    return ForecastingSuccess(
        consumer_load_forecast=(_load_point(value_mw=7.5, consumer_id="consumer-2"),),
        dam_price_forecast=(_price_point(amount="-12.00", market_id="market-2"),),
    )


def _state() -> WorkflowState:
    return WorkflowState(
        workflow_id=_WORKFLOW_ID,
        portfolio_id="portfolio-1",
        delivery_date=date(2026, 10, 1),
        correlation_id="corr-1",
        phase=WorkflowPhase.RISK_AND_BID,
        status=WorkflowStatus.RUNNING,
    )


def _as_read_port(reader: InMemoryForecastingSuccessReader) -> ForecastingSuccessReadPort:
    """Application-shaped call site: the port type is the only accepted argument."""

    return reader


def test_reader_structurally_satisfies_async_read_port() -> None:
    assert ForecastingSuccessReadPort not in InMemoryForecastingSuccessReader.__mro__
    assert InMemoryForecastingSuccessReader.__bases__ == (object,)
    assert inspect.iscoroutinefunction(InMemoryForecastingSuccessReader.get_success)
    signature = inspect.signature(InMemoryForecastingSuccessReader.get_success)
    assert tuple(signature.parameters) == ("self", "workflow_id")
    parameter = signature.parameters["workflow_id"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is inspect.Parameter.empty


def test_constructor_requires_keyword_only_successes_mapping() -> None:
    signature = inspect.signature(InMemoryForecastingSuccessReader.__init__)
    assert tuple(signature.parameters) == ("self", "successes")
    parameter = signature.parameters["successes"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is inspect.Parameter.empty
    with pytest.raises(TypeError):
        InMemoryForecastingSuccessReader({_WORKFLOW_ID: _success()})  # type: ignore[misc]


async def test_get_success_returns_exact_stored_object_by_identity() -> None:
    success = _success()
    port = _as_read_port(InMemoryForecastingSuccessReader(successes={_WORKFLOW_ID: success}))
    resolved = await port.get_success(workflow_id=_WORKFLOW_ID)
    assert resolved is success


async def test_forecast_tuples_keep_identity_and_canonical_values() -> None:
    success = _success()
    load_forecast = success.consumer_load_forecast
    dam_forecast = success.dam_price_forecast
    reader = InMemoryForecastingSuccessReader(successes={_WORKFLOW_ID: success})
    resolved = await reader.get_success(workflow_id=_WORKFLOW_ID)
    assert resolved.consumer_load_forecast is load_forecast
    assert resolved.dam_price_forecast is dam_forecast
    assert resolved.consumer_load_forecast[0] is load_forecast[0]
    assert resolved.dam_price_forecast[0] is dam_forecast[0]
    assert resolved.consumer_load_forecast == (_load_point(),)
    assert resolved.dam_price_forecast == (_price_point(),)
    assert resolved == _success()


async def test_lookup_key_is_exactly_the_requested_workflow_id() -> None:
    reader = InMemoryForecastingSuccessReader(successes={_WORKFLOW_ID: _success()})
    for near_miss in (
        f" {_WORKFLOW_ID}",
        f"{_WORKFLOW_ID} ",
        _WORKFLOW_ID.upper(),
        "workflow-forecasting",
        f"{_WORKFLOW_ID}-x",
    ):
        with pytest.raises(ResourceNotFoundError):
            await reader.get_success(workflow_id=near_miss)


async def test_multiple_workflow_ids_resolve_to_their_own_results() -> None:
    first = _success()
    second = _other_success()
    reader = InMemoryForecastingSuccessReader(
        successes={_WORKFLOW_ID: first, _OTHER_WORKFLOW_ID: second}
    )
    assert await reader.get_success(workflow_id=_WORKFLOW_ID) is first
    assert await reader.get_success(workflow_id=_OTHER_WORKFLOW_ID) is second


async def test_unknown_workflow_id_fails_closed_without_leaking_data() -> None:
    success = _success()
    reader = InMemoryForecastingSuccessReader(successes={_WORKFLOW_ID: success})
    with pytest.raises(ResourceNotFoundError) as exc_info:
        await reader.get_success(workflow_id=_MISSING_WORKFLOW_ID)
    error = exc_info.value
    assert error.message == "Forecasting success was not found."
    assert error.__cause__ is None
    assert error.__suppress_context__ is True
    rendered = f"{error!s} {error!r} {error.args!r}"
    assert _MISSING_WORKFLOW_ID not in rendered
    assert _WORKFLOW_ID not in rendered
    assert "consumer-1" not in rendered
    assert "market-1" not in rendered
    assert "45" not in rendered
    assert "3.25" not in rendered


async def test_empty_mapping_is_allowed_and_every_lookup_fails_closed() -> None:
    reader = InMemoryForecastingSuccessReader(successes={})
    for workflow_id in (_WORKFLOW_ID, _OTHER_WORKFLOW_ID, _MISSING_WORKFLOW_ID):
        with pytest.raises(ResourceNotFoundError):
            await reader.get_success(workflow_id=workflow_id)


async def test_mutating_input_mapping_after_construction_does_not_change_reader() -> None:
    original = _success()
    replacement = _other_success()
    supplied = {_WORKFLOW_ID: original}
    reader = InMemoryForecastingSuccessReader(successes=supplied)
    supplied[_WORKFLOW_ID] = replacement
    supplied[_OTHER_WORKFLOW_ID] = replacement
    assert await reader.get_success(workflow_id=_WORKFLOW_ID) is original
    with pytest.raises(ResourceNotFoundError):
        await reader.get_success(workflow_id=_OTHER_WORKFLOW_ID)
    supplied.clear()
    assert await reader.get_success(workflow_id=_WORKFLOW_ID) is original


async def test_repeated_reads_return_the_original_object_unchanged() -> None:
    success = _success()
    reader = InMemoryForecastingSuccessReader(successes={_WORKFLOW_ID: success})
    results = [await reader.get_success(workflow_id=_WORKFLOW_ID) for _ in range(3)]
    assert all(result is success for result in results)
    assert success == _success()


async def test_independent_readers_do_not_share_storage() -> None:
    first_success = _success()
    second_success = _other_success()
    first = InMemoryForecastingSuccessReader(successes={_WORKFLOW_ID: first_success})
    second = InMemoryForecastingSuccessReader(successes={_OTHER_WORKFLOW_ID: second_success})
    assert await first.get_success(workflow_id=_WORKFLOW_ID) is first_success
    assert await second.get_success(workflow_id=_OTHER_WORKFLOW_ID) is second_success
    with pytest.raises(ResourceNotFoundError):
        await first.get_success(workflow_id=_OTHER_WORKFLOW_ID)
    with pytest.raises(ResourceNotFoundError):
        await second.get_success(workflow_id=_WORKFLOW_ID)


async def test_read_needs_only_workflow_identity_and_leaves_state_unchanged() -> None:
    state = _state()
    success = _success()
    reader = InMemoryForecastingSuccessReader(successes={state.workflow_id: success})
    original_phase = state.phase
    original_status = state.status
    original_diagnostics = state.diagnostics
    resolved = await reader.get_success(workflow_id=state.workflow_id)
    assert resolved is success
    assert state.workflow_id == _WORKFLOW_ID
    assert state.phase is original_phase
    assert state.status is original_status
    assert state.diagnostics is original_diagnostics
    assert "forecasting_success" not in state.__slots__
