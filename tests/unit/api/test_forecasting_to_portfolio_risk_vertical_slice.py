"""Offline Phase 3 forecasting to Portfolio & Risk handoff verification.

These integration-style tests compose the published Chunk 190 stack builder
and Chunk 191 failure-runtime builder into the real ``build_workflow_graph``
over one real ``InMemoryForecastingReadAfterWriteContext``. After the
compiled graph finishes, the same wrapper instance is injected as the
``ForecastingSuccessReadPort`` of a real ``PortfolioRiskExecutionService``
whose agent is the real ``PortfolioRiskAgent``. Only the two model ports,
the assessment port, and the unrelated Regulatory and Phase 2 graph
collaborators are test doubles. Selector, attempt source, and policy objects
chosen here are test fixtures, not production defaults.

The assessment port fake returns caller-prepared canonical assessments. These
tests prove the application handoff only; they do not prove risk-model
accuracy, market-rule correctness, or production readiness, and empty input
tuples never mean that risk is zero, complete, or acceptable.
"""

from __future__ import annotations

from dataclasses import fields
from datetime import date

import pytest
from langgraph.graph import END, START
from langgraph.graph.state import CompiledStateGraph

from energy_trading.api.composition.forecasting_failure_runtime import (
    build_forecasting_failure_runtime_handler,
)
from energy_trading.api.composition.forecasting_stack import (
    build_forecasting_workflow_step_from_model_ports,
)
from energy_trading.application.agents.base import AgentPort
from energy_trading.application.agents.portfolio_risk import PortfolioRiskAgent
from energy_trading.application.errors import DependencyUnavailableError, ResourceNotFoundError
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
from energy_trading.application.orchestration.portfolio_risk_execution import (
    PortfolioRiskExecutionService,
)
from energy_trading.application.ports.consumer_load_forecast_model import (
    ConsumerLoadForecastModelRequest,
)
from energy_trading.application.ports.dam_price_forecast_model import (
    DAMPriceForecastModelRequest,
)
from energy_trading.application.ports.portfolio_risk_assessment import (
    PortfolioRiskAssessmentPort,
    PortfolioRiskAssessmentRequest,
)
from energy_trading.domain.models.forecasting import LoadForecastPoint, PriceForecastPoint
from energy_trading.domain.models.observations import (
    GenerationAvailabilityRecord,
    HydroRecord,
    MarketPriceRecord,
)
from energy_trading.domain.models.regulatory import RegulatoryConstraint
from energy_trading.domain.models.trading import RiskAssessment
from energy_trading.infrastructure.orchestration.forecasting_context import (
    InMemoryForecastingWorkflowContext,
)
from energy_trading.infrastructure.orchestration.forecasting_read_after_write_context import (
    InMemoryForecastingReadAfterWriteContext,
)
from tests.unit.domain._factories import (
    amd_money,
    amd_price,
    availability,
    constraint,
    consumption,
    diagnostic,
    utc,
)

_WORKFLOW_ID = "wf-handoff-a"
_OTHER_WORKFLOW_ID = "wf-handoff-b"
_PORTFOLIO_ID = "portfolio-handoff"
_DELIVERY_DATE = date(2026, 10, 2)
_SENTINEL_TEXT = "sentinel-handoff-raw-text-not-for-state"
_MSG_SUCCESS_NOT_FOUND = "Forecasting success was not found."
_STATE_FIELDS = frozenset(field.name for field in fields(WorkflowState))
_PUBLISHED_GRAPH_NODES = frozenset(
    {
        START,
        "workflow_entry",
        "regulatory_intelligence",
        "parallel_ingestion",
        "parallel_ingestion_success_transition",
        "forecasting",
        "forecasting_success_transition",
        END,
    }
)


_RiskInputs = tuple[
    tuple[GenerationAvailabilityRecord, ...],
    tuple[HydroRecord, ...],
    tuple[RegulatoryConstraint, ...],
]


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


class _AssessmentPort:
    """Test-only assessment fake behind the real agent. Not a risk engine."""

    def __init__(
        self,
        results: dict[str, RiskAssessment] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self._results = results or {}
        self._error = error
        self.calls: list[PortfolioRiskAssessmentRequest] = []

    async def assess(self, *, request: PortfolioRiskAssessmentRequest) -> RiskAssessment:
        self.calls.append(request)
        if self._error is not None:
            raise self._error
        return self._results[request.workflow_id]


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


def _as_assessment_port(fake: _AssessmentPort) -> PortfolioRiskAssessmentPort:
    """Mypy-visible structural assignment to the published assessment port."""

    return fake


def _as_agent_port(
    agent: PortfolioRiskAgent,
) -> AgentPort[PortfolioRiskAssessmentRequest, RiskAssessment]:
    """Mypy-visible structural assignment to the shared agent port."""

    return agent


class _Handoff:
    """Test-only bundle: one compiled Phase 3 graph and one risk execution service.

    Both stages share the exact same read-after-write wrapper instance.
    """

    def __init__(
        self,
        *,
        plans: dict[str, ForecastingPlan],
        consumer_model: _ConsumerLoadModel,
        dam_model: _DAMPriceModel,
        assessment_port: _AssessmentPort,
    ) -> None:
        self.wrapper = InMemoryForecastingReadAfterWriteContext(
            context=InMemoryForecastingWorkflowContext(plans),
        )
        context_port: ForecastingWorkflowContextPort = self.wrapper
        read_port: ForecastingSuccessReadPort = self.wrapper
        self.read_port = read_port
        self.consumer_model = consumer_model
        self.dam_model = dam_model
        self.assessment_port = assessment_port
        self.attempt_source = _RecordingAttemptNumberSource()
        self.policy = _RecordingFailurePolicy()
        self.regulatory = _UnusedRegulatoryNode()
        self.parallel_ingestion_step = _UnusedParallelIngestionStep()
        self.parallel_ingestion_handler = _UnusedParallelIngestionFailureHandler()
        forecasting_step = build_forecasting_workflow_step_from_model_ports(
            consumer_load_model=consumer_model,
            dam_price_model=dam_model,
            context=context_port,
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
        self.risk_agent = PortfolioRiskAgent(assessment_port=_as_assessment_port(assessment_port))
        self.risk_service = PortfolioRiskExecutionService(
            forecast_reader=read_port,
            risk_agent=_as_agent_port(self.risk_agent),
        )

    def assert_unrelated_collaborators_unused(self) -> None:
        assert self.regulatory.calls == 0
        assert self.parallel_ingestion_step.calls == 0
        assert self.parallel_ingestion_handler.calls == 0

    def assert_no_failure_processing(self) -> None:
        assert self.attempt_source.workflow_ids == []
        assert self.policy.contexts == []

    async def assert_risk_blocked(self, workflow_id: str) -> None:
        calls_before = len(self.assessment_port.calls)
        with pytest.raises(ResourceNotFoundError) as captured:
            await self.execute_risk(workflow_id)
        assert captured.value.code == "resource_not_found"
        assert captured.value.message == _MSG_SUCCESS_NOT_FOUND
        assert _SENTINEL_TEXT not in str(captured.value)
        assert len(self.assessment_port.calls) == calls_before

    async def execute_risk(
        self,
        workflow_id: str,
        inputs: _RiskInputs | None = None,
    ) -> RiskAssessment:
        generation, hydro, regulatory = inputs if inputs is not None else _inputs()
        return await self.risk_service.execute(
            workflow_id=workflow_id,
            portfolio_id=_PORTFOLIO_ID,
            delivery_date=_DELIVERY_DATE,
            generation_availability=generation,
            hydro_resources=hydro,
            regulatory_constraints=regulatory,
        )


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


def _plan() -> ForecastingPlan:
    return ForecastingPlan(
        consumer_load_request=_load_request(),
        dam_price_request=_dam_request(),
    )


def _load_points() -> tuple[LoadForecastPoint, ...]:
    return tuple(
        LoadForecastPoint.model_validate(
            {
                "forecast_run_id": "load-run-1",
                "consumer_id": "consumer-1",
                "generated_at": utc(hour=9),
                "target_timestamp": utc(hour=hour),
                "value_mw": value_mw,
            }
        )
        for hour, value_mw in ((16, 3.25), (17, 3.5))
    )


def _price_points() -> tuple[PriceForecastPoint, ...]:
    return tuple(
        PriceForecastPoint.model_validate(
            {
                "forecast_run_id": "price-run-1",
                "market_id": "market-1",
                "generated_at": utc(hour=9),
                "target_timestamp": utc(hour=hour),
                "price": amd_price(amount),
            }
        )
        for hour, amount in ((16, "45.00"), (17, "-3.10"))
    )


def _hydro() -> HydroRecord:
    return HydroRecord.model_validate(
        {
            "resource_id": "hydro-1",
            "timestamp": utc(),
            "reservoir_level_m": 12.5,
            "available_generation_mw": 4.0,
        }
    )


def _inputs() -> _RiskInputs:
    return (availability(),), (_hydro(),), (constraint(),)


def _assessment(assessment_id: str = "assessment-handoff-1") -> RiskAssessment:
    return RiskAssessment.model_validate(
        {
            "assessment_id": assessment_id,
            "assessed_at": utc(hour=9),
            "delivery_timestamp": utc(day=2, hour=16),
            "risk_score": 0.4,
            "expected_margin": amd_money("1500.00"),
            "value_at_risk": amd_money("250.00"),
            "notes": "caller-prepared test assessment",
        }
    )


def _state(**overrides: object) -> WorkflowState:
    values: dict[str, object] = {
        "workflow_id": _WORKFLOW_ID,
        "portfolio_id": _PORTFOLIO_ID,
        "delivery_date": _DELIVERY_DATE,
        "correlation_id": "corr-handoff",
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


def _successful_handoff(
    assessment_port: _AssessmentPort,
    plans: dict[str, ForecastingPlan] | None = None,
) -> tuple[_Handoff, tuple[LoadForecastPoint, ...], tuple[PriceForecastPoint, ...]]:
    load_points = _load_points()
    price_points = _price_points()
    built = _Handoff(
        plans=plans if plans is not None else {_WORKFLOW_ID: _plan()},
        consumer_model=_ConsumerLoadModel(outputs=(load_points,)),
        dam_model=_DAMPriceModel(outputs=(price_points,)),
        assessment_port=assessment_port,
    )
    return built, load_points, price_points


async def test_graph_forecast_hands_off_to_portfolio_risk_assessment() -> None:
    plan = _plan()
    expected = _assessment()
    built, load_points, price_points = _successful_handoff(
        _AssessmentPort({_WORKFLOW_ID: expected}),
        plans={_WORKFLOW_ID: plan},
    )
    original = _state()
    await built.assert_risk_blocked(_WORKFLOW_ID)

    payload = await built.graph.ainvoke(original)

    reconstructed = _reconstruct(payload)
    assert built.consumer_model.calls == [plan.consumer_load_request]
    assert built.consumer_model.calls[0] is plan.consumer_load_request
    assert built.dam_model.calls == [plan.dam_price_request]
    assert built.dam_model.calls[0] is plan.dam_price_request
    assert reconstructed.phase is WorkflowPhase.RISK_AND_BID
    assert reconstructed.status is WorkflowStatus.RUNNING
    _assert_metadata_preserved(reconstructed, original)
    assert load_points not in payload.values()
    assert price_points not in payload.values()
    assert built.assessment_port.calls == []
    published = await built.read_port.get_success(workflow_id=_WORKFLOW_ID)
    assert isinstance(published, ForecastingSuccess)
    assert await built.read_port.get_success(workflow_id=_WORKFLOW_ID) is published

    generation, hydro, regulatory = _inputs()
    empty_hydro: tuple[HydroRecord, ...] = ()
    result = await built.execute_risk(_WORKFLOW_ID, (generation, empty_hydro, regulatory))

    assert result is expected
    assert len(built.assessment_port.calls) == 1
    request = built.assessment_port.calls[0]
    assert isinstance(request, PortfolioRiskAssessmentRequest)
    assert request.workflow_id == _WORKFLOW_ID
    assert request.portfolio_id == _PORTFOLIO_ID
    assert request.delivery_date == _DELIVERY_DATE
    assert request.forecasting_success is published
    assert request.forecasting_success.consumer_load_forecast is load_points
    assert request.forecasting_success.dam_price_forecast is price_points
    assert all(
        sent is produced
        for sent, produced in zip(
            request.forecasting_success.consumer_load_forecast, load_points, strict=True
        )
    )
    assert all(
        sent is produced
        for sent, produced in zip(
            request.forecasting_success.dam_price_forecast, price_points, strict=True
        )
    )
    assert request.forecasting_success.dam_price_forecast[1].price.currency == "AMD"
    assert request.generation_availability is generation
    assert request.hydro_resources is empty_hydro
    assert request.regulatory_constraints is regulatory
    assert len(built.consumer_model.calls) == 1
    assert len(built.dam_model.calls) == 1
    built.assert_no_failure_processing()
    built.assert_unrelated_collaborators_unused()


@pytest.mark.parametrize("failing_branch", ["consumer_load", "dam_price"])
async def test_forecast_failure_blocks_portfolio_risk_handoff(failing_branch: str) -> None:
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
    built = _Handoff(
        plans={_WORKFLOW_ID: _plan()},
        consumer_model=consumer_model,
        dam_model=dam_model,
        assessment_port=_AssessmentPort({_WORKFLOW_ID: _assessment()}),
    )
    original = _state()

    reconstructed = _reconstruct(await built.graph.ainvoke(original))

    failing_calls = consumer_model.calls if failing_branch == "consumer_load" else dam_model.calls
    assert len(failing_calls) == 1
    assert built.policy.actions == [FailureAction.FAIL]
    assert reconstructed.phase is WorkflowPhase.FORECASTING
    assert reconstructed.status is WorkflowStatus.FAILED
    _assert_metadata_preserved(reconstructed, original)
    assert _SENTINEL_TEXT not in repr(reconstructed)

    await built.assert_risk_blocked(_WORKFLOW_ID)

    assert built.assessment_port.calls == []
    built.assert_unrelated_collaborators_unused()


async def test_risk_handoff_is_isolated_by_exact_workflow_identity() -> None:
    expected = _assessment()
    built, _, _ = _successful_handoff(_AssessmentPort({_WORKFLOW_ID: expected}))
    await built.graph.ainvoke(_state())

    for other in (_OTHER_WORKFLOW_ID, "wf-handoff", "wf-handoff-a ", "WF-HANDOFF-A"):
        await built.assert_risk_blocked(other)
    assert built.assessment_port.calls == []

    assert await built.execute_risk(_WORKFLOW_ID) is expected
    assert [request.workflow_id for request in built.assessment_port.calls] == [_WORKFLOW_ID]

    await built.assert_risk_blocked(_OTHER_WORKFLOW_ID)
    assert len(built.assessment_port.calls) == 1
    assert len(built.consumer_model.calls) == 1
    assert len(built.dam_model.calls) == 1


async def test_assessment_failure_keeps_published_forecast_and_graph_state() -> None:
    error = DependencyUnavailableError("Portfolio risk assessment is unavailable.")
    built, load_points, price_points = _successful_handoff(_AssessmentPort(error=error))
    reconstructed = _reconstruct(await built.graph.ainvoke(_state()))
    snapshot = _reconstruct(
        {field.name: getattr(reconstructed, field.name) for field in fields(reconstructed)}
    )
    published = await built.read_port.get_success(workflow_id=_WORKFLOW_ID)

    with pytest.raises(DependencyUnavailableError) as captured:
        await built.execute_risk(_WORKFLOW_ID)

    assert captured.value is error
    assert len(built.assessment_port.calls) == 1
    assert built.assessment_port.calls[0].forecasting_success is published
    assert await built.read_port.get_success(workflow_id=_WORKFLOW_ID) is published
    assert published.consumer_load_forecast is load_points
    assert published.dam_price_forecast is price_points
    assert reconstructed == snapshot
    assert reconstructed.phase is WorkflowPhase.RISK_AND_BID
    assert reconstructed.status is WorkflowStatus.RUNNING
    assert len(built.consumer_model.calls) == 1
    assert len(built.dam_model.calls) == 1
    built.assert_no_failure_processing()
    built.assert_unrelated_collaborators_unused()


async def test_graph_runs_forecasting_only_and_risk_runs_explicitly_afterwards() -> None:
    expected = _assessment()
    built, _, _ = _successful_handoff(_AssessmentPort({_WORKFLOW_ID: expected}))

    assert set(built.graph.get_graph().nodes) == _PUBLISHED_GRAPH_NODES
    visited = [
        node
        async for update in built.graph.astream(_state(), stream_mode="updates")
        for node in update
    ]

    assert visited == ["workflow_entry", "forecasting", "forecasting_success_transition"]
    assert built.assessment_port.calls == []

    assert await built.execute_risk(_WORKFLOW_ID) is expected
    assert len(built.assessment_port.calls) == 1
    assert len(built.consumer_model.calls) == 1
    assert len(built.dam_model.calls) == 1
    built.assert_unrelated_collaborators_unused()
