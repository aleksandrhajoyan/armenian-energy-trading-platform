"""Trading Strategy proposal handoff composition reuses the published stack builder.

Bid-port fakes are test-only structural port implementations. Their proposal
tuples are caller-prepared fixtures, not results of a bid engine, and do not
establish commercial eligibility, regulatory approval, risk-methodology
accuracy, bid profitability, market acceptance, or trading readiness. A
returned handoff is a proposal result, not an approved, eligible, submitted,
or settled trading decision.
"""

from __future__ import annotations

import dataclasses
import inspect
from datetime import date, datetime

import pytest

from energy_trading.api.composition import (
    trading_strategy_proposal_handoff_stack,
    trading_strategy_stack,
)
from energy_trading.api.composition.trading_strategy_proposal_handoff_stack import (
    build_trading_strategy_proposal_handoff_service,
)
from energy_trading.application.agents.trading_strategy import TradingStrategyAgent
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
from energy_trading.domain.models.trading import BidSide, MarketBid, RiskAssessment
from tests.unit.domain._factories import amd_money, amd_price, availability, bid, constraint, utc

_WORKFLOW_ID = "workflow-bid-handoff-stack-1"
_PORTFOLIO_ID = "portfolio-bid-handoff-stack"
_DELIVERY_DATE = date(2026, 10, 2)

_HANDOFF_FIELDS = (
    "workflow_id",
    "portfolio_id",
    "delivery_date",
    "forecasting_success",
    "risk_assessment",
    "bid_proposals",
)


class _FakeBidPort:
    """Test-only bid port fake. Not a bid engine and not a market gateway."""

    def __init__(
        self,
        proposals: object = (),
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
        # Deliberately nonconforming proposals are confined to this test fake.
        return self.proposals  # type: ignore[return-value]


def _as_bid_port(port: _FakeBidPort) -> TradingStrategyBidPort:
    """Mypy-visible structural assignment to the published bid port."""

    return port


def _build(port: _FakeBidPort) -> TradingStrategyProposalHandoffService:
    return build_trading_strategy_proposal_handoff_service(bid_port=_as_bid_port(port))


class _BuilderSpy:
    """Records calls to the published Chunk 206 builder and delegates unchanged."""

    def __init__(self) -> None:
        self.received_bid_ports: list[TradingStrategyBidPort] = []
        self.returned: list[TradingStrategyExecutionService] = []

    def __call__(self, *, bid_port: TradingStrategyBidPort) -> TradingStrategyExecutionService:
        self.received_bid_ports.append(bid_port)
        service = trading_strategy_stack.build_trading_strategy_execution_service(bid_port=bid_port)
        self.returned.append(service)
        return service


class _RecordingHandoffService(TradingStrategyProposalHandoffService):
    instances: list[_RecordingHandoffService] = []
    execute_calls: int = 0

    def __init__(self, *, trading_strategy_service: TradingStrategyExecutionService) -> None:
        super().__init__(trading_strategy_service=trading_strategy_service)
        self.received_trading_strategy_service = trading_strategy_service
        type(self).instances.append(self)

    async def execute(self, **kwargs: object) -> RiskAndBidProposalHandoff:
        type(self).execute_calls += 1
        return await super().execute(**kwargs)  # type: ignore[arg-type]


class _RecordingTradingStrategyAgent(TradingStrategyAgent):
    run_calls: int = 0

    async def run(self, request: TradingStrategyBidRequest) -> tuple[MarketBid, ...]:
        type(self).run_calls += 1
        return await super().run(request)


class _RecordingExecutionService(TradingStrategyExecutionService):
    execute_calls: int = 0

    async def execute(self, **kwargs: object) -> tuple[MarketBid, ...]:
        type(self).execute_calls += 1
        return await super().execute(**kwargs)  # type: ignore[arg-type]


class _HandoffConstructionRecorder:
    """Counts handoff constructions while delegating to the published contract."""

    def __init__(self) -> None:
        self.constructed: list[RiskAndBidProposalHandoff] = []

    def __call__(self, **kwargs: object) -> RiskAndBidProposalHandoff:
        handoff = RiskAndBidProposalHandoff(**kwargs)  # type: ignore[arg-type]
        self.constructed.append(handoff)
        return handoff


@pytest.fixture
def builder_spy(monkeypatch: pytest.MonkeyPatch) -> _BuilderSpy:
    spy = _BuilderSpy()
    monkeypatch.setattr(
        trading_strategy_proposal_handoff_stack,
        "build_trading_strategy_execution_service",
        spy,
    )
    return spy


@pytest.fixture
def recording_handoff_service(monkeypatch: pytest.MonkeyPatch) -> None:
    _RecordingHandoffService.instances = []
    _RecordingHandoffService.execute_calls = 0
    monkeypatch.setattr(
        trading_strategy_proposal_handoff_stack,
        "TradingStrategyProposalHandoffService",
        _RecordingHandoffService,
    )


@pytest.fixture
def recording_inner_stack(monkeypatch: pytest.MonkeyPatch) -> None:
    _RecordingTradingStrategyAgent.run_calls = 0
    _RecordingExecutionService.execute_calls = 0
    monkeypatch.setattr(
        trading_strategy_stack, "TradingStrategyAgent", _RecordingTradingStrategyAgent
    )
    monkeypatch.setattr(
        trading_strategy_stack, "TradingStrategyExecutionService", _RecordingExecutionService
    )


@pytest.fixture
def handoff_recorder(monkeypatch: pytest.MonkeyPatch) -> _HandoffConstructionRecorder:
    recorder = _HandoffConstructionRecorder()
    monkeypatch.setattr(
        trading_strategy_proposal_handoff,
        "RiskAndBidProposalHandoff",
        recorder,
    )
    return recorder


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


def _assessment(assessment_id: str = "assessment-bid-handoff-stack-1") -> RiskAssessment:
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


def _valid_kwargs() -> dict[str, object]:
    return {
        "workflow_id": _WORKFLOW_ID,
        "portfolio_id": _PORTFOLIO_ID,
        "delivery_date": _DELIVERY_DATE,
        "risk_assessment": _assessment(),
        "forecasting_success": _success(),
        "generation_availability": (availability(), availability(asset_id="asset-2")),
        "regulatory_constraints": (constraint(),),
    }


# A. Public function contract


def test_builder_signature_is_one_required_keyword_only_bid_port() -> None:
    signature = inspect.signature(build_trading_strategy_proposal_handoff_service)
    assert tuple(signature.parameters) == ("bid_port",)
    parameter = signature.parameters["bid_port"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is inspect.Parameter.empty
    assert parameter.annotation is TradingStrategyBidPort
    assert signature.return_annotation is TradingStrategyProposalHandoffService
    assert not inspect.iscoroutinefunction(build_trading_strategy_proposal_handoff_service)


def test_builder_rejects_positional_missing_and_unknown_arguments() -> None:
    port = _FakeBidPort()
    with pytest.raises(TypeError):
        build_trading_strategy_proposal_handoff_service(port)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        build_trading_strategy_proposal_handoff_service()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        build_trading_strategy_proposal_handoff_service(
            bid_port=_as_bid_port(port),
            market_gateway=object(),  # type: ignore[call-arg]
        )
    assert port.calls == []


def test_builder_returns_the_published_handoff_service_type() -> None:
    service = _build(_FakeBidPort())
    assert type(service) is TradingStrategyProposalHandoffService
    assert TradingStrategyBidPort not in _FakeBidPort.__mro__
    assert _FakeBidPort.__bases__ == (object,)


# B. Exact construction


def test_builder_delegates_once_to_the_published_builder_and_wraps_its_service(
    builder_spy: _BuilderSpy,
    recording_handoff_service: None,
) -> None:
    port = _FakeBidPort()

    service = _build(port)

    assert len(builder_spy.received_bid_ports) == 1
    assert builder_spy.received_bid_ports[0] is port
    assert len(builder_spy.returned) == 1
    assert type(builder_spy.returned[0]) is TradingStrategyExecutionService
    assert len(_RecordingHandoffService.instances) == 1
    built = _RecordingHandoffService.instances[0]
    assert built.received_trading_strategy_service is builder_spy.returned[0]
    assert service is built


def test_repeated_builds_construct_new_object_graphs(
    builder_spy: _BuilderSpy,
    recording_handoff_service: None,
) -> None:
    port = _FakeBidPort()

    first = _build(port)
    second = _build(port)

    assert first is not second
    assert builder_spy.received_bid_ports == [port, port]
    first_inner, second_inner = builder_spy.returned
    assert first_inner is not second_inner
    first_built, second_built = _RecordingHandoffService.instances
    assert first_built.received_trading_strategy_service is first_inner
    assert second_built.received_trading_strategy_service is second_inner


# C. No eager execution


def test_builder_executes_nothing(
    recording_inner_stack: None,
    recording_handoff_service: None,
    handoff_recorder: _HandoffConstructionRecorder,
) -> None:
    proposals = (bid(),)
    port = _FakeBidPort(proposals)

    _build(port)

    assert port.calls == []
    assert port.proposals is proposals
    assert port.error is None
    assert _RecordingTradingStrategyAgent.run_calls == 0
    assert _RecordingExecutionService.execute_calls == 0
    assert _RecordingHandoffService.execute_calls == 0
    assert handoff_recorder.constructed == []


# D. Real assembled stack


async def test_assembled_stack_executes_through_real_service_agent_and_bid_port(
    recording_inner_stack: None,
) -> None:
    first = bid(bid_id="bid-1", side=BidSide.SELL, quantity_mw=5.0)
    second = bid(bid_id="bid-2", side=BidSide.BUY, quantity_mw=2.5, limit_price=amd_price("7.25"))
    proposals = (first, second)
    port = _FakeBidPort(proposals)
    service = _build(port)
    kwargs = _valid_kwargs()

    handoff = await service.execute(**kwargs)  # type: ignore[arg-type]

    assert _RecordingExecutionService.execute_calls == 1
    assert _RecordingTradingStrategyAgent.run_calls == 1
    assert len(port.calls) == 1
    request = port.calls[0]
    assert type(request) is TradingStrategyBidRequest
    assert request.workflow_id == _WORKFLOW_ID
    assert request.portfolio_id == _PORTFOLIO_ID
    assert request.delivery_date == _DELIVERY_DATE
    assert request.risk_assessment is kwargs["risk_assessment"]
    assert request.forecasting_success is kwargs["forecasting_success"]
    assert request.generation_availability is kwargs["generation_availability"]
    assert request.regulatory_constraints is kwargs["regulatory_constraints"]

    assert type(handoff) is RiskAndBidProposalHandoff
    assert handoff.workflow_id == _WORKFLOW_ID
    assert handoff.portfolio_id == _PORTFOLIO_ID
    assert handoff.delivery_date == _DELIVERY_DATE
    assert handoff.forecasting_success is kwargs["forecasting_success"]
    assert handoff.risk_assessment is kwargs["risk_assessment"]
    assert handoff.bid_proposals is proposals
    assert handoff.bid_proposals[0] is first
    assert handoff.bid_proposals[1] is second
    assert tuple(field.name for field in dataclasses.fields(handoff)) == _HANDOFF_FIELDS
    for token in ("approv", "eligib", "submit", "settle", "authoriz", "status"):
        assert not any(token in name for name in _HANDOFF_FIELDS), token


# E. Empty proposals


async def test_empty_proposal_tuple_is_carried_unchanged_without_default_bids() -> None:
    empty: tuple[MarketBid, ...] = ()
    port = _FakeBidPort(empty)

    handoff = await _build(port).execute(**_valid_kwargs())  # type: ignore[arg-type]

    assert handoff.bid_proposals is empty
    assert handoff.bid_proposals == ()
    assert len(port.calls) == 1


# F. Request-validation failures


@pytest.mark.parametrize(
    ("field_name", "value", "error_type", "message"),
    [
        ("workflow_id", "   ", ValueError, "workflow_id must be a non-empty string"),
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
async def test_request_validation_failure_propagates_before_the_bid_port(
    field_name: str,
    value: object,
    error_type: type[Exception],
    message: str,
    handoff_recorder: _HandoffConstructionRecorder,
) -> None:
    port = _FakeBidPort((bid(),))
    kwargs = _valid_kwargs()
    kwargs[field_name] = value

    with pytest.raises(error_type, match=message):
        await _build(port).execute(**kwargs)  # type: ignore[arg-type]

    assert port.calls == []
    assert handoff_recorder.constructed == []


# G. Port failures


@pytest.mark.parametrize(
    "error",
    [
        DependencyUnavailableError("Trading strategy bid proposal is unavailable."),
        RuntimeError("unexpected bid proposal failure"),
    ],
)
async def test_bid_port_failure_propagates_exact_instance_without_retry(
    error: Exception,
    handoff_recorder: _HandoffConstructionRecorder,
) -> None:
    port = _FakeBidPort(error=error)

    with pytest.raises(type(error)) as captured:
        await _build(port).execute(**_valid_kwargs())  # type: ignore[arg-type]

    assert captured.value is error
    assert len(port.calls) == 1
    assert handoff_recorder.constructed == []


# H. Invalid proposal output


@pytest.mark.parametrize(
    ("returned", "message"),
    [
        ([bid()], "bid_proposals must be an immutable tuple"),
        ((bid(), object()), "bid_proposals must contain MarketBid values"),
        ((availability(),), "bid_proposals must contain MarketBid values"),
    ],
)
async def test_nonconforming_proposals_are_rejected_by_the_handoff_contract(
    returned: object,
    message: str,
    handoff_recorder: _HandoffConstructionRecorder,
) -> None:
    port = _FakeBidPort(returned)

    with pytest.raises(TypeError, match=message):
        await _build(port).execute(**_valid_kwargs())  # type: ignore[arg-type]

    assert len(port.calls) == 1
    assert handoff_recorder.constructed == []


# I. Dependency isolation


async def test_independent_stacks_use_only_their_own_bid_ports() -> None:
    first_proposals = (bid(bid_id="bid-first"),)
    second_proposals = (bid(bid_id="bid-second"),)
    first_port = _FakeBidPort(first_proposals)
    second_port = _FakeBidPort(second_proposals)
    first = _build(first_port)
    second = _build(second_port)
    assert first is not second

    first_kwargs = _valid_kwargs()
    first_kwargs["risk_assessment"] = _assessment("assessment-first")
    first_handoff = await first.execute(**first_kwargs)  # type: ignore[arg-type]

    assert first_handoff.bid_proposals is first_proposals
    assert first_handoff.risk_assessment is first_kwargs["risk_assessment"]
    assert len(first_port.calls) == 1
    assert second_port.calls == []

    second_kwargs = _valid_kwargs()
    second_kwargs["risk_assessment"] = _assessment("assessment-second")
    second_handoff = await second.execute(**second_kwargs)  # type: ignore[arg-type]

    assert second_handoff is not first_handoff
    assert second_handoff.bid_proposals is second_proposals
    assert second_handoff.bid_proposals is not first_handoff.bid_proposals
    assert second_port.calls[0].risk_assessment is second_kwargs["risk_assessment"]
    assert len(second_port.calls) == 1
    assert len(first_port.calls) == 1


# J. Structural typing


def test_structural_fake_assembles_through_the_published_protocol() -> None:
    port: TradingStrategyBidPort = _FakeBidPort()
    service: TradingStrategyProposalHandoffService = (
        build_trading_strategy_proposal_handoff_service(bid_port=port)
    )
    assert isinstance(service, TradingStrategyProposalHandoffService)
