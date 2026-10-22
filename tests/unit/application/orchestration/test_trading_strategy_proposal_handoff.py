"""Trading Strategy proposal handoff execution service contract.

These tests verify single delegation to the published Trading Strategy
execution service, exact-identity forwarding into the published Risk & Bid
proposal handoff, and unchanged failure propagation only. They do not prove
any bid methodology, risk methodology, market-rule correctness, or trading
readiness. A returned handoff is a proposal result, not an approved,
eligible, submitted, or settled trading decision. Proposals are explicit
test doubles behind the real Chunk 206 builder, not results of a bid engine.
"""

from __future__ import annotations

import dataclasses
import inspect
from datetime import date, datetime
from decimal import Decimal
from typing import get_type_hints

import pytest

from energy_trading.api.composition.trading_strategy_stack import (
    build_trading_strategy_execution_service,
)
from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.orchestration import trading_strategy_proposal_handoff
from energy_trading.application.orchestration.forecasting_success import ForecastingSuccess
from energy_trading.application.orchestration.risk_and_bid_proposal_handoff import (
    RiskAndBidProposalHandoff,
)
from energy_trading.application.orchestration.trading_strategy_execution import (
    TradingStrategyExecutionService,
)
from energy_trading.application.orchestration.trading_strategy_proposal_handoff import (
    TradingStrategyProposalHandoffService,
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
from tests.unit.domain._factories import amd_price, availability, bid, constraint, utc

_WORKFLOW_ID = "workflow-bid-handoff-1"
_OTHER_WORKFLOW_ID = "workflow-bid-handoff-2"

_EXECUTE_PARAMETERS = (
    "workflow_id",
    "portfolio_id",
    "delivery_date",
    "risk_assessment",
    "forecasting_success",
    "generation_availability",
    "regulatory_constraints",
)

_HANDOFF_FIELDS = (
    "workflow_id",
    "portfolio_id",
    "delivery_date",
    "forecasting_success",
    "risk_assessment",
    "bid_proposals",
)


class _FakeBidPort:
    """Test-only structural bid port fake. Not a bid engine or market gateway."""

    def __init__(
        self,
        results: dict[str, object] | None = None,
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
        # Deliberately nonconforming results are confined to this test fake.
        return self.results[request.workflow_id]  # type: ignore[return-value]


class _RecordingTradingStrategyExecutionService(TradingStrategyExecutionService):
    """Localized spy over the real execution service; delegates unchanged."""

    def __init__(self, *, delegate: TradingStrategyExecutionService) -> None:
        self._delegate = delegate
        self.execute_calls = 0

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
        self.execute_calls += 1
        return await self._delegate.execute(
            workflow_id=workflow_id,
            portfolio_id=portfolio_id,
            delivery_date=delivery_date,
            risk_assessment=risk_assessment,
            forecasting_success=forecasting_success,
            generation_availability=generation_availability,
            regulatory_constraints=regulatory_constraints,
        )


def _as_bid_port(fake: _FakeBidPort) -> TradingStrategyBidPort:
    """Mypy-visible structural assignment to the published bid port."""

    return fake


def _service(port: _FakeBidPort) -> TradingStrategyProposalHandoffService:
    strategy_service = build_trading_strategy_execution_service(bid_port=_as_bid_port(port))
    return TradingStrategyProposalHandoffService(trading_strategy_service=strategy_service)


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


def _valid_kwargs(workflow_id: str = _WORKFLOW_ID) -> dict[str, object]:
    return {
        "workflow_id": workflow_id,
        "portfolio_id": "portfolio-1",
        "delivery_date": date(2026, 10, 2),
        "risk_assessment": _risk_assessment(),
        "forecasting_success": _success(),
        "generation_availability": (availability(), availability(asset_id="asset-2")),
        "regulatory_constraints": (constraint(),),
    }


class _HandoffConstructionRecorder:
    """Counts handoff constructions while delegating to the published contract."""

    def __init__(self) -> None:
        self.constructed: list[RiskAndBidProposalHandoff] = []

    def __call__(self, **kwargs: object) -> RiskAndBidProposalHandoff:
        handoff = RiskAndBidProposalHandoff(**kwargs)  # type: ignore[arg-type]
        self.constructed.append(handoff)
        return handoff


@pytest.fixture
def handoff_recorder(monkeypatch: pytest.MonkeyPatch) -> _HandoffConstructionRecorder:
    recorder = _HandoffConstructionRecorder()
    monkeypatch.setattr(
        trading_strategy_proposal_handoff,
        "RiskAndBidProposalHandoff",
        recorder,
    )
    return recorder


def test_service_does_not_inherit_a_base_class() -> None:
    assert TradingStrategyProposalHandoffService.__bases__ == (object,)


def test_fake_bid_port_does_not_inherit_the_published_protocol() -> None:
    assert TradingStrategyBidPort not in _FakeBidPort.__mro__
    assert _FakeBidPort.__bases__ == (object,)


def test_constructor_requires_one_keyword_only_execution_service() -> None:
    parameters = inspect.signature(TradingStrategyProposalHandoffService.__init__).parameters
    assert tuple(parameters) == ("self", "trading_strategy_service")
    parameter = parameters["trading_strategy_service"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is inspect.Parameter.empty
    hints = get_type_hints(TradingStrategyProposalHandoffService.__init__)
    assert hints["trading_strategy_service"] is TradingStrategyExecutionService
    strategy_service = build_trading_strategy_execution_service(
        bid_port=_as_bid_port(_FakeBidPort())
    )
    with pytest.raises(TypeError):
        TradingStrategyProposalHandoffService(strategy_service)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        TradingStrategyProposalHandoffService()  # type: ignore[call-arg]


def test_execute_is_async_with_exact_keyword_only_canonical_inputs() -> None:
    assert inspect.iscoroutinefunction(TradingStrategyProposalHandoffService.execute)
    parameters = inspect.signature(TradingStrategyProposalHandoffService.execute).parameters
    assert tuple(parameters) == ("self", *_EXECUTE_PARAMETERS)
    for name, parameter in parameters.items():
        if name == "self":
            continue
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty
    hints = get_type_hints(TradingStrategyProposalHandoffService.execute, include_extras=True)
    assert hints == {
        "workflow_id": str,
        "portfolio_id": EntityId,
        "delivery_date": date,
        "risk_assessment": RiskAssessment,
        "forecasting_success": ForecastingSuccess,
        "generation_availability": tuple[GenerationAvailabilityRecord, ...],
        "regulatory_constraints": tuple[RegulatoryConstraint, ...],
        "return": RiskAndBidProposalHandoff,
    }


async def test_execute_returns_handoff_preserving_every_canonical_identity() -> None:
    first = bid(bid_id="bid-1", side=BidSide.SELL, quantity_mw=5.0)
    second = bid(bid_id="bid-2", side=BidSide.BUY, quantity_mw=2.5, limit_price=amd_price("7.25"))
    proposals = (second, first)
    snapshots = [proposal.model_dump() for proposal in proposals]
    port = _FakeBidPort({_WORKFLOW_ID: proposals})
    risk_assessment = _risk_assessment()
    success = _success()
    consumer_load_forecast = success.consumer_load_forecast
    dam_price_forecast = success.dam_price_forecast
    generation = (availability(), availability(asset_id="asset-2"))
    constraints = (constraint(),)
    delivery_date = date(2026, 10, 2)
    workflow_id = _WORKFLOW_ID
    portfolio_id = "portfolio-1"

    handoff = await _service(port).execute(
        workflow_id=workflow_id,
        portfolio_id=portfolio_id,
        delivery_date=delivery_date,
        risk_assessment=risk_assessment,
        forecasting_success=success,
        generation_availability=generation,
        regulatory_constraints=constraints,
    )

    assert len(port.calls) == 1
    request = port.calls[0]
    assert type(request) is TradingStrategyBidRequest
    assert request.workflow_id is workflow_id
    assert request.portfolio_id is portfolio_id
    assert request.delivery_date is delivery_date
    assert request.risk_assessment is risk_assessment
    assert request.forecasting_success is success
    assert request.generation_availability is generation
    assert request.regulatory_constraints is constraints

    assert type(handoff) is RiskAndBidProposalHandoff
    assert handoff.workflow_id is workflow_id
    assert handoff.portfolio_id is portfolio_id
    assert handoff.delivery_date is delivery_date
    assert handoff.forecasting_success is success
    assert handoff.forecasting_success.consumer_load_forecast is consumer_load_forecast
    assert handoff.forecasting_success.dam_price_forecast is dam_price_forecast
    assert handoff.risk_assessment is risk_assessment
    assert handoff.bid_proposals is proposals
    assert handoff.bid_proposals[0] is second
    assert handoff.bid_proposals[1] is first
    assert [proposal.model_dump() for proposal in handoff.bid_proposals] == snapshots


async def test_handoff_carries_no_approval_eligibility_submission_or_settlement_state() -> None:
    port = _FakeBidPort({_WORKFLOW_ID: (bid(),)})

    handoff = await _service(port).execute(**_valid_kwargs())  # type: ignore[arg-type]

    assert tuple(field.name for field in dataclasses.fields(handoff)) == _HANDOFF_FIELDS
    public_members = {name for name in dir(handoff) if not name.startswith("_")}
    assert public_members == set(_HANDOFF_FIELDS)
    for forbidden in (
        "approved",
        "authorized",
        "eligible",
        "status",
        "submission_id",
        "settlement_status",
    ):
        assert not hasattr(handoff, forbidden), forbidden


async def test_empty_proposal_tuple_is_carried_without_fallback_bid() -> None:
    empty: tuple[MarketBid, ...] = ()
    port = _FakeBidPort({_WORKFLOW_ID: empty})

    handoff = await _service(port).execute(**_valid_kwargs())  # type: ignore[arg-type]

    assert handoff.bid_proposals is empty
    assert handoff.bid_proposals == ()
    assert len(port.calls) == 1
    assert not hasattr(handoff, "status")


@pytest.mark.parametrize(
    ("field_name", "value", "error_type", "message"),
    [
        ("workflow_id", "   ", ValueError, "workflow_id must be a non-empty string"),
        ("portfolio_id", None, TypeError, "portfolio_id must be a string"),
        (
            "delivery_date",
            datetime(2026, 10, 2, 0, 0),
            TypeError,
            "delivery_date must be a date",
        ),
        ("risk_assessment", object(), TypeError, "risk_assessment must be a RiskAssessment"),
        (
            "generation_availability",
            [availability()],
            TypeError,
            "generation_availability must be an immutable tuple",
        ),
    ],
)
async def test_request_validation_failure_propagates_before_bid_port(
    field_name: str,
    value: object,
    error_type: type[Exception],
    message: str,
    handoff_recorder: _HandoffConstructionRecorder,
) -> None:
    port = _FakeBidPort({_WORKFLOW_ID: (bid(),)})
    kwargs = _valid_kwargs()
    kwargs[field_name] = value

    with pytest.raises(error_type, match=message):
        await _service(port).execute(**kwargs)  # type: ignore[arg-type]

    assert port.calls == []
    assert handoff_recorder.constructed == []


@pytest.mark.parametrize(
    "error",
    [
        DependencyUnavailableError("trading strategy bid proposal unavailable"),
        RuntimeError("unexpected bid proposal failure"),
    ],
)
async def test_bid_port_failure_propagates_exact_instance_without_handoff(
    error: Exception,
    handoff_recorder: _HandoffConstructionRecorder,
) -> None:
    port = _FakeBidPort(error=error)

    with pytest.raises(type(error)) as caught:
        await _service(port).execute(**_valid_kwargs())  # type: ignore[arg-type]

    assert caught.value is error
    assert str(caught.value) == str(error)
    assert len(port.calls) == 1
    assert handoff_recorder.constructed == []


@pytest.mark.parametrize(
    ("returned", "message"),
    [
        ([bid()], "bid_proposals must be an immutable tuple"),
        ((bid(), object()), "bid_proposals must contain MarketBid values"),
        ((availability(),), "bid_proposals must contain MarketBid values"),
    ],
)
async def test_nonconforming_returned_proposals_fail_handoff_validation(
    returned: object,
    message: str,
    handoff_recorder: _HandoffConstructionRecorder,
) -> None:
    port = _FakeBidPort({_WORKFLOW_ID: returned})

    with pytest.raises(TypeError, match=message):
        await _service(port).execute(**_valid_kwargs())  # type: ignore[arg-type]

    assert len(port.calls) == 1
    assert handoff_recorder.constructed == []


async def test_execute_awaits_injected_strategy_service_exactly_once() -> None:
    proposals = (bid(),)
    port = _FakeBidPort({_WORKFLOW_ID: proposals})
    spy = _RecordingTradingStrategyExecutionService(
        delegate=build_trading_strategy_execution_service(bid_port=_as_bid_port(port))
    )
    service = TradingStrategyProposalHandoffService(trading_strategy_service=spy)

    handoff = await service.execute(**_valid_kwargs())  # type: ignore[arg-type]

    assert spy.execute_calls == 1
    assert len(port.calls) == 1
    assert handoff.bid_proposals is proposals


async def test_independent_workflows_return_independent_handoffs() -> None:
    first_risk = _risk_assessment(assessment_id="assessment-1")
    second_risk = _risk_assessment(assessment_id="assessment-2", risk_score=Decimal("0.9"))
    first_success = _success(value_mw=3.25, price="45.00")
    second_success = _success(value_mw=7.5, price="80.00")
    first_proposals = (bid(bid_id="bid-1"),)
    second_proposals = (bid(bid_id="bid-2"), bid(bid_id="bid-3"))
    port = _FakeBidPort({_WORKFLOW_ID: first_proposals, _OTHER_WORKFLOW_ID: second_proposals})
    service = _service(port)

    second = await service.execute(
        workflow_id=_OTHER_WORKFLOW_ID,
        portfolio_id="portfolio-2",
        delivery_date=date(2026, 10, 3),
        risk_assessment=second_risk,
        forecasting_success=second_success,
        generation_availability=(availability(asset_id="asset-2"),),
        regulatory_constraints=(constraint(constraint_id="constraint-2"),),
    )
    first = await service.execute(
        workflow_id=_WORKFLOW_ID,
        portfolio_id="portfolio-1",
        delivery_date=date(2026, 10, 2),
        risk_assessment=first_risk,
        forecasting_success=first_success,
        generation_availability=(availability(asset_id="asset-1"),),
        regulatory_constraints=(constraint(constraint_id="constraint-1"),),
    )

    assert first is not second
    assert len(port.calls) == 2
    assert second.workflow_id == _OTHER_WORKFLOW_ID
    assert second.portfolio_id == "portfolio-2"
    assert second.delivery_date == date(2026, 10, 3)
    assert second.risk_assessment is second_risk
    assert second.forecasting_success is second_success
    assert second.bid_proposals is second_proposals
    assert first.workflow_id == _WORKFLOW_ID
    assert first.portfolio_id == "portfolio-1"
    assert first.delivery_date == date(2026, 10, 2)
    assert first.risk_assessment is first_risk
    assert first.forecasting_success is first_success
    assert first.bid_proposals is first_proposals
