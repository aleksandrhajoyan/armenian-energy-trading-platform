"""Offline Phase 3 forecasting vertical slice through the real compiled graph.

These integration-style tests compose the published Chunk 190 stack builder
and Chunk 191 failure-runtime builder from explicit test-supplied ports, hand
the results to the real ``build_workflow_graph``, and invoke the compiled
graph. Only the two external model ports and the unrelated Regulatory and
Phase 2 graph collaborators are test doubles. Selector, attempt source, and
policy objects chosen here are test fixtures, not production defaults.
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
    DependencyUnavailableError,
    InvalidRequestError,
    ResourceNotFoundError,
)
from energy_trading.application.orchestration import (
    FailureAction,
    FailurePolicyContext,
    ForecastingAgentFailure,
    ForecastingPlan,
    ForecastingSuccess,
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
from tests.unit.domain._factories import amd_price, consumption, diagnostic, utc

_WORKFLOW_ID = "wf-phase3-slice"
_SENTINEL_TEXT = "sentinel-phase3-slice-text-not-for-state"
_INVALID_ENTRY_ROUTE_MESSAGE = (
    "Workflow entry routing requires contract running, ingestion running, "
    "or forecasting running status."
)
_STATE_FIELDS = frozenset(field.name for field in fields(WorkflowState))


class _ConsumerLoadModel:
    """Test-only model fake that structurally satisfies the Consumer Load port."""

    def __init__(
        self,
        points: tuple[LoadForecastPoint, ...] = (),
        error: Exception | None = None,
    ) -> None:
        self.points = points
        self.error = error
        self.calls: list[ConsumerLoadForecastModelRequest] = []

    async def forecast(
        self,
        *,
        request: ConsumerLoadForecastModelRequest,
    ) -> tuple[LoadForecastPoint, ...]:
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        return self.points


class _DAMPriceModel:
    """Test-only model fake that structurally satisfies the DAM Price port."""

    def __init__(
        self,
        points: tuple[PriceForecastPoint, ...] = (),
        error: Exception | None = None,
    ) -> None:
        self.points = points
        self.error = error
        self.calls: list[DAMPriceForecastModelRequest] = []

    async def forecast(
        self,
        *,
        request: DAMPriceForecastModelRequest,
    ) -> tuple[PriceForecastPoint, ...]:
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        return self.points


class _RecordingContext:
    """Test-only forwarding wrapper over the real in-memory forecasting context."""

    def __init__(self, inner: InMemoryForecastingWorkflowContext) -> None:
        self._inner = inner
        self.resolved: list[WorkflowState] = []
        self.recorded: list[tuple[WorkflowState, ForecastingSuccess]] = []

    async def resolve_plan(self, *, state: WorkflowState) -> ForecastingPlan:
        self.resolved.append(state)
        return await self._inner.resolve_plan(state=state)

    async def record_success(
        self,
        *,
        state: WorkflowState,
        success: ForecastingSuccess,
    ) -> None:
        self.recorded.append((state, success))
        await self._inner.record_success(state=state, success=success)


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
    """Test-only bundle of one explicitly composed Phase 3 graph and its doubles."""

    def __init__(
        self,
        *,
        plans: dict[str, ForecastingPlan],
        consumer_model: _ConsumerLoadModel,
        dam_model: _DAMPriceModel,
    ) -> None:
        self.inner_context = InMemoryForecastingWorkflowContext(plans)
        self.context = _RecordingContext(self.inner_context)
        self.consumer_model = consumer_model
        self.dam_model = dam_model
        self.attempt_source = _RecordingAttemptNumberSource()
        self.policy = _RecordingFailurePolicy()
        self.regulatory = _UnusedRegulatoryNode()
        self.parallel_ingestion_step = _UnusedParallelIngestionStep()
        self.parallel_ingestion_handler = _UnusedParallelIngestionFailureHandler()
        self.forecasting_step = build_forecasting_workflow_step_from_model_ports(
            consumer_load_model=consumer_model,
            dam_price_model=dam_model,
            context=self.context,
        )
        self.failure_handler = build_forecasting_failure_runtime_handler(
            selector=StrictSingleForecastingFailureSelector(),
            attempt_number_source=self.attempt_source,
            policy=self.policy,
        )
        self.graph: CompiledStateGraph[WorkflowState, None, WorkflowState, WorkflowState] = (
            build_workflow_graph(
                regulatory_intelligence_node=self.regulatory,  # type: ignore[arg-type]
                parallel_ingestion_step=self.parallel_ingestion_step,  # type: ignore[arg-type]
                parallel_ingestion_failure_runtime_handler=self.parallel_ingestion_handler,  # type: ignore[arg-type]
                forecasting_step=self.forecasting_step,
                forecasting_failure_runtime_handler=self.failure_handler,
            )
        )

    def assert_unrelated_collaborators_unused(self) -> None:
        assert self.regulatory.calls == 0
        assert self.parallel_ingestion_step.calls == 0
        assert self.parallel_ingestion_handler.calls == 0


def _load_request(**overrides: object) -> ConsumerLoadForecastModelRequest:
    values: dict[str, object] = {
        "forecast_run_id": "load-run-1",
        "generated_at": utc(hour=9),
        "consumer_id": "consumer-1",
        "history": (consumption(),),
        "target_timestamps": (utc(hour=16), utc(hour=17)),
    }
    values.update(overrides)
    return ConsumerLoadForecastModelRequest(**values)  # type: ignore[arg-type]


def _dam_request(**overrides: object) -> DAMPriceForecastModelRequest:
    market = MarketPriceRecord.model_validate(
        {
            "market_id": "market-1",
            "timestamp": utc(),
            "price": amd_price(),
        }
    )
    values: dict[str, object] = {
        "forecast_run_id": "price-run-1",
        "generated_at": utc(hour=9),
        "market_id": "market-1",
        "currency": "AMD",
        "history": (market,),
        "target_timestamps": (utc(hour=16), utc(hour=17)),
    }
    values.update(overrides)
    return DAMPriceForecastModelRequest(**values)  # type: ignore[arg-type]


def _plan(
    consumer_load_request: ConsumerLoadForecastModelRequest | None = None,
    dam_price_request: DAMPriceForecastModelRequest | None = None,
) -> ForecastingPlan:
    return ForecastingPlan(
        consumer_load_request=(
            consumer_load_request if consumer_load_request is not None else _load_request()
        ),
        dam_price_request=dam_price_request if dam_price_request is not None else _dam_request(),
    )


def _load_points(
    forecast_run_id: str = "load-run-1",
    consumer_id: str = "consumer-1",
) -> tuple[LoadForecastPoint, ...]:
    return tuple(
        LoadForecastPoint.model_validate(
            {
                "forecast_run_id": forecast_run_id,
                "consumer_id": consumer_id,
                "generated_at": utc(hour=9),
                "target_timestamp": utc(hour=hour),
                "value_mw": value_mw,
            }
        )
        for hour, value_mw in ((16, 3.25), (17, 3.5))
    )


def _price_points(
    forecast_run_id: str = "price-run-1",
    market_id: str = "market-1",
) -> tuple[PriceForecastPoint, ...]:
    return tuple(
        PriceForecastPoint.model_validate(
            {
                "forecast_run_id": forecast_run_id,
                "market_id": market_id,
                "generated_at": utc(hour=9),
                "target_timestamp": utc(hour=hour),
                "price": amd_price(amount),
            }
        )
        for hour, amount in ((16, "45.00"), (17, "-3.10"))
    )


def _diagnostics() -> tuple[AdapterDiagnostic, ...]:
    return (
        diagnostic(),
        AdapterDiagnostic(
            code="SCHEMA_AMBIGUOUS",
            message="header mapping was ambiguous",
            severity=DiagnosticSeverity.WARNING,
            field_name="timestamp",
        ),
    )


def _state(**overrides: object) -> WorkflowState:
    values: dict[str, object] = {
        "workflow_id": _WORKFLOW_ID,
        "portfolio_id": "portfolio-phase3",
        "delivery_date": date(2026, 10, 2),
        "correlation_id": "corr-phase3",
        "phase": WorkflowPhase.FORECASTING,
        "status": WorkflowStatus.RUNNING,
        "diagnostics": _diagnostics(),
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


async def test_offline_success_path_runs_both_models_records_success_and_advances() -> None:
    plan = _plan()
    load_points = _load_points()
    price_points = _price_points()
    built = _Slice(
        plans={_WORKFLOW_ID: plan},
        consumer_model=_ConsumerLoadModel(points=load_points),
        dam_model=_DAMPriceModel(points=price_points),
    )
    original = _state()

    reconstructed = _reconstruct(await built.graph.ainvoke(original))

    assert [state.workflow_id for state in built.context.resolved] == [_WORKFLOW_ID]
    assert built.consumer_model.calls == [plan.consumer_load_request]
    assert built.consumer_model.calls[0] is plan.consumer_load_request
    assert built.dam_model.calls == [plan.dam_price_request]
    assert built.dam_model.calls[0] is plan.dam_price_request
    assert len(built.context.recorded) == 1
    recorded_state, recorded_success = built.context.recorded[0]
    assert recorded_state.workflow_id == _WORKFLOW_ID
    assert recorded_state.phase is WorkflowPhase.FORECASTING
    assert recorded_state.status is WorkflowStatus.RUNNING
    assert isinstance(recorded_success, ForecastingSuccess)
    assert recorded_success.consumer_load_forecast is load_points
    assert recorded_success.dam_price_forecast is price_points
    assert built.attempt_source.workflow_ids == []
    assert built.policy.contexts == []
    assert reconstructed.phase is WorkflowPhase.RISK_AND_BID
    assert reconstructed.status is WorkflowStatus.RUNNING
    _assert_metadata_preserved(reconstructed, original)
    assert original.phase is WorkflowPhase.FORECASTING
    assert original.status is WorkflowStatus.RUNNING
    built.assert_unrelated_collaborators_unused()


async def test_offline_success_is_stored_by_the_real_in_memory_context() -> None:
    load_points = _load_points()
    price_points = _price_points()
    built = _Slice(
        plans={_WORKFLOW_ID: _plan()},
        consumer_model=_ConsumerLoadModel(points=load_points),
        dam_model=_DAMPriceModel(points=price_points),
    )
    original = _state()

    await built.graph.ainvoke(original)

    equal_retry = ForecastingSuccess(
        consumer_load_forecast=load_points,
        dam_price_forecast=price_points,
    )
    await built.inner_context.record_success(state=original, success=equal_retry)
    conflicting = ForecastingSuccess(
        consumer_load_forecast=(),
        dam_price_forecast=price_points,
    )
    with pytest.raises(ConflictError):
        await built.inner_context.record_success(state=original, success=conflicting)


@pytest.mark.parametrize(
    ("failing_branch", "error", "expected_agent", "expected_error_code"),
    [
        (
            "consumer_load",
            RuntimeError(_SENTINEL_TEXT),
            AgentName.CONSUMER_LOAD_FORECAST,
            "forecasting_unexpected_failure",
        ),
        (
            "dam_price",
            DependencyUnavailableError(_SENTINEL_TEXT),
            AgentName.DAM_PRICE_FORECAST,
            "dependency_unavailable",
        ),
    ],
)
async def test_offline_single_branch_failure_ends_forecasting_failed(
    failing_branch: str,
    error: Exception,
    expected_agent: AgentName,
    expected_error_code: str,
) -> None:
    plan = _plan()
    consumer_model = (
        _ConsumerLoadModel(error=error)
        if failing_branch == "consumer_load"
        else _ConsumerLoadModel(points=_load_points())
    )
    dam_model = (
        _DAMPriceModel(error=error)
        if failing_branch == "dam_price"
        else _DAMPriceModel(points=_price_points())
    )
    built = _Slice(
        plans={_WORKFLOW_ID: plan},
        consumer_model=consumer_model,
        dam_model=dam_model,
    )
    original = _state()

    reconstructed = _reconstruct(await built.graph.ainvoke(original))

    assert [state.workflow_id for state in built.context.resolved] == [_WORKFLOW_ID]
    failing_calls: list[object] = list(
        consumer_model.calls if failing_branch == "consumer_load" else dam_model.calls
    )
    expected_request: object = (
        plan.consumer_load_request if failing_branch == "consumer_load" else plan.dam_price_request
    )
    assert len(failing_calls) == 1
    assert failing_calls[0] is expected_request
    assert built.context.recorded == []
    assert built.attempt_source.workflow_ids == [_WORKFLOW_ID]
    assert built.policy.contexts == [
        FailurePolicyContext(
            phase=WorkflowPhase.FORECASTING,
            error_code=expected_error_code,
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
    built.assert_unrelated_collaborators_unused()


@pytest.mark.parametrize(
    ("failing_branch", "expected_agent"),
    [
        ("consumer_load", AgentName.CONSUMER_LOAD_FORECAST),
        ("dam_price", AgentName.DAM_PRICE_FORECAST),
    ],
)
async def test_offline_branch_failure_reaches_graph_as_attributed_exception_group(
    failing_branch: str,
    expected_agent: AgentName,
) -> None:
    error = RuntimeError(_SENTINEL_TEXT)
    built = _Slice(
        plans={_WORKFLOW_ID: _plan()},
        consumer_model=(
            _ConsumerLoadModel(error=error)
            if failing_branch == "consumer_load"
            else _ConsumerLoadModel(points=_load_points())
        ),
        dam_model=(
            _DAMPriceModel(error=error)
            if failing_branch == "dam_price"
            else _DAMPriceModel(points=_price_points())
        ),
    )

    with pytest.raises(BaseExceptionGroup) as captured:
        await built.forecasting_step.run(_state())

    leaves = captured.value.exceptions
    assert len(leaves) == 1
    leaf = leaves[0]
    assert isinstance(leaf, ForecastingAgentFailure)
    assert leaf.agent_name is expected_agent
    assert leaf.__cause__ is error
    assert _SENTINEL_TEXT not in str(leaf)
    assert built.context.recorded == []


async def test_missing_plan_propagates_resource_not_found_without_policy() -> None:
    built = _Slice(
        plans={"wf-other": _plan()},
        consumer_model=_ConsumerLoadModel(points=_load_points()),
        dam_model=_DAMPriceModel(points=_price_points()),
    )
    original = _state()

    with pytest.raises(ResourceNotFoundError) as captured:
        await built.graph.ainvoke(original)

    assert captured.value.code == "resource_not_found"
    assert [state.workflow_id for state in built.context.resolved] == [_WORKFLOW_ID]
    assert built.consumer_model.calls == []
    assert built.dam_model.calls == []
    assert built.context.recorded == []
    assert built.attempt_source.workflow_ids == []
    assert built.policy.contexts == []
    assert original.phase is WorkflowPhase.FORECASTING
    assert original.status is WorkflowStatus.RUNNING
    built.assert_unrelated_collaborators_unused()


@pytest.mark.parametrize(
    ("phase", "status"),
    [
        (WorkflowPhase.FORECASTING, WorkflowStatus.PENDING),
        (WorkflowPhase.FORECASTING, WorkflowStatus.FAILED),
        (WorkflowPhase.FORECASTING, WorkflowStatus.SUCCEEDED),
        (WorkflowPhase.RISK_AND_BID, WorkflowStatus.RUNNING),
        (WorkflowPhase.SETTLEMENT, WorkflowStatus.RUNNING),
    ],
)
async def test_invalid_entry_fails_closed_without_forecasting(
    phase: WorkflowPhase,
    status: WorkflowStatus,
) -> None:
    built = _Slice(
        plans={_WORKFLOW_ID: _plan()},
        consumer_model=_ConsumerLoadModel(points=_load_points()),
        dam_model=_DAMPriceModel(points=_price_points()),
    )
    original = _state(phase=phase, status=status)

    with pytest.raises(InvalidRequestError) as captured:
        await built.graph.ainvoke(original)

    assert captured.value.code == "invalid_request"
    assert captured.value.message == _INVALID_ENTRY_ROUTE_MESSAGE
    assert built.context.resolved == []
    assert built.context.recorded == []
    assert built.consumer_model.calls == []
    assert built.dam_model.calls == []
    assert built.attempt_source.workflow_ids == []
    assert built.policy.contexts == []
    built.assert_unrelated_collaborators_unused()


async def test_independent_slices_keep_workflow_identities_and_models_separate() -> None:
    first_plan = _plan()
    second_plan = _plan(
        consumer_load_request=_load_request(forecast_run_id="load-run-2"),
        dam_price_request=_dam_request(forecast_run_id="price-run-2"),
    )
    first = _Slice(
        plans={"wf-first": first_plan},
        consumer_model=_ConsumerLoadModel(points=_load_points()),
        dam_model=_DAMPriceModel(points=_price_points()),
    )
    second = _Slice(
        plans={"wf-second": second_plan},
        consumer_model=_ConsumerLoadModel(points=_load_points(forecast_run_id="load-run-2")),
        dam_model=_DAMPriceModel(points=_price_points(forecast_run_id="price-run-2")),
    )

    first_result = _reconstruct(await first.graph.ainvoke(_state(workflow_id="wf-first")))
    second_result = _reconstruct(await second.graph.ainvoke(_state(workflow_id="wf-second")))

    assert first_result.workflow_id == "wf-first"
    assert second_result.workflow_id == "wf-second"
    assert first_result.phase is WorkflowPhase.RISK_AND_BID
    assert second_result.phase is WorkflowPhase.RISK_AND_BID
    assert first.consumer_model.calls == [first_plan.consumer_load_request]
    assert first.dam_model.calls == [first_plan.dam_price_request]
    assert second.consumer_model.calls == [second_plan.consumer_load_request]
    assert second.dam_model.calls == [second_plan.dam_price_request]
    assert [state.workflow_id for state, _ in first.context.recorded] == ["wf-first"]
    assert [state.workflow_id for state, _ in second.context.recorded] == ["wf-second"]
    with pytest.raises(ResourceNotFoundError):
        await first.inner_context.resolve_plan(state=_state(workflow_id="wf-second"))
