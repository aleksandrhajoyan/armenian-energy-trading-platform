"""Trading Strategy bid proposal execution service contract.

These tests verify explicit request assembly, exact-identity forwarding,
single agent delegation, and unchanged propagation only. They do not prove
any bid methodology, market-rule correctness, risk-policy sufficiency, bid
profitability, or production trading readiness. A valid risk assessment is
not trading authorization, and an empty proposal tuple is not approval.
Proposals are explicit test doubles, not results of a bid engine.
"""

from __future__ import annotations

import inspect
from datetime import date, datetime
from decimal import Decimal

import pytest

from energy_trading.application.agents.base import AgentName, AgentPort
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
from tests.unit.domain._factories import amd_price, availability, bid, constraint, utc

_WORKFLOW_ID = "workflow-bid-exec-1"
_OTHER_WORKFLOW_ID = "workflow-bid-exec-2"


class _FakeBidAgent:
    """Test-only structural agent fake. Not a bid engine."""

    def __init__(
        self,
        results: dict[str, tuple[MarketBid, ...]] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.results = results or {}
        self.error = error
        self.calls: list[TradingStrategyBidRequest] = []

    @property
    def name(self) -> AgentName:
        return AgentName.TRADING_STRATEGY

    async def run(self, request: TradingStrategyBidRequest) -> tuple[MarketBid, ...]:
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        return self.results[request.workflow_id]


class _FakeBidPort:
    """Test-only bid port fake behind the real agent. Not a bid engine."""

    def __init__(self, results: dict[str, tuple[MarketBid, ...]]) -> None:
        self.results = results
        self.calls: list[TradingStrategyBidRequest] = []

    async def propose_bids(self, *, request: TradingStrategyBidRequest) -> tuple[MarketBid, ...]:
        self.calls.append(request)
        return self.results[request.workflow_id]


def _as_agent_port(
    agent: _FakeBidAgent | TradingStrategyAgent,
) -> AgentPort[TradingStrategyBidRequest, tuple[MarketBid, ...]]:
    """Mypy-visible structural assignment to the shared agent port."""

    return agent


def _as_bid_port(fake: _FakeBidPort) -> TradingStrategyBidPort:
    """Mypy-visible structural assignment to the published bid port."""

    return fake


def _service(agent: _FakeBidAgent | TradingStrategyAgent) -> TradingStrategyExecutionService:
    return TradingStrategyExecutionService(bid_agent=_as_agent_port(agent))


def _success(*, value_mw: float = 3.25, price: str = "45.00") -> ForecastingSuccess:
    load_point = LoadForecastPoint.model_validate(
        {
            "forecast_run_id": "run-1",
            "consumer_id": "consumer-1",
            "generated_at": utc(),
            "target_timestamp": utc(hour=16),
            "value_mw": value_mw,
        }
    )
    price_point = PriceForecastPoint.model_validate(
        {
            "forecast_run_id": "run-1",
            "market_id": "market-1",
            "generated_at": utc(),
            "target_timestamp": utc(hour=16),
            "price": amd_price(price),
        }
    )
    return ForecastingSuccess(
        consumer_load_forecast=(load_point,),
        dam_price_forecast=(price_point,),
    )


def _risk_assessment(**overrides: object) -> RiskAssessment:
    values: dict[str, object] = {
        "assessment_id": "assessment-1",
        "assessed_at": utc(hour=9),
        "delivery_timestamp": utc(day=2, hour=16),
        "risk_score": Decimal("0.4"),
    }
    values.update(overrides)
    return RiskAssessment.model_validate(values)


def _inputs() -> tuple[
    tuple[GenerationAvailabilityRecord, ...],
    tuple[RegulatoryConstraint, ...],
]:
    return (availability(), availability(asset_id="asset-2")), (constraint(),)


def _valid_kwargs() -> dict[str, object]:
    generation, constraints = _inputs()
    return {
        "workflow_id": _WORKFLOW_ID,
        "portfolio_id": "portfolio-1",
        "delivery_date": date(2026, 10, 2),
        "risk_assessment": _risk_assessment(),
        "forecasting_success": _success(),
        "generation_availability": generation,
        "regulatory_constraints": constraints,
    }


def test_service_does_not_inherit_a_base_class() -> None:
    assert TradingStrategyExecutionService.__bases__ == (object,)


def test_fakes_do_not_inherit_published_protocols() -> None:
    assert AgentPort not in _FakeBidAgent.__mro__
    assert _FakeBidAgent.__bases__ == (object,)
    assert TradingStrategyBidPort not in _FakeBidPort.__mro__
    assert _FakeBidPort.__bases__ == (object,)


def test_constructor_requires_one_keyword_only_bid_agent() -> None:
    parameters = inspect.signature(TradingStrategyExecutionService.__init__).parameters
    assert tuple(parameters) == ("self", "bid_agent")
    assert parameters["bid_agent"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["bid_agent"].default is inspect.Parameter.empty
    with pytest.raises(TypeError):
        TradingStrategyExecutionService(_FakeBidAgent())  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        TradingStrategyExecutionService()  # type: ignore[call-arg]


def test_execute_requires_exact_keyword_only_inputs_and_returns_bid_tuple() -> None:
    assert inspect.iscoroutinefunction(TradingStrategyExecutionService.execute)
    signature = inspect.signature(TradingStrategyExecutionService.execute)
    parameters = signature.parameters
    assert tuple(parameters) == (
        "self",
        "workflow_id",
        "portfolio_id",
        "delivery_date",
        "risk_assessment",
        "forecasting_success",
        "generation_availability",
        "regulatory_constraints",
    )
    for name, parameter in parameters.items():
        if name == "self":
            continue
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty
    assert signature.return_annotation == tuple[MarketBid, ...]


async def test_execute_constructs_delegates_and_preserves_every_input_identity() -> None:
    generation, constraints = _inputs()
    risk_assessment = _risk_assessment()
    success = _success()
    consumer_load_forecast = success.consumer_load_forecast
    dam_price_forecast = success.dam_price_forecast
    delivery_date = date(2026, 10, 2)
    proposals = (bid(),)
    agent = _FakeBidAgent({_WORKFLOW_ID: proposals})

    await _service(agent).execute(
        workflow_id=_WORKFLOW_ID,
        portfolio_id="portfolio-1",
        delivery_date=delivery_date,
        risk_assessment=risk_assessment,
        forecasting_success=success,
        generation_availability=generation,
        regulatory_constraints=constraints,
    )

    assert len(agent.calls) == 1
    request = agent.calls[0]
    assert type(request) is TradingStrategyBidRequest
    assert request.workflow_id == _WORKFLOW_ID
    assert request.portfolio_id == "portfolio-1"
    assert request.delivery_date is delivery_date
    assert request.risk_assessment is risk_assessment
    assert request.forecasting_success is success
    assert request.forecasting_success.consumer_load_forecast is consumer_load_forecast
    assert request.forecasting_success.dam_price_forecast is dam_price_forecast
    assert request.generation_availability is generation
    assert request.regulatory_constraints is constraints
    assert all(
        forwarded is original
        for forwarded, original in zip(request.generation_availability, generation, strict=True)
    )
    assert all(
        forwarded is original
        for forwarded, original in zip(request.regulatory_constraints, constraints, strict=True)
    )


async def test_execute_returns_exact_proposal_tuple_with_order_and_fields_unchanged() -> None:
    first = bid(bid_id="bid-1", side=BidSide.SELL, quantity_mw=5.0)
    second = bid(bid_id="bid-2", side=BidSide.BUY, quantity_mw=2.5, limit_price=amd_price("7.25"))
    proposals = (second, first)
    snapshots = [proposal.model_dump() for proposal in proposals]
    agent = _FakeBidAgent({_WORKFLOW_ID: proposals})

    result = await _service(agent).execute(**_valid_kwargs())  # type: ignore[arg-type]

    assert result is proposals
    assert result[0] is second
    assert result[1] is first
    assert [proposal.model_dump() for proposal in result] == snapshots


async def test_empty_proposal_tuple_is_returned_unchanged_without_a_default_bid() -> None:
    empty: tuple[MarketBid, ...] = ()
    agent = _FakeBidAgent({_WORKFLOW_ID: empty})

    result = await _service(agent).execute(**_valid_kwargs())  # type: ignore[arg-type]

    assert result is empty
    assert result == ()
    assert len(agent.calls) == 1


async def test_explicitly_empty_input_tuples_are_forwarded_unchanged() -> None:
    empty_generation: tuple[GenerationAvailabilityRecord, ...] = ()
    empty_constraints: tuple[RegulatoryConstraint, ...] = ()
    agent = _FakeBidAgent({_WORKFLOW_ID: ()})
    kwargs = _valid_kwargs()
    kwargs["generation_availability"] = empty_generation
    kwargs["regulatory_constraints"] = empty_constraints

    await _service(agent).execute(**kwargs)  # type: ignore[arg-type]

    request = agent.calls[0]
    assert request.generation_availability is empty_generation
    assert request.regulatory_constraints is empty_constraints


@pytest.mark.parametrize(
    ("field_name", "value", "error_type", "message"),
    [
        ("workflow_id", "   ", ValueError, "workflow_id must be a non-empty string"),
        ("workflow_id", 7, TypeError, "workflow_id must be a string"),
        ("portfolio_id", "", ValueError, "portfolio_id must be a non-empty string"),
        ("portfolio_id", None, TypeError, "portfolio_id must be a string"),
        (
            "delivery_date",
            datetime(2026, 10, 2, 0, 0),
            TypeError,
            "delivery_date must be a date",
        ),
        ("risk_assessment", object(), TypeError, "risk_assessment must be a RiskAssessment"),
        (
            "forecasting_success",
            object(),
            TypeError,
            "forecasting_success must be a ForecastingSuccess",
        ),
        (
            "generation_availability",
            [availability()],
            TypeError,
            "generation_availability must be an immutable tuple",
        ),
        (
            "regulatory_constraints",
            (availability(),),
            TypeError,
            "regulatory_constraints must contain RegulatoryConstraint values",
        ),
        (
            "generation_availability",
            (constraint(),),
            TypeError,
            "generation_availability must contain GenerationAvailabilityRecord values",
        ),
    ],
)
async def test_request_validation_failure_propagates_before_agent(
    field_name: str,
    value: object,
    error_type: type[Exception],
    message: str,
) -> None:
    agent = _FakeBidAgent({_WORKFLOW_ID: (bid(),)})
    kwargs = _valid_kwargs()
    kwargs[field_name] = value

    with pytest.raises(error_type, match=message):
        await _service(agent).execute(**kwargs)  # type: ignore[arg-type]

    assert agent.calls == []


@pytest.mark.parametrize(
    "error",
    [
        DependencyUnavailableError("trading strategy bid proposal unavailable"),
        RuntimeError("unexpected bid proposal failure"),
    ],
)
async def test_agent_failure_propagates_exact_instance_without_retry(error: Exception) -> None:
    agent = _FakeBidAgent(error=error)

    with pytest.raises(type(error)) as caught:
        await _service(agent).execute(**_valid_kwargs())  # type: ignore[arg-type]

    assert caught.value is error
    assert str(caught.value) == str(error)
    assert len(agent.calls) == 1


async def test_independent_workflows_do_not_cross_contaminate() -> None:
    first_risk = _risk_assessment(assessment_id="assessment-1")
    second_risk = _risk_assessment(assessment_id="assessment-2", risk_score=Decimal("0.9"))
    first_success = _success(value_mw=3.25, price="45.00")
    second_success = _success(value_mw=7.5, price="80.00")
    first_generation = (availability(asset_id="asset-1"),)
    second_generation = (availability(asset_id="asset-2"),)
    first_constraints = (constraint(constraint_id="constraint-1"),)
    second_constraints = (constraint(constraint_id="constraint-2"),)
    first_proposals = (bid(bid_id="bid-1"),)
    second_proposals = (bid(bid_id="bid-2"), bid(bid_id="bid-3"))
    agent = _FakeBidAgent({_WORKFLOW_ID: first_proposals, _OTHER_WORKFLOW_ID: second_proposals})
    service = _service(agent)

    second_result = await service.execute(
        workflow_id=_OTHER_WORKFLOW_ID,
        portfolio_id="portfolio-2",
        delivery_date=date(2026, 10, 3),
        risk_assessment=second_risk,
        forecasting_success=second_success,
        generation_availability=second_generation,
        regulatory_constraints=second_constraints,
    )
    first_result = await service.execute(
        workflow_id=_WORKFLOW_ID,
        portfolio_id="portfolio-1",
        delivery_date=date(2026, 10, 2),
        risk_assessment=first_risk,
        forecasting_success=first_success,
        generation_availability=first_generation,
        regulatory_constraints=first_constraints,
    )

    assert second_result is second_proposals
    assert first_result is first_proposals
    assert len(agent.calls) == 2
    second_request, first_request = agent.calls
    assert second_request.workflow_id == _OTHER_WORKFLOW_ID
    assert second_request.portfolio_id == "portfolio-2"
    assert second_request.risk_assessment is second_risk
    assert second_request.forecasting_success is second_success
    assert second_request.generation_availability is second_generation
    assert second_request.regulatory_constraints is second_constraints
    assert first_request.workflow_id == _WORKFLOW_ID
    assert first_request.portfolio_id == "portfolio-1"
    assert first_request.risk_assessment is first_risk
    assert first_request.forecasting_success is first_success
    assert first_request.generation_availability is first_generation
    assert first_request.regulatory_constraints is first_constraints


async def test_unknown_workflow_after_success_fails_closed_without_last_result() -> None:
    agent = _FakeBidAgent({_WORKFLOW_ID: (bid(),)})
    service = _service(agent)

    await service.execute(**_valid_kwargs())  # type: ignore[arg-type]
    kwargs = _valid_kwargs()
    kwargs["workflow_id"] = _OTHER_WORKFLOW_ID
    with pytest.raises(KeyError):
        await service.execute(**kwargs)  # type: ignore[arg-type]

    assert [request.workflow_id for request in agent.calls] == [_WORKFLOW_ID, _OTHER_WORKFLOW_ID]


async def test_real_trading_strategy_agent_delegates_to_bid_port_unchanged() -> None:
    proposals = (bid(bid_id="bid-1"), bid(bid_id="bid-2"))
    bid_port = _FakeBidPort({_WORKFLOW_ID: proposals})
    agent = TradingStrategyAgent(bid_port=_as_bid_port(bid_port))
    kwargs = _valid_kwargs()

    result = await _service(agent).execute(**kwargs)  # type: ignore[arg-type]

    assert result is proposals
    assert len(bid_port.calls) == 1
    request = bid_port.calls[0]
    assert type(request) is TradingStrategyBidRequest
    assert request.workflow_id == _WORKFLOW_ID
    assert request.risk_assessment is kwargs["risk_assessment"]
    assert request.forecasting_success is kwargs["forecasting_success"]
    assert request.generation_availability is kwargs["generation_availability"]
    assert request.regulatory_constraints is kwargs["regulatory_constraints"]
