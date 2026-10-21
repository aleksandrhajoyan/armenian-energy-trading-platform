"""Trading Strategy Agent application contract.

These tests verify delegation to the injected bid port only. They do not
prove any bid methodology, market-rule correctness, risk-policy sufficiency,
bid profitability, or production trading readiness.
"""

from __future__ import annotations

import inspect
from datetime import date
from decimal import Decimal

import pytest
from tests.unit.domain._factories import amd_price, availability, bid, constraint, utc

from energy_trading.application.agents.base import AgentName, AgentPort
from energy_trading.application.agents.trading_strategy import TradingStrategyAgent
from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.orchestration.forecasting_success import ForecastingSuccess
from energy_trading.application.ports.trading_strategy_bid import (
    TradingStrategyBidPort,
    TradingStrategyBidRequest,
)
from energy_trading.domain.models.forecasting import LoadForecastPoint, PriceForecastPoint
from energy_trading.domain.models.trading import MarketBid, RiskAssessment


class _FakeTradingStrategyBid:
    """Test-only bid port fake. Not a bid algorithm and not a production adapter."""

    def __init__(
        self,
        results: dict[str, tuple[MarketBid, ...]] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.results = results or {}
        self.error = error
        self.calls: list[TradingStrategyBidRequest] = []

    async def propose_bids(self, *, request: TradingStrategyBidRequest) -> tuple[MarketBid, ...]:
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        return self.results[request.workflow_id]


def _as_agent_port(
    agent: TradingStrategyAgent,
) -> AgentPort[TradingStrategyBidRequest, tuple[MarketBid, ...]]:
    """Mypy-visible structural assignment to the shared agent port."""

    return agent


def _as_bid_port(fake: _FakeTradingStrategyBid) -> TradingStrategyBidPort:
    """Mypy-visible structural assignment to the published bid port."""

    return fake


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


def _risk_assessment() -> RiskAssessment:
    return RiskAssessment.model_validate(
        {
            "assessment_id": "assessment-1",
            "assessed_at": utc(hour=9),
            "delivery_timestamp": utc(day=2, hour=16),
            "risk_score": Decimal("0.4"),
        }
    )


def _request(**overrides: object) -> TradingStrategyBidRequest:
    values: dict[str, object] = {
        "workflow_id": "workflow-bid-1",
        "portfolio_id": "portfolio-1",
        "delivery_date": date(2026, 10, 2),
        "risk_assessment": _risk_assessment(),
        "forecasting_success": _success(),
        "generation_availability": (availability(),),
        "regulatory_constraints": (constraint(),),
    }
    values.update(overrides)
    return TradingStrategyBidRequest(**values)  # type: ignore[arg-type]


def _agent(fake: _FakeTradingStrategyBid) -> TradingStrategyAgent:
    return TradingStrategyAgent(bid_port=_as_bid_port(fake))


def test_agent_does_not_inherit_agent_port() -> None:
    assert AgentPort not in TradingStrategyAgent.__mro__
    assert TradingStrategyAgent.__bases__ == (object,)


def test_fake_does_not_inherit_production_bid_port() -> None:
    assert TradingStrategyBidPort not in _FakeTradingStrategyBid.__mro__
    assert _FakeTradingStrategyBid.__bases__ == (object,)


def test_agent_name_is_canonical_trading_strategy_identity() -> None:
    port = _as_agent_port(_agent(_FakeTradingStrategyBid()))
    assert port.name is AgentName.TRADING_STRATEGY
    assert port.name.value == "Trading Strategy Agent"
    assert len(AgentName) == 13


def test_constructor_accepts_only_keyword_only_bid_port() -> None:
    parameters = inspect.signature(TradingStrategyAgent.__init__).parameters
    assert tuple(parameters) == ("self", "bid_port")
    bid_port = parameters["bid_port"]
    assert bid_port.kind is inspect.Parameter.KEYWORD_ONLY
    assert bid_port.default is inspect.Parameter.empty
    fake = _FakeTradingStrategyBid()
    with pytest.raises(TypeError):
        TradingStrategyAgent(fake)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        TradingStrategyAgent()  # type: ignore[call-arg]


def test_constructor_preserves_injected_port_without_invoking_it() -> None:
    fake = _FakeTradingStrategyBid()
    agent = _agent(fake)
    assert list(vars(agent).values()) == [fake]
    assert next(iter(vars(agent).values())) is fake
    assert fake.calls == []


def test_run_signature_matches_published_agent_port() -> None:
    assert inspect.iscoroutinefunction(TradingStrategyAgent.run)
    parameters = inspect.signature(TradingStrategyAgent.run).parameters
    assert tuple(parameters) == ("self", "request")
    assert parameters["request"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert isinstance(inspect.getattr_static(TradingStrategyAgent, "name"), property)


async def test_run_forwards_exact_request_and_leaves_inputs_unchanged() -> None:
    request = _request()
    assessment = request.risk_assessment
    assessment_snapshot = assessment.model_dump()
    success = request.forecasting_success
    generation = request.generation_availability
    constraints = request.regulatory_constraints
    proposals = (bid(),)
    fake = _FakeTradingStrategyBid({"workflow-bid-1": proposals})
    await _as_agent_port(_agent(fake)).run(request)
    assert len(fake.calls) == 1
    assert fake.calls[0] is request
    assert request.risk_assessment is assessment
    assert assessment.model_dump() == assessment_snapshot
    assert request.forecasting_success is success
    assert request.forecasting_success.consumer_load_forecast is success.consumer_load_forecast
    assert request.forecasting_success.dam_price_forecast is success.dam_price_forecast
    assert request.generation_availability is generation
    assert request.regulatory_constraints is constraints


async def test_run_returns_exact_proposal_tuple_and_bid_instances() -> None:
    first = bid(bid_id="bid-1", delivery_timestamp=utc(hour=17))
    second = bid(bid_id="bid-2", delivery_timestamp=utc(hour=16))
    proposals = (first, second)
    snapshots = (first.model_dump(), second.model_dump())
    fake = _FakeTradingStrategyBid({"workflow-bid-1": proposals})
    result = await _agent(fake).run(_request())
    assert result is proposals
    assert result[0] is first
    assert result[1] is second
    assert tuple(item.bid_id for item in result) == ("bid-1", "bid-2")
    assert (first.model_dump(), second.model_dump()) == snapshots
    assert len(fake.calls) == 1


async def test_run_passes_empty_proposal_tuple_through_unchanged() -> None:
    proposals: tuple[MarketBid, ...] = ()
    request = _request()
    fake = _FakeTradingStrategyBid({"workflow-bid-1": proposals})
    result = await _agent(fake).run(request)
    assert result is proposals
    assert result == ()
    assert fake.calls == [request]


async def test_run_propagates_dependency_unavailable_without_retry_or_fallback() -> None:
    error = DependencyUnavailableError("trading strategy bid proposals unavailable")
    fake = _FakeTradingStrategyBid(error=error)
    with pytest.raises(DependencyUnavailableError) as caught:
        await _agent(fake).run(_request())
    assert caught.value is error
    assert len(fake.calls) == 1


async def test_run_does_not_catch_or_sanitize_unexpected_exceptions() -> None:
    error = RuntimeError("unexpected bid proposal failure")
    fake = _FakeTradingStrategyBid(error=error)
    with pytest.raises(RuntimeError) as caught:
        await _agent(fake).run(_request())
    assert caught.value is error
    assert str(caught.value) == "unexpected bid proposal failure"
    assert len(fake.calls) == 1


async def test_run_forwards_independent_requests_without_leaking_results() -> None:
    first_proposals = (bid(bid_id="bid-1"),)
    second_proposals = (bid(bid_id="bid-2"), bid(bid_id="bid-3"))
    fake = _FakeTradingStrategyBid(
        {"workflow-bid-1": first_proposals, "workflow-bid-2": second_proposals}
    )
    agent = _agent(fake)
    first_request = _request(workflow_id="workflow-bid-1")
    second_request = _request(workflow_id="workflow-bid-2")
    second_result = await agent.run(second_request)
    first_result = await agent.run(first_request)
    assert second_result is second_proposals
    assert first_result is first_proposals
    assert len(fake.calls) == 2
    assert fake.calls[0] is second_request
    assert fake.calls[1] is first_request


async def test_entire_proposal_result_originates_from_injected_port() -> None:
    proposals = (bid(bid_id="bid-port-only"),)
    fake = _FakeTradingStrategyBid({"workflow-bid-1": proposals})
    agent = _agent(fake)
    first = await agent.run(_request())
    second = await agent.run(_request())
    assert first is proposals
    assert second is proposals
    assert len(fake.calls) == 2
    assert fake.calls[0] is not fake.calls[1]
