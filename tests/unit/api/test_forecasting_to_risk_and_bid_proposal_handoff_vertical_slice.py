"""Offline Phase 3 forecasting to Risk & Bid proposal handoff vertical slice.

These integration-style tests compose the published Chunk 190 stack builder
and Chunk 191 failure-runtime builder into the real ``build_workflow_graph``
over one real ``InMemoryForecastingReadAfterWriteContext``. After the
compiled graph finishes, the test separately constructs a real
``PortfolioRiskExecutionService`` through the published Chunk 201
``build_portfolio_risk_execution_service`` and a real
``TradingStrategyProposalHandoffService`` through the published Chunk 209
``build_trading_strategy_proposal_handoff_service``, then executes them in
order and receives the published ``RiskAndBidProposalHandoff``. Only the two
model ports, the assessment port, the bid port, and the unrelated Regulatory
and Phase 2 graph collaborators are test doubles. Selector, attempt source,
and policy objects chosen here are test fixtures, not production defaults.

Read ownership: the Portfolio & Risk service performs its own
``get_success`` read through a test-only recording forwarder whose delegate
is the exact wrapper instance the graph wrote to; the test performs a
second, separate read of the same wrapper to obtain the snapshot it hands to
Trading Strategy. Identity across those two reads holds only because this
in-memory wrapper keeps the first published object. It is not evidence of
atomic, versioned, or consistent reads from a future mutable durable store.

The test owns the downstream call order; no production coordinator exists.
The assessment and bid fakes return caller-prepared canonical objects. These
tests prove the application handoff only; they do not prove risk-policy
validity, trading eligibility, bid profitability, exchange acceptance, or
production readiness. A risk assessment is not risk approval, a canonical
bid is not authorization to submit it, and an empty proposal tuple is not
approval or market success.
"""

from __future__ import annotations

import asyncio
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
from energy_trading.api.composition.portfolio_risk_stack import (
    build_portfolio_risk_execution_service,
)
from energy_trading.api.composition.trading_strategy_proposal_handoff_stack import (
    build_trading_strategy_proposal_handoff_service,
)
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
    trading_strategy_proposal_handoff,
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
from energy_trading.application.orchestration.risk_and_bid_proposal_handoff import (
    RiskAndBidProposalHandoff,
)
from energy_trading.application.orchestration.trading_strategy_proposal_handoff import (
    TradingStrategyProposalHandoffService,
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
from energy_trading.application.ports.trading_strategy_bid import (
    TradingStrategyBidPort,
    TradingStrategyBidRequest,
)
from energy_trading.domain.models.forecasting import LoadForecastPoint, PriceForecastPoint
from energy_trading.domain.models.observations import (
    GenerationAvailabilityRecord,
    HydroRecord,
    MarketPriceRecord,
)
from energy_trading.domain.models.regulatory import RegulatoryConstraint
from energy_trading.domain.models.trading import BidSide, MarketBid, RiskAssessment
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
    bid,
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
_HANDOFF_FIELDS = (
    "workflow_id",
    "portfolio_id",
    "delivery_date",
    "forecasting_success",
    "risk_assessment",
    "bid_proposals",
)
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


_Inputs = tuple[
    tuple[GenerationAvailabilityRecord, ...],
    tuple[HydroRecord, ...],
    tuple[RegulatoryConstraint, ...],
]


class _ConsumerLoadModel:
    """Test-only Consumer Load port fake keyed by forecast run identity."""

    def __init__(
        self,
        outputs: dict[str, tuple[LoadForecastPoint, ...]] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._outputs = outputs or {}
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
        return self._outputs[request.forecast_run_id]


class _DAMPriceModel:
    """Test-only DAM Price port fake keyed by forecast run identity."""

    def __init__(
        self,
        outputs: dict[str, tuple[PriceForecastPoint, ...]] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._outputs = outputs or {}
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
        return self._outputs[request.forecast_run_id]


class _RecordingForecastReader:
    """Test-only read forwarder over the exact graph-facing wrapper instance."""

    def __init__(
        self,
        events: list[tuple[str, str]],
        inner: InMemoryForecastingReadAfterWriteContext,
    ) -> None:
        self._events = events
        self.inner = inner
        self.returned: list[ForecastingSuccess] = []

    async def get_success(self, *, workflow_id: str) -> ForecastingSuccess:
        self._events.append(("risk_read", workflow_id))
        success = await self.inner.get_success(workflow_id=workflow_id)
        self.returned.append(success)
        return success


class _AssessmentPort:
    """Test-only assessment fake behind the real agent. Not a risk engine."""

    def __init__(
        self,
        events: list[tuple[str, str]],
        results: dict[str, RiskAssessment] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self._events = events
        self._results = results or {}
        self._error = error
        self.calls: list[PortfolioRiskAssessmentRequest] = []

    async def assess(self, *, request: PortfolioRiskAssessmentRequest) -> RiskAssessment:
        self.calls.append(request)
        self._events.append(("assess", request.workflow_id))
        if self._error is not None:
            raise self._error
        return self._results[request.workflow_id]


class _BidPort:
    """Test-only bid port fake behind the real agent. Not a bid engine."""

    def __init__(
        self,
        events: list[tuple[str, str]],
        results: dict[str, object] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self._events = events
        self._results = results or {}
        self._error = error
        self.calls: list[TradingStrategyBidRequest] = []

    async def propose_bids(self, *, request: TradingStrategyBidRequest) -> tuple[MarketBid, ...]:
        self.calls.append(request)
        self._events.append(("propose_bids", request.workflow_id))
        if self._error is not None:
            raise self._error
        # Deliberately nonconforming results are confined to this test fake.
        return self._results[request.workflow_id]  # type: ignore[return-value]


class _HandoffConstructionRecorder:
    """Counts handoff constructions while delegating to the published contract."""

    def __init__(self) -> None:
        self.constructed: list[RiskAndBidProposalHandoff] = []

    def __call__(self, **kwargs: object) -> RiskAndBidProposalHandoff:
        handoff = RiskAndBidProposalHandoff(**kwargs)  # type: ignore[arg-type]
        self.constructed.append(handoff)
        return handoff


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


def _as_read_port(reader: _RecordingForecastReader) -> ForecastingSuccessReadPort:
    """Mypy-visible structural assignment to the published read port."""

    return reader


def _as_assessment_port(fake: _AssessmentPort) -> PortfolioRiskAssessmentPort:
    """Mypy-visible structural assignment to the published assessment port."""

    return fake


def _as_bid_port(fake: _BidPort) -> TradingStrategyBidPort:
    """Mypy-visible structural assignment to the published bid port."""

    return fake


@pytest.fixture
def handoff_recorder(monkeypatch: pytest.MonkeyPatch) -> _HandoffConstructionRecorder:
    recorder = _HandoffConstructionRecorder()
    monkeypatch.setattr(
        trading_strategy_proposal_handoff,
        "RiskAndBidProposalHandoff",
        recorder,
    )
    return recorder


class _Vertical:
    """Test-only bundle: one compiled Phase 3 graph plus test-owned Phase 4 stacks.

    The graph-facing forecasting context and the delegate of the Portfolio &
    Risk read forwarder are the exact same read-after-write wrapper
    instance. The Phase 4 stacks are constructed only by ``build_downstream``.
    """

    def __init__(
        self,
        *,
        plans: dict[str, ForecastingPlan],
        consumer_model: _ConsumerLoadModel,
        dam_model: _DAMPriceModel,
        assessment_results: dict[str, RiskAssessment] | None = None,
        assessment_error: Exception | None = None,
        bid_results: dict[str, object] | None = None,
        bid_error: Exception | None = None,
    ) -> None:
        self.events: list[tuple[str, str]] = []
        self.wrapper = InMemoryForecastingReadAfterWriteContext(
            context=InMemoryForecastingWorkflowContext(plans),
        )
        context_port: ForecastingWorkflowContextPort = self.wrapper
        self.reader = _RecordingForecastReader(self.events, self.wrapper)
        self.consumer_model = consumer_model
        self.dam_model = dam_model
        self.assessment_port = _AssessmentPort(
            self.events, assessment_results, error=assessment_error
        )
        self.bid_port = _BidPort(self.events, bid_results, error=bid_error)
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
        self.risk_service: PortfolioRiskExecutionService | None = None
        self.handoff_service: TradingStrategyProposalHandoffService | None = None

    def build_downstream(self) -> None:
        self.risk_service = build_portfolio_risk_execution_service(
            forecast_reader=_as_read_port(self.reader),
            assessment_port=_as_assessment_port(self.assessment_port),
        )
        self.handoff_service = build_trading_strategy_proposal_handoff_service(
            bid_port=_as_bid_port(self.bid_port),
        )

    async def run_graph(self, original: WorkflowState) -> WorkflowState:
        return _reconstruct(await self.graph.ainvoke(original))

    async def snapshot(self, workflow_id: str) -> ForecastingSuccess:
        """Test-owned read of the same wrapper instance, separate from the risk read."""

        return await self.wrapper.get_success(workflow_id=workflow_id)

    async def execute_risk(self, workflow_id: str, inputs: _Inputs) -> RiskAssessment:
        assert self.risk_service is not None
        generation, hydro, regulatory = inputs
        return await self.risk_service.execute(
            workflow_id=workflow_id,
            portfolio_id=_PORTFOLIO_ID,
            delivery_date=_DELIVERY_DATE,
            generation_availability=generation,
            hydro_resources=hydro,
            regulatory_constraints=regulatory,
        )

    async def execute_handoff(
        self,
        workflow_id: str,
        *,
        risk_assessment: RiskAssessment,
        forecasting_success: ForecastingSuccess,
        inputs: _Inputs,
    ) -> RiskAndBidProposalHandoff:
        assert self.handoff_service is not None
        generation, _, regulatory = inputs
        return await self.handoff_service.execute(
            workflow_id=workflow_id,
            portfolio_id=_PORTFOLIO_ID,
            delivery_date=_DELIVERY_DATE,
            risk_assessment=risk_assessment,
            forecasting_success=forecasting_success,
            generation_availability=generation,
            regulatory_constraints=regulatory,
        )

    async def assert_forecast_unavailable(self, workflow_id: str) -> None:
        with pytest.raises(ResourceNotFoundError) as captured:
            await self.wrapper.get_success(workflow_id=workflow_id)
        assert captured.value.message == _MSG_SUCCESS_NOT_FOUND

    async def assert_risk_blocked(self, workflow_id: str) -> None:
        calls_before = len(self.assessment_port.calls)
        with pytest.raises(ResourceNotFoundError) as captured:
            await self.execute_risk(workflow_id, _inputs())
        assert captured.value.code == "resource_not_found"
        assert captured.value.message == _MSG_SUCCESS_NOT_FOUND
        assert _SENTINEL_TEXT not in str(captured.value)
        assert len(self.assessment_port.calls) == calls_before

    def assert_unrelated_collaborators_unused(self) -> None:
        assert self.regulatory.calls == 0
        assert self.parallel_ingestion_step.calls == 0
        assert self.parallel_ingestion_handler.calls == 0

    def assert_no_failure_processing(self) -> None:
        assert self.attempt_source.workflow_ids == []
        assert self.policy.contexts == []


def _load_request(forecast_run_id: str) -> ConsumerLoadForecastModelRequest:
    return ConsumerLoadForecastModelRequest(
        forecast_run_id=forecast_run_id,
        generated_at=utc(hour=9),
        consumer_id="consumer-1",
        history=(consumption(),),
        target_timestamps=(utc(hour=16), utc(hour=17)),
    )


def _dam_request(forecast_run_id: str) -> DAMPriceForecastModelRequest:
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


def _plan(suffix: str = "1") -> ForecastingPlan:
    return ForecastingPlan(
        consumer_load_request=_load_request(f"load-run-{suffix}"),
        dam_price_request=_dam_request(f"price-run-{suffix}"),
    )


def _load_points(
    suffix: str = "1",
    values: tuple[float, float] = (3.25, 3.5),
) -> tuple[LoadForecastPoint, ...]:
    return tuple(
        LoadForecastPoint.model_validate(
            {
                "forecast_run_id": f"load-run-{suffix}",
                "consumer_id": "consumer-1",
                "generated_at": utc(hour=9),
                "target_timestamp": utc(hour=hour),
                "value_mw": value_mw,
            }
        )
        for hour, value_mw in zip((16, 17), values, strict=True)
    )


def _price_points(
    suffix: str = "1",
    amounts: tuple[str, str] = ("45.00", "-3.10"),
) -> tuple[PriceForecastPoint, ...]:
    return tuple(
        PriceForecastPoint.model_validate(
            {
                "forecast_run_id": f"price-run-{suffix}",
                "market_id": "market-1",
                "generated_at": utc(hour=9),
                "target_timestamp": utc(hour=hour),
                "price": amd_price(amount),
            }
        )
        for hour, amount in zip((16, 17), amounts, strict=True)
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


def _inputs() -> _Inputs:
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


def _proposals(prefix: str = "bid-a") -> tuple[MarketBid, ...]:
    return (
        bid(bid_id=f"{prefix}-1", side=BidSide.SELL, quantity_mw=5.0),
        bid(
            bid_id=f"{prefix}-2",
            side=BidSide.BUY,
            quantity_mw=2.5,
            delivery_timestamp=utc(hour=17),
            limit_price=amd_price("7.25"),
        ),
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


def _successful_vertical(
    *,
    assessment_results: dict[str, RiskAssessment] | None = None,
    assessment_error: Exception | None = None,
    bid_results: dict[str, object] | None = None,
    bid_error: Exception | None = None,
) -> tuple[_Vertical, tuple[LoadForecastPoint, ...], tuple[PriceForecastPoint, ...]]:
    load_points = _load_points()
    price_points = _price_points()
    built = _Vertical(
        plans={_WORKFLOW_ID: _plan()},
        consumer_model=_ConsumerLoadModel({"load-run-1": load_points}),
        dam_model=_DAMPriceModel({"price-run-1": price_points}),
        assessment_results=assessment_results,
        assessment_error=assessment_error,
        bid_results=bid_results,
        bid_error=bid_error,
    )
    return built, load_points, price_points


# A. Complete successful handoff


async def test_graph_forecast_reaches_risk_and_bid_proposal_handoff(
    handoff_recorder: _HandoffConstructionRecorder,
) -> None:
    expected_assessment = _assessment()
    expected_proposals = _proposals()
    built, load_points, price_points = _successful_vertical(
        assessment_results={_WORKFLOW_ID: expected_assessment},
        bid_results={_WORKFLOW_ID: expected_proposals},
    )
    assert set(built.graph.get_graph().nodes) == _PUBLISHED_GRAPH_NODES
    original = _state()
    await built.assert_forecast_unavailable(_WORKFLOW_ID)

    reconstructed = await built.run_graph(original)

    assert reconstructed.phase is WorkflowPhase.RISK_AND_BID
    assert reconstructed.status is WorkflowStatus.RUNNING
    _assert_metadata_preserved(reconstructed, original)
    assert built.events == []
    assert handoff_recorder.constructed == []

    built.build_downstream()
    inputs = _inputs()
    generation, hydro, regulatory = inputs
    assessment = await built.execute_risk(_WORKFLOW_ID, inputs)

    assert assessment is expected_assessment
    assert built.reader.inner is built.wrapper
    assert len(built.reader.returned) == 1
    assert len(built.assessment_port.calls) == 1
    risk_request = built.assessment_port.calls[0]
    assert risk_request.workflow_id == _WORKFLOW_ID
    assert risk_request.forecasting_success is built.reader.returned[0]
    assert risk_request.generation_availability is generation
    assert risk_request.hydro_resources is hydro
    assert risk_request.regulatory_constraints is regulatory
    assert built.bid_port.calls == []

    snapshot = await built.snapshot(_WORKFLOW_ID)

    assert snapshot is risk_request.forecasting_success
    assert snapshot.consumer_load_forecast is load_points
    assert snapshot.dam_price_forecast is price_points

    handoff = await built.execute_handoff(
        _WORKFLOW_ID,
        risk_assessment=assessment,
        forecasting_success=snapshot,
        inputs=inputs,
    )

    assert len(built.bid_port.calls) == 1
    bid_request = built.bid_port.calls[0]
    assert bid_request.workflow_id == _WORKFLOW_ID
    assert bid_request.portfolio_id == _PORTFOLIO_ID
    assert bid_request.delivery_date == _DELIVERY_DATE
    assert bid_request.risk_assessment is expected_assessment
    assert bid_request.forecasting_success is snapshot
    assert bid_request.forecasting_success is risk_request.forecasting_success
    assert bid_request.generation_availability is generation
    assert bid_request.regulatory_constraints is regulatory
    assert built.events == [
        ("risk_read", _WORKFLOW_ID),
        ("assess", _WORKFLOW_ID),
        ("propose_bids", _WORKFLOW_ID),
    ]

    assert type(handoff) is RiskAndBidProposalHandoff
    assert handoff_recorder.constructed == [handoff]
    assert handoff_recorder.constructed[0] is handoff
    assert tuple(field.name for field in fields(handoff)) == _HANDOFF_FIELDS
    assert handoff.workflow_id == _WORKFLOW_ID
    assert handoff.portfolio_id == _PORTFOLIO_ID
    assert handoff.delivery_date == _DELIVERY_DATE
    assert handoff.forecasting_success is snapshot
    assert handoff.forecasting_success is risk_request.forecasting_success
    assert handoff.forecasting_success.consumer_load_forecast is load_points
    assert handoff.forecasting_success.dam_price_forecast is price_points
    assert handoff.risk_assessment is expected_assessment
    assert handoff.bid_proposals is expected_proposals
    assert all(
        carried is prepared
        for carried, prepared in zip(handoff.bid_proposals, expected_proposals, strict=True)
    )
    assert [proposal.bid_id for proposal in handoff.bid_proposals] == ["bid-a-1", "bid-a-2"]
    assert len(built.consumer_model.calls) == 1
    assert len(built.dam_model.calls) == 1
    built.assert_no_failure_processing()
    built.assert_unrelated_collaborators_unused()


async def test_graph_stops_at_risk_and_bid_without_phase_4_nodes() -> None:
    built, _, _ = _successful_vertical(
        assessment_results={_WORKFLOW_ID: _assessment()},
        bid_results={_WORKFLOW_ID: _proposals()},
    )
    built.build_downstream()

    updates = [update async for update in built.graph.astream(_state(), stream_mode="updates")]
    visited = [node for update in updates for node in update]

    assert visited == ["workflow_entry", "forecasting", "forecasting_success_transition"]
    final = _reconstruct(updates[-1]["forecasting_success_transition"])
    assert final.phase is WorkflowPhase.RISK_AND_BID
    assert final.status is WorkflowStatus.RUNNING
    assert built.events == []
    assert built.reader.returned == []
    assert built.assessment_port.calls == []
    assert built.bid_port.calls == []


# B. Construction does not execute


async def test_constructing_downstream_stacks_executes_nothing(
    handoff_recorder: _HandoffConstructionRecorder,
) -> None:
    built, load_points, price_points = _successful_vertical(
        assessment_results={_WORKFLOW_ID: _assessment()},
        bid_results={_WORKFLOW_ID: _proposals()},
    )
    original = _state()
    reconstructed = await built.run_graph(original)
    published = await built.snapshot(_WORKFLOW_ID)

    built.build_downstream()

    assert type(built.risk_service) is PortfolioRiskExecutionService
    assert type(built.handoff_service) is TradingStrategyProposalHandoffService
    assert built.events == []
    assert built.reader.returned == []
    assert built.assessment_port.calls == []
    assert built.bid_port.calls == []
    assert handoff_recorder.constructed == []
    assert await built.snapshot(_WORKFLOW_ID) is published
    assert published.consumer_load_forecast is load_points
    assert published.dam_price_forecast is price_points
    assert reconstructed.phase is WorkflowPhase.RISK_AND_BID
    assert reconstructed.status is WorkflowStatus.RUNNING
    _assert_metadata_preserved(reconstructed, original)
    assert original.phase is WorkflowPhase.FORECASTING
    assert original.status is WorkflowStatus.RUNNING
    assert len(built.consumer_model.calls) == 1
    assert len(built.dam_model.calls) == 1
    built.assert_no_failure_processing()


# C. Forecasting failure blocks downstream activity


@pytest.mark.parametrize("failing_branch", ["consumer_load", "dam_price"])
async def test_forecast_failure_blocks_risk_bid_and_handoff(
    failing_branch: str,
    handoff_recorder: _HandoffConstructionRecorder,
) -> None:
    error = RuntimeError(_SENTINEL_TEXT)
    consumer_model = (
        _ConsumerLoadModel(error=error)
        if failing_branch == "consumer_load"
        else _ConsumerLoadModel({"load-run-1": _load_points()})
    )
    dam_model = (
        _DAMPriceModel(error=error)
        if failing_branch == "dam_price"
        else _DAMPriceModel({"price-run-1": _price_points()})
    )
    built = _Vertical(
        plans={_WORKFLOW_ID: _plan()},
        consumer_model=consumer_model,
        dam_model=dam_model,
        assessment_results={_WORKFLOW_ID: _assessment()},
        bid_results={_WORKFLOW_ID: _proposals()},
    )
    original = _state()

    reconstructed = await built.run_graph(original)

    failing_calls = consumer_model.calls if failing_branch == "consumer_load" else dam_model.calls
    assert len(failing_calls) == 1
    assert built.policy.actions == [FailureAction.FAIL]
    assert reconstructed.phase is WorkflowPhase.FORECASTING
    assert reconstructed.status is WorkflowStatus.FAILED
    _assert_metadata_preserved(reconstructed, original)
    assert _SENTINEL_TEXT not in repr(reconstructed)

    built.build_downstream()
    await built.assert_forecast_unavailable(_WORKFLOW_ID)
    await built.assert_risk_blocked(_WORKFLOW_ID)

    assert built.events == [("risk_read", _WORKFLOW_ID)]
    assert built.reader.returned == []
    assert built.assessment_port.calls == []
    assert built.bid_port.calls == []
    assert handoff_recorder.constructed == []
    built.assert_unrelated_collaborators_unused()


# D. Assessment failure


async def test_assessment_failure_blocks_bid_and_handoff_and_keeps_forecast(
    handoff_recorder: _HandoffConstructionRecorder,
) -> None:
    error = DependencyUnavailableError("Portfolio risk assessment is unavailable.")
    built, load_points, price_points = _successful_vertical(
        assessment_error=error,
        bid_results={_WORKFLOW_ID: _proposals()},
    )
    reconstructed = await built.run_graph(_state())
    published = await built.snapshot(_WORKFLOW_ID)
    built.build_downstream()

    with pytest.raises(DependencyUnavailableError) as captured:
        await built.execute_risk(_WORKFLOW_ID, _inputs())

    assert captured.value is error
    assert len(built.assessment_port.calls) == 1
    assert built.assessment_port.calls[0].forecasting_success is published
    assert built.bid_port.calls == []
    assert handoff_recorder.constructed == []
    assert built.events == [("risk_read", _WORKFLOW_ID), ("assess", _WORKFLOW_ID)]
    assert await built.snapshot(_WORKFLOW_ID) is published
    assert published.consumer_load_forecast is load_points
    assert published.dam_price_forecast is price_points
    assert reconstructed.phase is WorkflowPhase.RISK_AND_BID
    assert reconstructed.status is WorkflowStatus.RUNNING
    built.assert_no_failure_processing()
    built.assert_unrelated_collaborators_unused()


# E. Bid proposal failure


async def test_bid_failure_propagates_once_without_partial_handoff(
    handoff_recorder: _HandoffConstructionRecorder,
) -> None:
    expected_assessment = _assessment()
    assessment_snapshot = expected_assessment.model_copy(deep=True)
    error = DependencyUnavailableError("Trading strategy bid proposal is unavailable.")
    built, load_points, price_points = _successful_vertical(
        assessment_results={_WORKFLOW_ID: expected_assessment},
        bid_error=error,
    )
    await built.run_graph(_state())
    built.build_downstream()
    inputs = _inputs()
    assessment = await built.execute_risk(_WORKFLOW_ID, inputs)
    published = await built.snapshot(_WORKFLOW_ID)

    with pytest.raises(DependencyUnavailableError) as captured:
        await built.execute_handoff(
            _WORKFLOW_ID,
            risk_assessment=assessment,
            forecasting_success=published,
            inputs=inputs,
        )

    assert captured.value is error
    assert len(built.assessment_port.calls) == 1
    assert len(built.bid_port.calls) == 1
    assert built.bid_port.calls[0].risk_assessment is expected_assessment
    assert built.bid_port.calls[0].forecasting_success is published
    assert handoff_recorder.constructed == []
    assert built.events == [
        ("risk_read", _WORKFLOW_ID),
        ("assess", _WORKFLOW_ID),
        ("propose_bids", _WORKFLOW_ID),
    ]
    assert assessment is expected_assessment
    assert assessment == assessment_snapshot
    assert await built.snapshot(_WORKFLOW_ID) is published
    assert published.consumer_load_forecast is load_points
    assert published.dam_price_forecast is price_points
    built.assert_no_failure_processing()
    built.assert_unrelated_collaborators_unused()


# F. Empty proposal result


async def test_empty_proposal_tuple_is_carried_without_fabricated_bids() -> None:
    empty: tuple[MarketBid, ...] = ()
    expected_assessment = _assessment()
    built, _, _ = _successful_vertical(
        assessment_results={_WORKFLOW_ID: expected_assessment},
        bid_results={_WORKFLOW_ID: empty},
    )
    await built.run_graph(_state())
    built.build_downstream()
    inputs = _inputs()
    assessment = await built.execute_risk(_WORKFLOW_ID, inputs)
    published = await built.snapshot(_WORKFLOW_ID)

    handoff = await built.execute_handoff(
        _WORKFLOW_ID,
        risk_assessment=assessment,
        forecasting_success=published,
        inputs=inputs,
    )

    assert handoff.bid_proposals is empty
    assert handoff.bid_proposals == ()
    assert handoff.risk_assessment is expected_assessment
    assert handoff.forecasting_success is published
    assert tuple(field.name for field in fields(handoff)) == _HANDOFF_FIELDS
    assert len(built.bid_port.calls) == 1
    assert built.events == [
        ("risk_read", _WORKFLOW_ID),
        ("assess", _WORKFLOW_ID),
        ("propose_bids", _WORKFLOW_ID),
    ]


# G. Invalid bid-port output


@pytest.mark.parametrize(
    ("returned", "message"),
    [
        ([bid()], "bid_proposals must be an immutable tuple"),
        ((bid(), object()), "bid_proposals must contain MarketBid values"),
    ],
)
async def test_nonconforming_bid_output_is_rejected_by_the_handoff_contract(
    returned: object,
    message: str,
    handoff_recorder: _HandoffConstructionRecorder,
) -> None:
    expected_assessment = _assessment()
    built, _, _ = _successful_vertical(
        assessment_results={_WORKFLOW_ID: expected_assessment},
        bid_results={_WORKFLOW_ID: returned},
    )
    await built.run_graph(_state())
    built.build_downstream()
    inputs = _inputs()
    assessment = await built.execute_risk(_WORKFLOW_ID, inputs)
    published = await built.snapshot(_WORKFLOW_ID)

    with pytest.raises(TypeError, match=message):
        await built.execute_handoff(
            _WORKFLOW_ID,
            risk_assessment=assessment,
            forecasting_success=published,
            inputs=inputs,
        )

    assert len(built.assessment_port.calls) == 1
    assert len(built.bid_port.calls) == 1
    assert handoff_recorder.constructed == []
    assert assessment is expected_assessment
    assert await built.snapshot(_WORKFLOW_ID) is published


# H. Workflow isolation


async def test_interleaved_workflows_receive_only_their_own_results(
    handoff_recorder: _HandoffConstructionRecorder,
) -> None:
    first_load, first_price = _load_points("1"), _price_points("1")
    second_load = _load_points("2", (6.0, 6.5))
    second_price = _price_points("2", ("51.00", "12.40"))
    first_assessment = _assessment("assessment-handoff-a")
    second_assessment = _assessment("assessment-handoff-b")
    first_proposals = _proposals("bid-a")
    second_proposals = _proposals("bid-b")
    built = _Vertical(
        plans={_WORKFLOW_ID: _plan("1"), _OTHER_WORKFLOW_ID: _plan("2")},
        consumer_model=_ConsumerLoadModel({"load-run-1": first_load, "load-run-2": second_load}),
        dam_model=_DAMPriceModel({"price-run-1": first_price, "price-run-2": second_price}),
        assessment_results={
            _WORKFLOW_ID: first_assessment,
            _OTHER_WORKFLOW_ID: second_assessment,
        },
        bid_results={_WORKFLOW_ID: first_proposals, _OTHER_WORKFLOW_ID: second_proposals},
    )
    first_state, second_state = await asyncio.gather(
        built.run_graph(_state()),
        built.run_graph(_state(workflow_id=_OTHER_WORKFLOW_ID)),
    )
    assert first_state.workflow_id == _WORKFLOW_ID
    assert second_state.workflow_id == _OTHER_WORKFLOW_ID
    assert first_state.phase is second_state.phase is WorkflowPhase.RISK_AND_BID
    built.build_downstream()
    for unknown in ("wf-unknown", "wf-handoff", "wf-handoff-a ", "WF-HANDOFF-A"):
        await built.assert_risk_blocked(unknown)
    del built.events[:]

    inputs = _inputs()
    second_risk = await built.execute_risk(_OTHER_WORKFLOW_ID, inputs)
    first_risk = await built.execute_risk(_WORKFLOW_ID, inputs)
    first_success = await built.snapshot(_WORKFLOW_ID)
    second_success = await built.snapshot(_OTHER_WORKFLOW_ID)
    first_handoff = await built.execute_handoff(
        _WORKFLOW_ID,
        risk_assessment=first_risk,
        forecasting_success=first_success,
        inputs=inputs,
    )
    second_handoff = await built.execute_handoff(
        _OTHER_WORKFLOW_ID,
        risk_assessment=second_risk,
        forecasting_success=second_success,
        inputs=inputs,
    )

    assert first_success is not second_success
    assert first_success.consumer_load_forecast is first_load
    assert first_success.dam_price_forecast is first_price
    assert second_success.consumer_load_forecast is second_load
    assert second_success.dam_price_forecast is second_price
    assert built.assessment_port.calls[0].forecasting_success is second_success
    assert built.assessment_port.calls[1].forecasting_success is first_success
    assert first_risk is first_assessment
    assert second_risk is second_assessment
    assert built.bid_port.calls[0].risk_assessment is first_assessment
    assert built.bid_port.calls[0].forecasting_success is first_success
    assert built.bid_port.calls[1].risk_assessment is second_assessment
    assert built.bid_port.calls[1].forecasting_success is second_success
    assert handoff_recorder.constructed == [first_handoff, second_handoff]
    assert first_handoff.workflow_id == _WORKFLOW_ID
    assert first_handoff.forecasting_success is first_success
    assert first_handoff.risk_assessment is first_assessment
    assert first_handoff.bid_proposals is first_proposals
    assert second_handoff.workflow_id == _OTHER_WORKFLOW_ID
    assert second_handoff.forecasting_success is second_success
    assert second_handoff.risk_assessment is second_assessment
    assert second_handoff.bid_proposals is second_proposals
    assert built.events == [
        ("risk_read", _OTHER_WORKFLOW_ID),
        ("assess", _OTHER_WORKFLOW_ID),
        ("risk_read", _WORKFLOW_ID),
        ("assess", _WORKFLOW_ID),
        ("propose_bids", _WORKFLOW_ID),
        ("propose_bids", _OTHER_WORKFLOW_ID),
    ]
    assert len(built.consumer_model.calls) == 2
    assert len(built.dam_model.calls) == 2
    built.assert_no_failure_processing()
    built.assert_unrelated_collaborators_unused()
