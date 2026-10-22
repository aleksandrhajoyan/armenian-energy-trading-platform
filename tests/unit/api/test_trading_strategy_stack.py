"""Trading Strategy execution composition wires published application objects.

Bid-port fakes are test-only structural port implementations. Their proposal
tuples are caller-prepared fixtures, not results of a bid engine, and do not
establish market eligibility, trading approval, or exchange acceptance.
"""

from __future__ import annotations

import inspect
from datetime import date

import pytest

from energy_trading.api.composition import trading_strategy_stack
from energy_trading.api.composition.trading_strategy_stack import (
    build_trading_strategy_execution_service,
)
from energy_trading.application.agents.base import AgentPort
from energy_trading.application.agents.trading_strategy import TradingStrategyAgent
from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.orchestration.forecasting_success import ForecastingSuccess
from energy_trading.application.orchestration.trading_strategy_execution import (
    TradingStrategyExecutionService,
)
from energy_trading.application.ports.trading_strategy_bid import (
    TradingStrategyBidPort,
    TradingStrategyBidRequest,
)
from energy_trading.domain.models.forecasting import LoadForecastPoint, PriceForecastPoint
from energy_trading.domain.models.observations import GenerationAvailabilityRecord
from energy_trading.domain.models.regulatory import RegulatoryConstraint
from energy_trading.domain.models.trading import BidSide, MarketBid, RiskAssessment
from energy_trading.domain.value_objects.quantities import EntityId
from tests.unit.domain._factories import amd_money, amd_price, availability, bid, constraint, utc

_WORKFLOW_ID = "workflow-bid-stack-1"
_PORTFOLIO_ID = "portfolio-bid-stack"
_DELIVERY_DATE = date(2026, 10, 2)


class _FakeBidPort:
    """Test-only bid port fake. Not a bid engine and not a market gateway."""

    def __init__(
        self,
        proposals: tuple[MarketBid, ...] = (),
        *,
        error: Exception | None = None,
    ) -> None:
        self.proposals = proposals
        self.error = error
        self.calls: list[TradingStrategyBidRequest] = []

    async def propose_bids(self, *, request: TradingStrategyBidRequest) -> tuple[MarketBid, ...]:
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        return self.proposals


def _as_bid_port(port: _FakeBidPort) -> TradingStrategyBidPort:
    """Mypy-visible structural assignment to the published bid port."""

    return port


def _build(port: _FakeBidPort) -> TradingStrategyExecutionService:
    return build_trading_strategy_execution_service(bid_port=_as_bid_port(port))


class _RecordingTradingStrategyAgent(TradingStrategyAgent):
    instances: list[_RecordingTradingStrategyAgent] = []
    run_calls: int = 0

    def __init__(self, *, bid_port: TradingStrategyBidPort) -> None:
        super().__init__(bid_port=bid_port)
        self.received_bid_port = bid_port
        type(self).instances.append(self)

    async def run(self, request: TradingStrategyBidRequest) -> tuple[MarketBid, ...]:
        type(self).run_calls += 1
        return await super().run(request)


class _RecordingTradingStrategyExecutionService(TradingStrategyExecutionService):
    instances: list[_RecordingTradingStrategyExecutionService] = []
    execute_calls: int = 0

    def __init__(
        self,
        *,
        bid_agent: AgentPort[TradingStrategyBidRequest, tuple[MarketBid, ...]],
    ) -> None:
        super().__init__(bid_agent=bid_agent)
        self.received_bid_agent = bid_agent
        type(self).instances.append(self)

    async def execute(
        self,
        *,
        workflow_id: str,
        portfolio_id: EntityId,
        delivery_date: date,
        risk_assessment: RiskAssessment,
        forecasting_success: ForecastingSuccess,
        generation_availability: tuple[GenerationAvailabilityRecord, ...],
        regulatory_constraints: tuple[RegulatoryConstraint, ...],
    ) -> tuple[MarketBid, ...]:
        type(self).execute_calls += 1
        return await super().execute(
            workflow_id=workflow_id,
            portfolio_id=portfolio_id,
            delivery_date=delivery_date,
            risk_assessment=risk_assessment,
            forecasting_success=forecasting_success,
            generation_availability=generation_availability,
            regulatory_constraints=regulatory_constraints,
        )


@pytest.fixture
def recording_constructors(monkeypatch: pytest.MonkeyPatch) -> None:
    _RecordingTradingStrategyAgent.instances = []
    _RecordingTradingStrategyAgent.run_calls = 0
    _RecordingTradingStrategyExecutionService.instances = []
    _RecordingTradingStrategyExecutionService.execute_calls = 0
    monkeypatch.setattr(
        trading_strategy_stack,
        "TradingStrategyAgent",
        _RecordingTradingStrategyAgent,
    )
    monkeypatch.setattr(
        trading_strategy_stack,
        "TradingStrategyExecutionService",
        _RecordingTradingStrategyExecutionService,
    )


def _success() -> ForecastingSuccess:
    load_point = LoadForecastPoint.model_validate(
        {
            "forecast_run_id": "run-1",
            "consumer_id": "consumer-1",
            "generated_at": utc(),
            "target_timestamp": utc(hour=16),
            "value_mw": 3.25,
        }
    )
    price_point = PriceForecastPoint.model_validate(
        {
            "forecast_run_id": "run-1",
            "market_id": "market-1",
            "generated_at": utc(),
            "target_timestamp": utc(hour=16),
            "price": amd_price("45.00"),
        }
    )
    return ForecastingSuccess(
        consumer_load_forecast=(load_point,),
        dam_price_forecast=(price_point,),
    )


def _assessment() -> RiskAssessment:
    return RiskAssessment.model_validate(
        {
            "assessment_id": "assessment-bid-stack-1",
            "assessed_at": utc(hour=9),
            "delivery_timestamp": utc(day=2, hour=16),
            "risk_score": 0.4,
            "expected_margin": amd_money("1500.00"),
            "value_at_risk": amd_money("250.00"),
            "notes": "caller-prepared test assessment",
        }
    )


async def _execute(
    service: TradingStrategyExecutionService,
    *,
    workflow_id: str = _WORKFLOW_ID,
    risk_assessment: RiskAssessment | None = None,
    forecasting_success: ForecastingSuccess | None = None,
) -> tuple[MarketBid, ...]:
    return await service.execute(
        workflow_id=workflow_id,
        portfolio_id=_PORTFOLIO_ID,
        delivery_date=_DELIVERY_DATE,
        risk_assessment=risk_assessment or _assessment(),
        forecasting_success=forecasting_success or _success(),
        generation_availability=(availability(),),
        regulatory_constraints=(constraint(),),
    )


def test_builder_signature_is_one_keyword_only_bid_port() -> None:
    signature = inspect.signature(build_trading_strategy_execution_service)
    assert tuple(signature.parameters) == ("bid_port",)
    parameter = signature.parameters["bid_port"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is inspect.Parameter.empty
    assert parameter.annotation is TradingStrategyBidPort
    assert signature.return_annotation is TradingStrategyExecutionService
    assert not inspect.iscoroutinefunction(build_trading_strategy_execution_service)


def test_builder_rejects_positional_and_unknown_arguments() -> None:
    port = _FakeBidPort()
    with pytest.raises(TypeError):
        build_trading_strategy_execution_service(port)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        build_trading_strategy_execution_service()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        build_trading_strategy_execution_service(
            bid_port=_as_bid_port(port),
            market_gateway=object(),  # type: ignore[call-arg]
        )


def test_builder_returns_the_existing_execution_service_type() -> None:
    service = _build(_FakeBidPort())
    assert type(service) is TradingStrategyExecutionService
    assert TradingStrategyBidPort not in _FakeBidPort.__mro__


def test_builder_forwards_identities_through_each_constructor(
    recording_constructors: None,
) -> None:
    port = _FakeBidPort()

    service = _build(port)

    assert len(_RecordingTradingStrategyAgent.instances) == 1
    assert len(_RecordingTradingStrategyExecutionService.instances) == 1
    agent = _RecordingTradingStrategyAgent.instances[0]
    built = _RecordingTradingStrategyExecutionService.instances[0]
    assert agent.received_bid_port is port
    assert built.received_bid_agent is agent
    assert service is built


def test_builder_does_not_execute_anything(recording_constructors: None) -> None:
    proposals = (bid(),)
    port = _FakeBidPort(proposals)

    _build(port)

    assert port.calls == []
    assert port.proposals is proposals
    assert port.error is None
    assert _RecordingTradingStrategyAgent.run_calls == 0
    assert _RecordingTradingStrategyExecutionService.execute_calls == 0


async def test_assembled_service_delegates_once_through_real_agent_to_bid_port() -> None:
    first = bid(bid_id="bid-1", side=BidSide.SELL, quantity_mw=5.0)
    second = bid(bid_id="bid-2", side=BidSide.BUY, quantity_mw=2.5, limit_price=amd_price("7.25"))
    proposals = (first, second)
    port = _FakeBidPort(proposals)
    service = _build(port)
    assessment = _assessment()
    success = _success()
    generation = (availability(), availability(asset_id="asset-2"))
    regulatory = (constraint(),)

    result = await service.execute(
        workflow_id=_WORKFLOW_ID,
        portfolio_id=_PORTFOLIO_ID,
        delivery_date=_DELIVERY_DATE,
        risk_assessment=assessment,
        forecasting_success=success,
        generation_availability=generation,
        regulatory_constraints=regulatory,
    )

    assert result is proposals
    assert result[0] is first
    assert result[1] is second
    assert len(port.calls) == 1
    request = port.calls[0]
    assert type(request) is TradingStrategyBidRequest
    assert request.workflow_id == _WORKFLOW_ID
    assert request.portfolio_id == _PORTFOLIO_ID
    assert request.delivery_date == _DELIVERY_DATE
    assert request.risk_assessment is assessment
    assert request.forecasting_success is success
    assert request.generation_availability is generation
    assert request.regulatory_constraints is regulatory


async def test_empty_proposal_tuple_is_returned_unchanged_without_a_default_bid() -> None:
    empty: tuple[MarketBid, ...] = ()
    port = _FakeBidPort(empty)
    service = _build(port)

    result = await _execute(service)

    assert result is empty
    assert result == ()
    assert len(port.calls) == 1


async def test_request_validation_failure_propagates_before_the_bid_port() -> None:
    port = _FakeBidPort((bid(),))
    service = _build(port)

    with pytest.raises(ValueError, match="workflow_id must be a non-empty string"):
        await _execute(service, workflow_id="   ")

    assert port.calls == []


@pytest.mark.parametrize(
    "error",
    [
        DependencyUnavailableError("Trading strategy bid proposal is unavailable."),
        RuntimeError("unexpected bid proposal failure"),
    ],
)
async def test_bid_port_failure_propagates_unchanged_without_retry(error: Exception) -> None:
    port = _FakeBidPort(error=error)
    service = _build(port)

    with pytest.raises(type(error)) as captured:
        await _execute(service)

    assert captured.value is error
    assert len(port.calls) == 1


async def test_independent_builds_use_only_their_own_bid_ports() -> None:
    first_proposals = (bid(bid_id="bid-first"),)
    second_proposals = (bid(bid_id="bid-second"),)
    first_port = _FakeBidPort(first_proposals)
    second_port = _FakeBidPort(second_proposals)
    first_assessment = _assessment()
    second_assessment = _assessment()

    first = _build(first_port)
    second = _build(second_port)

    assert first is not second
    assert await _execute(first, risk_assessment=first_assessment) is first_proposals
    assert len(first_port.calls) == 1
    assert first_port.calls[0].risk_assessment is first_assessment
    assert second_port.calls == []

    assert await _execute(second, risk_assessment=second_assessment) is second_proposals
    assert len(second_port.calls) == 1
    assert second_port.calls[0].risk_assessment is second_assessment
    assert len(first_port.calls) == 1


def test_repeated_builds_construct_new_object_graphs(recording_constructors: None) -> None:
    port = _FakeBidPort()

    first = _build(port)
    second = _build(port)

    assert first is not second
    first_agent, second_agent = _RecordingTradingStrategyAgent.instances
    assert first_agent is not second_agent
    assert first_agent.received_bid_port is port
    assert second_agent.received_bid_port is port
    first_service, second_service = _RecordingTradingStrategyExecutionService.instances
    assert first_service.received_bid_agent is first_agent
    assert second_service.received_bid_agent is second_agent
