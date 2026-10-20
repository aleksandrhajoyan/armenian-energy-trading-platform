"""Offline Phase 3 forecasting graph read-after-write integration verification.

These integration-style tests compose the published Chunk 190 stack builder
and Chunk 191 failure-runtime builder, hand the results to the real
``build_workflow_graph``, and invoke the compiled graph with one real
``InMemoryForecastingReadAfterWriteContext`` injected as the forecasting
workflow-context port. The same wrapper instance is then read through the
``ForecastingSuccessReadPort`` shape. Only the two external model ports and
the unrelated Regulatory and Phase 2 graph collaborators are test doubles.
Selector, attempt source, and policy objects chosen here are test fixtures,
not production defaults.
"""

from __future__ import annotations

from dataclasses import fields
from datetime import date

import pytest
from langgraph.graph.state import CompiledStateGraph

from energy_trading.api.composition.forecasting_failure_runtime import (
    build_forecasting_failure_runtime_handler,
)
from energy_trading.api.composition.forecasting_stack import (
    build_forecasting_workflow_step_from_model_ports,
)
from energy_trading.application.agents import AgentName
from energy_trading.application.errors import (
    ConflictError,
    InvalidRequestError,
    ResourceNotFoundError,
)
from energy_trading.application.orchestration import (
    FailureAction,
    FailurePolicyContext,
    ForecastingPlan,
    ForecastingSuccess,
    ForecastingWorkflowContextPort,
    StrictSingleForecastingFailureSelector,
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
    build_workflow_graph,
)
from energy_trading.application.orchestration.forecasting_initial_attempt_number_source import (
    InitialForecastingAttemptNumberSource,
)
from energy_trading.application.orchestration.forecasting_initial_failure_policy import (
    InitialForecastingFailurePolicy,
)
from energy_trading.application.orchestration.forecasting_success_read import (
    ForecastingSuccessReadPort,
)
from energy_trading.application.ports.consumer_load_forecast_model import (
    ConsumerLoadForecastModelRequest,
)
from energy_trading.application.ports.dam_price_forecast_model import (
    DAMPriceForecastModelRequest,
)
from energy_trading.domain.models.forecasting import LoadForecastPoint, PriceForecastPoint
from energy_trading.domain.models.observations import MarketPriceRecord
from energy_trading.infrastructure.orchestration.forecasting_context import (
    InMemoryForecastingWorkflowContext,
)
from energy_trading.infrastructure.orchestration.forecasting_read_after_write_context import (
    InMemoryForecastingReadAfterWriteContext,
)
from tests.unit.domain._factories import amd_price, consumption, diagnostic, utc

_WORKFLOW_ID = "wf-phase3-raw-a"
_OTHER_WORKFLOW_ID = "wf-phase3-raw-b"
_SENTINEL_TEXT = "sentinel-phase3-raw-text-not-for-state"
_MSG_SUCCESS_NOT_FOUND = "Forecasting success was not found."
_MSG_PLAN_NOT_FOUND = "Forecasting plan was not found."
_MSG_SUCCESS_CONFLICT = "Forecasting success conflicts with the recorded result."
_INVALID_ENTRY_ROUTE_MESSAGE = (
    "Workflow entry routing requires contract running, ingestion running, "
    "or forecasting running status."
)
_STATE_FIELDS = frozenset(field.name for field in fields(WorkflowState))


class _ConsumerLoadModel:
    """Test-only Consumer Load port fake returning one scripted output per call."""

    def __init__(
        self,
        outputs: tuple[tuple[LoadForecastPoint, ...], ...] = (),
        error: Exception | None = None,
    ) -> None:
        self._outputs = outputs
        self._error = error
        self.calls: list[ConsumerLoadForecastModelRequest] = []

    async def forecast(
        self,
        *,
        request: ConsumerLoadForecastModelRequest,
    ) -> tuple[LoadForecastPoint, ...]:
        self.calls.append(request)
        if self._error is not None:
            raise self._error
        return self._outputs[len(self.calls) - 1]


class _DAMPriceModel:
    """Test-only DAM Price port fake returning one scripted output per call."""

    def __init__(
        self,
        outputs: tuple[tuple[PriceForecastPoint, ...], ...] = (),
        error: Exception | None = None,
    ) -> None:
        self._outputs = outputs
        self._error = error
        self.calls: list[DAMPriceForecastModelRequest] = []

    async def forecast(
        self,
        *,
        request: DAMPriceForecastModelRequest,
    ) -> tuple[PriceForecastPoint, ...]:
        self.calls.append(request)
        if self._error is not None:
            raise self._error
        return self._outputs[len(self.calls) - 1]


class _RecordingAttemptNumberSource:
    """Test-only forwarding wrapper over the initial attempt-number source."""

    def __init__(self) -> None:
        self._inner = InitialForecastingAttemptNumberSource()
        self.workflow_ids: list[str] = []

    async def get_attempt_number(self, workflow_id: str) -> int:
        self.workflow_ids.append(workflow_id)
        return await self._inner.get_attempt_number(workflow_id)


class _RecordingFailurePolicy:
    """Test-only forwarding wrapper over the initial terminal-fail policy."""

    def __init__(self) -> None:
        self._inner = InitialForecastingFailurePolicy()
        self.contexts: list[FailurePolicyContext] = []
        self.actions: list[FailureAction] = []

    async def decide(self, context: FailurePolicyContext) -> FailureAction:
        self.contexts.append(context)
        action = await self._inner.decide(context)
        self.actions.append(action)
        return action


class _UnusedRegulatoryNode:
    """Test-only Regulatory node that must not run on the Phase 3 path."""

    def __init__(self) -> None:
        self.calls = 0

    async def run(self, state: WorkflowState) -> WorkflowState:
        self.calls += 1
        msg = "Regulatory node must not run on the Phase 3 graph path"
        raise AssertionError(msg)


class _UnusedParallelIngestionStep:
    """Test-only Phase 2 step that must not run on the Phase 3 path."""

    def __init__(self) -> None:
        self.calls = 0

    async def run(self, state: WorkflowState) -> WorkflowState:
        self.calls += 1
        msg = "Parallel-ingestion step must not run on the Phase 3 graph path"
        raise AssertionError(msg)


class _UnusedParallelIngestionFailureHandler:
    """Test-only Phase 2 failure handler that must not run on the Phase 3 path."""

    def __init__(self) -> None:
        self.calls = 0

    async def handle(
        self,
        *,
        state: WorkflowState,
        failure_group: BaseExceptionGroup,
    ) -> WorkflowState:
        self.calls += 1
        msg = "Parallel-ingestion failure handler must not run on the Phase 3 graph path"
        raise AssertionError(msg)


class _Slice:
    """Test-only bundle of one composed Phase 3 graph over one read-after-write wrapper."""

    def __init__(
        self,
        *,
        plans: dict[str, ForecastingPlan],
        consumer_model: _ConsumerLoadModel,
        dam_model: _DAMPriceModel,
    ) -> None:
        wrapper = InMemoryForecastingReadAfterWriteContext(
            context=InMemoryForecastingWorkflowContext(plans),
        )
        self.context_port: ForecastingWorkflowContextPort = wrapper
        self.read_port: ForecastingSuccessReadPort = wrapper
        self.consumer_model = consumer_model
        self.dam_model = dam_model
        self.attempt_source = _RecordingAttemptNumberSource()
        self.policy = _RecordingFailurePolicy()
        self.regulatory = _UnusedRegulatoryNode()
        self.parallel_ingestion_step = _UnusedParallelIngestionStep()
        self.parallel_ingestion_handler = _UnusedParallelIngestionFailureHandler()
        forecasting_step = build_forecasting_workflow_step_from_model_ports(
            consumer_load_model=consumer_model,
            dam_price_model=dam_model,
            context=self.context_port,
        )
        failure_handler = build_forecasting_failure_runtime_handler(
            selector=StrictSingleForecastingFailureSelector(),
            attempt_number_source=self.attempt_source,
            policy=self.policy,
        )
        self.graph: CompiledStateGraph[WorkflowState, None, WorkflowState, WorkflowState] = (
            build_workflow_graph(
                regulatory_intelligence_node=self.regulatory,  # type: ignore[arg-type]
                parallel_ingestion_step=self.parallel_ingestion_step,  # type: ignore[arg-type]
                parallel_ingestion_failure_runtime_handler=self.parallel_ingestion_handler,  # type: ignore[arg-type]
                forecasting_step=forecasting_step,
                forecasting_failure_runtime_handler=failure_handler,
            )
        )

    def assert_unrelated_collaborators_unused(self) -> None:
        assert self.regulatory.calls == 0
        assert self.parallel_ingestion_step.calls == 0
        assert self.parallel_ingestion_handler.calls == 0

    def assert_no_failure_processing(self) -> None:
        assert self.attempt_source.workflow_ids == []
        assert self.policy.contexts == []

    async def assert_success_not_found(self, workflow_id: str) -> None:
        with pytest.raises(ResourceNotFoundError) as captured:
            await self.read_port.get_success(workflow_id=workflow_id)
        assert captured.value.code == "resource_not_found"
        assert captured.value.message == _MSG_SUCCESS_NOT_FOUND
        assert _SENTINEL_TEXT not in str(captured.value)


def _load_request(forecast_run_id: str = "load-run-1") -> ConsumerLoadForecastModelRequest:
    return ConsumerLoadForecastModelRequest(
        forecast_run_id=forecast_run_id,
        generated_at=utc(hour=9),
        consumer_id="consumer-1",
        history=(consumption(),),
        target_timestamps=(utc(hour=16), utc(hour=17)),
    )


def _dam_request(forecast_run_id: str = "price-run-1") -> DAMPriceForecastModelRequest:
    market = MarketPriceRecord.model_validate(
        {
            "market_id": "market-1",
            "timestamp": utc(),
            "price": amd_price(),
        }
    )
    return DAMPriceForecastModelRequest(
        forecast_run_id=forecast_run_id,
        generated_at=utc(hour=9),
        market_id="market-1",
        currency="AMD",
        history=(market,),
        target_timestamps=(utc(hour=16), utc(hour=17)),
    )


def _plan(load_run_id: str = "load-run-1", price_run_id: str = "price-run-1") -> ForecastingPlan:
    return ForecastingPlan(
        consumer_load_request=_load_request(load_run_id),
        dam_price_request=_dam_request(price_run_id),
    )


def _load_points(
    forecast_run_id: str = "load-run-1",
    values_mw: tuple[float, float] = (3.25, 3.5),
) -> tuple[LoadForecastPoint, ...]:
    return tuple(
        LoadForecastPoint.model_validate(
            {
                "forecast_run_id": forecast_run_id,
                "consumer_id": "consumer-1",
                "generated_at": utc(hour=9),
                "target_timestamp": utc(hour=hour),
                "value_mw": value_mw,
            }
        )
        for hour, value_mw in zip((16, 17), values_mw, strict=True)
    )


def _price_points(forecast_run_id: str = "price-run-1") -> tuple[PriceForecastPoint, ...]:
    return tuple(
        PriceForecastPoint.model_validate(
            {
                "forecast_run_id": forecast_run_id,
                "market_id": "market-1",
                "generated_at": utc(hour=9),
                "target_timestamp": utc(hour=hour),
                "price": amd_price(amount),
            }
        )
        for hour, amount in ((16, "45.00"), (17, "-3.10"))
    )


def _state(**overrides: object) -> WorkflowState:
    values: dict[str, object] = {
        "workflow_id": _WORKFLOW_ID,
        "portfolio_id": "portfolio-phase3",
        "delivery_date": date(2026, 10, 2),
        "correlation_id": "corr-phase3-raw",
        "phase": WorkflowPhase.FORECASTING,
        "status": WorkflowStatus.RUNNING,
        "diagnostics": (diagnostic(),),
    }
    values.update(overrides)
    return WorkflowState(**values)  # type: ignore[arg-type]


def _reconstruct(payload: dict[str, object]) -> WorkflowState:
    assert set(payload) == _STATE_FIELDS
    return WorkflowState(**payload)  # type: ignore[arg-type]


def _assert_metadata_preserved(result: WorkflowState, original: WorkflowState) -> None:
    assert result.workflow_id == original.workflow_id
    assert result.portfolio_id == original.portfolio_id
    assert result.delivery_date == original.delivery_date
    assert result.correlation_id == original.correlation_id
    assert result.diagnostics == original.diagnostics


async def test_graph_success_is_readable_through_the_same_wrapper() -> None:
    plan = _plan()
    load_points = _load_points()
    price_points = _price_points()
    built = _Slice(
        plans={_WORKFLOW_ID: plan},
        consumer_model=_ConsumerLoadModel(outputs=(load_points,)),
        dam_model=_DAMPriceModel(outputs=(price_points,)),
    )
    original = _state()
    await built.assert_success_not_found(_WORKFLOW_ID)

    payload = await built.graph.ainvoke(original)

    reconstructed = _reconstruct(payload)
    assert built.consumer_model.calls == [plan.consumer_load_request]
    assert built.consumer_model.calls[0] is plan.consumer_load_request
    assert built.dam_model.calls == [plan.dam_price_request]
    assert built.dam_model.calls[0] is plan.dam_price_request
    assert reconstructed.phase is WorkflowPhase.RISK_AND_BID
    assert reconstructed.status is WorkflowStatus.RUNNING
    _assert_metadata_preserved(reconstructed, original)
    assert original.phase is WorkflowPhase.FORECASTING
    assert original.status is WorkflowStatus.RUNNING
    assert load_points not in payload.values()
    assert price_points not in payload.values()

    success = await built.read_port.get_success(workflow_id=_WORKFLOW_ID)

    assert isinstance(success, ForecastingSuccess)
    assert success.consumer_load_forecast is load_points
    assert success.dam_price_forecast is price_points
    assert all(
        read is produced
        for read, produced in zip(success.consumer_load_forecast, load_points, strict=True)
    )
    assert all(
        read is produced
        for read, produced in zip(success.dam_price_forecast, price_points, strict=True)
    )
    assert success.dam_price_forecast[1].price.currency == "AMD"
    assert await built.read_port.get_success(workflow_id=_WORKFLOW_ID) is success
    built.assert_no_failure_processing()
    built.assert_unrelated_collaborators_unused()


async def test_reads_are_isolated_by_exact_workflow_identity() -> None:
    first_plan = _plan()
    second_plan = _plan(load_run_id="load-run-2", price_run_id="price-run-2")
    first_load = _load_points()
    second_load = _load_points(forecast_run_id="load-run-2", values_mw=(8.0, 8.5))
    first_price = _price_points()
    second_price = _price_points(forecast_run_id="price-run-2")
    built = _Slice(
        plans={_WORKFLOW_ID: first_plan, _OTHER_WORKFLOW_ID: second_plan},
        consumer_model=_ConsumerLoadModel(outputs=(first_load, second_load)),
        dam_model=_DAMPriceModel(outputs=(first_price, second_price)),
    )

    await built.graph.ainvoke(_state(workflow_id=_WORKFLOW_ID))

    first_success = await built.read_port.get_success(workflow_id=_WORKFLOW_ID)
    assert first_success.consumer_load_forecast is first_load
    await built.assert_success_not_found(_OTHER_WORKFLOW_ID)
    for near_miss in ("", "wf-phase3-raw", "wf-phase3-raw-a ", "WF-PHASE3-RAW-A", "wf-phase3"):
        await built.assert_success_not_found(near_miss)

    second_result = _reconstruct(await built.graph.ainvoke(_state(workflow_id=_OTHER_WORKFLOW_ID)))

    assert second_result.workflow_id == _OTHER_WORKFLOW_ID
    assert second_result.phase is WorkflowPhase.RISK_AND_BID
    assert built.consumer_model.calls == [
        first_plan.consumer_load_request,
        second_plan.consumer_load_request,
    ]
    assert built.dam_model.calls == [first_plan.dam_price_request, second_plan.dam_price_request]
    second_success = await built.read_port.get_success(workflow_id=_OTHER_WORKFLOW_ID)
    assert second_success.consumer_load_forecast is second_load
    assert second_success.dam_price_forecast is second_price
    assert await built.read_port.get_success(workflow_id=_WORKFLOW_ID) is first_success
    assert second_success is not first_success
    assert second_success != first_success
    built.assert_no_failure_processing()
    built.assert_unrelated_collaborators_unused()


@pytest.mark.parametrize(
    ("failing_branch", "expected_agent"),
    [
        ("consumer_load", AgentName.CONSUMER_LOAD_FORECAST),
        ("dam_price", AgentName.DAM_PRICE_FORECAST),
    ],
)
async def test_branch_failure_ends_failed_without_publishing_success(
    failing_branch: str,
    expected_agent: AgentName,
) -> None:
    plan = _plan()
    error = RuntimeError(_SENTINEL_TEXT)
    consumer_model = (
        _ConsumerLoadModel(error=error)
        if failing_branch == "consumer_load"
        else _ConsumerLoadModel(outputs=(_load_points(),))
    )
    dam_model = (
        _DAMPriceModel(error=error)
        if failing_branch == "dam_price"
        else _DAMPriceModel(outputs=(_price_points(),))
    )
    built = _Slice(
        plans={_WORKFLOW_ID: plan},
        consumer_model=consumer_model,
        dam_model=dam_model,
    )
    original = _state()

    reconstructed = _reconstruct(await built.graph.ainvoke(original))

    failing_calls: list[object] = list(
        consumer_model.calls if failing_branch == "consumer_load" else dam_model.calls
    )
    expected_request: object = (
        plan.consumer_load_request if failing_branch == "consumer_load" else plan.dam_price_request
    )
    assert len(failing_calls) == 1
    assert failing_calls[0] is expected_request
    assert built.attempt_source.workflow_ids == [_WORKFLOW_ID]
    assert built.policy.contexts == [
        FailurePolicyContext(
            phase=WorkflowPhase.FORECASTING,
            error_code="forecasting_unexpected_failure",
            attempt_number=1,
            agent_name=expected_agent,
        )
    ]
    assert built.policy.actions == [FailureAction.FAIL]
    assert reconstructed.phase is WorkflowPhase.FORECASTING
    assert reconstructed.status is WorkflowStatus.FAILED
    _assert_metadata_preserved(reconstructed, original)
    assert _SENTINEL_TEXT not in repr(reconstructed)
    assert original.status is WorkflowStatus.RUNNING
    await built.assert_success_not_found(_WORKFLOW_ID)
    built.assert_unrelated_collaborators_unused()


async def test_missing_plan_propagates_without_execution_or_publication() -> None:
    built = _Slice(
        plans={_OTHER_WORKFLOW_ID: _plan()},
        consumer_model=_ConsumerLoadModel(outputs=(_load_points(),)),
        dam_model=_DAMPriceModel(outputs=(_price_points(),)),
    )

    with pytest.raises(ResourceNotFoundError) as captured:
        await built.graph.ainvoke(_state())

    assert captured.value.code == "resource_not_found"
    assert captured.value.message == _MSG_PLAN_NOT_FOUND
    assert built.consumer_model.calls == []
    assert built.dam_model.calls == []
    await built.assert_success_not_found(_WORKFLOW_ID)
    await built.assert_success_not_found(_OTHER_WORKFLOW_ID)
    built.assert_no_failure_processing()
    built.assert_unrelated_collaborators_unused()


async def test_equivalent_reexecution_keeps_first_published_success() -> None:
    first_load = _load_points()
    first_price = _price_points()
    equal_load = _load_points()
    equal_price = _price_points()
    assert equal_load == first_load
    assert equal_load is not first_load
    built = _Slice(
        plans={_WORKFLOW_ID: _plan()},
        consumer_model=_ConsumerLoadModel(outputs=(first_load, equal_load)),
        dam_model=_DAMPriceModel(outputs=(first_price, equal_price)),
    )
    await built.graph.ainvoke(_state())
    first_success = await built.read_port.get_success(workflow_id=_WORKFLOW_ID)

    reconstructed = _reconstruct(await built.graph.ainvoke(_state()))

    assert reconstructed.phase is WorkflowPhase.RISK_AND_BID
    assert reconstructed.status is WorkflowStatus.RUNNING
    assert len(built.consumer_model.calls) == 2
    assert len(built.dam_model.calls) == 2
    published = await built.read_port.get_success(workflow_id=_WORKFLOW_ID)
    assert published is first_success
    assert published.consumer_load_forecast is first_load
    assert published.dam_price_forecast is first_price
    assert published.consumer_load_forecast is not equal_load
    built.assert_no_failure_processing()
    built.assert_unrelated_collaborators_unused()


async def test_conflicting_reexecution_propagates_conflict_and_keeps_original() -> None:
    first_load = _load_points()
    conflicting_load = _load_points(values_mw=(9.75, 10.0))
    first_price = _price_points()
    built = _Slice(
        plans={_WORKFLOW_ID: _plan()},
        consumer_model=_ConsumerLoadModel(outputs=(first_load, conflicting_load)),
        dam_model=_DAMPriceModel(outputs=(first_price, _price_points())),
    )
    await built.graph.ainvoke(_state())
    first_success = await built.read_port.get_success(workflow_id=_WORKFLOW_ID)

    with pytest.raises(ConflictError) as captured:
        await built.graph.ainvoke(_state())

    assert captured.value.code == "conflict"
    assert captured.value.message == _MSG_SUCCESS_CONFLICT
    assert len(built.consumer_model.calls) == 2
    published = await built.read_port.get_success(workflow_id=_WORKFLOW_ID)
    assert published is first_success
    assert published.consumer_load_forecast is first_load
    built.assert_no_failure_processing()
    built.assert_unrelated_collaborators_unused()


@pytest.mark.parametrize(
    ("phase", "status"),
    [
        (WorkflowPhase.FORECASTING, WorkflowStatus.PENDING),
        (WorkflowPhase.RISK_AND_BID, WorkflowStatus.RUNNING),
    ],
)
async def test_invalid_entry_fails_closed_without_execution_or_publication(
    phase: WorkflowPhase,
    status: WorkflowStatus,
) -> None:
    built = _Slice(
        plans={_WORKFLOW_ID: _plan()},
        consumer_model=_ConsumerLoadModel(outputs=(_load_points(),)),
        dam_model=_DAMPriceModel(outputs=(_price_points(),)),
    )

    with pytest.raises(InvalidRequestError) as captured:
        await built.graph.ainvoke(_state(phase=phase, status=status))

    assert captured.value.code == "invalid_request"
    assert captured.value.message == _INVALID_ENTRY_ROUTE_MESSAGE
    assert built.consumer_model.calls == []
    assert built.dam_model.calls == []
    await built.assert_success_not_found(_WORKFLOW_ID)
    built.assert_no_failure_processing()
    built.assert_unrelated_collaborators_unused()
