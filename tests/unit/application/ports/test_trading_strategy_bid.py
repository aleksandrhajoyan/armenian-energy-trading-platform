"""Application-owned Trading Strategy bid proposal request and Protocol.

These are contract-level tests against a test-only structural fake. They do
not prove any bid methodology: no concrete Trading Strategy implementation
exists, and nothing here submits a bid.
"""

from __future__ import annotations

import dataclasses
import inspect
from datetime import date, datetime
from decimal import Decimal
from typing import get_type_hints

import pytest

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.orchestration.forecasting_success import ForecastingSuccess
from energy_trading.application.ports.trading_strategy_bid import (
    TradingStrategyBidPort,
    TradingStrategyBidRequest,
)
from energy_trading.domain.models import (
    GenerationAvailabilityRecord,
    LoadForecastPoint,
    MarketBid,
    PriceForecastPoint,
    RegulatoryConstraint,
    RiskAssessment,
)
from tests.unit.domain._factories import amd_price, availability, bid, constraint, utc

_FIELD_NAMES = (
    "workflow_id",
    "portfolio_id",
    "delivery_date",
    "risk_assessment",
    "forecasting_success",
    "generation_availability",
    "regulatory_constraints",
)


class _StructuralTradingStrategyBidFake:
    """Test-only fake that structurally satisfies the bid proposal Protocol.

    Not a bid algorithm. Does not inherit a production base class. Returns
    the caller-prepared proposal tuple or raises the caller-prepared error.
    """

    def __init__(
        self,
        *,
        result: tuple[MarketBid, ...] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.received_requests: list[TradingStrategyBidRequest] = []

    async def propose_bids(self, *, request: TradingStrategyBidRequest) -> tuple[MarketBid, ...]:
        self.received_requests.append(request)
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


def _as_bid_port(fake: _StructuralTradingStrategyBidFake) -> TradingStrategyBidPort:
    """Application-shaped call site: the port type is the only accepted argument."""

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


def test_request_accepts_exact_published_canonical_input_types() -> None:
    hints = get_type_hints(TradingStrategyBidRequest)
    assert tuple(hints) == _FIELD_NAMES
    assert hints["workflow_id"] is str
    assert hints["portfolio_id"] is str
    assert hints["delivery_date"] is date
    assert hints["risk_assessment"] is RiskAssessment
    assert hints["forecasting_success"] is ForecastingSuccess
    assert hints["generation_availability"] == tuple[GenerationAvailabilityRecord, ...]
    assert hints["regulatory_constraints"] == tuple[RegulatoryConstraint, ...]
    request = _request()
    assert isinstance(request, TradingStrategyBidRequest)


def test_request_is_frozen() -> None:
    request = _request()
    with pytest.raises(dataclasses.FrozenInstanceError):
        request.workflow_id = "workflow-other"  # type: ignore[misc]


def test_request_uses_slots() -> None:
    request = _request()
    assert TradingStrategyBidRequest.__slots__ == _FIELD_NAMES
    assert not hasattr(request, "__dict__")


def test_request_fields_are_keyword_only_without_defaults() -> None:
    fields = dataclasses.fields(TradingStrategyBidRequest)
    assert tuple(field.name for field in fields) == _FIELD_NAMES
    for field in fields:
        assert field.kw_only is True
        assert field.default is dataclasses.MISSING
        assert field.default_factory is dataclasses.MISSING
    signature = inspect.signature(TradingStrategyBidRequest)
    for parameter in signature.parameters.values():
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty
    with pytest.raises(TypeError):
        TradingStrategyBidRequest()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        TradingStrategyBidRequest(  # type: ignore[call-arg]
            "workflow-bid-1",
            "portfolio-1",
            date(2026, 10, 2),
            _risk_assessment(),
            _success(),
            (),
            (),
        )


@pytest.mark.parametrize("missing", _FIELD_NAMES)
def test_request_requires_every_field(missing: str) -> None:
    values: dict[str, object] = {
        "workflow_id": "workflow-bid-1",
        "portfolio_id": "portfolio-1",
        "delivery_date": date(2026, 10, 2),
        "risk_assessment": _risk_assessment(),
        "forecasting_success": _success(),
        "generation_availability": (),
        "regulatory_constraints": (),
    }
    del values[missing]
    with pytest.raises(TypeError):
        TradingStrategyBidRequest(**values)  # type: ignore[arg-type]


def test_request_preserves_risk_assessment_by_identity() -> None:
    assessment = _risk_assessment()
    request = _request(risk_assessment=assessment)
    assert request.risk_assessment is assessment


def test_request_preserves_forecasting_success_by_identity() -> None:
    success = _success()
    request = _request(forecasting_success=success)
    assert request.forecasting_success is success
    assert request.forecasting_success.consumer_load_forecast is success.consumer_load_forecast
    assert request.forecasting_success.dam_price_forecast is success.dam_price_forecast


def test_request_preserves_canonical_input_tuples_unchanged() -> None:
    later = availability(asset_id="asset-2", timestamp=utc(hour=12))
    earlier = availability(asset_id="asset-1", timestamp=utc(hour=8))
    generation = (later, earlier)
    constraints = (constraint(constraint_id="constraint-2"), constraint())
    request = _request(
        generation_availability=generation,
        regulatory_constraints=constraints,
    )
    assert request.generation_availability is generation
    assert request.regulatory_constraints is constraints
    assert request.generation_availability[0] is later
    assert request.generation_availability[1] is earlier
    assert request.regulatory_constraints[0] is constraints[0]
    assert request.regulatory_constraints[1] is constraints[1]


def test_request_preserves_explicit_identity_and_delivery_date() -> None:
    delivery_date = date(2026, 10, 2)
    request = _request(
        workflow_id="workflow-bid-7",
        portfolio_id="portfolio-9",
        delivery_date=delivery_date,
    )
    assert request.workflow_id == "workflow-bid-7"
    assert request.portfolio_id == "portfolio-9"
    assert request.delivery_date is delivery_date


def test_request_does_not_normalize_identifiers() -> None:
    request = _request(workflow_id=" workflow-bid-1 ", portfolio_id=" portfolio-1 ")
    assert request.workflow_id == " workflow-bid-1 "
    assert request.portfolio_id == " portfolio-1 "


def test_request_represents_empty_canonical_input_tuples_without_generating_data() -> None:
    success = ForecastingSuccess(consumer_load_forecast=(), dam_price_forecast=())
    request = _request(
        forecasting_success=success,
        generation_availability=(),
        regulatory_constraints=(),
    )
    assert request.forecasting_success is success
    assert request.forecasting_success.consumer_load_forecast == ()
    assert request.forecasting_success.dam_price_forecast == ()
    assert request.generation_availability == ()
    assert request.regulatory_constraints == ()


@pytest.mark.parametrize(
    ("field_name", "value", "error_type"),
    [
        ("workflow_id", 7, TypeError),
        ("workflow_id", None, TypeError),
        ("workflow_id", "", ValueError),
        ("workflow_id", "   ", ValueError),
        ("portfolio_id", None, TypeError),
        ("portfolio_id", "", ValueError),
        ("portfolio_id", "  ", ValueError),
        ("delivery_date", datetime(2026, 10, 2, 0, 0), TypeError),
        ("delivery_date", "2026-10-02", TypeError),
        ("risk_assessment", object(), TypeError),
        ("risk_assessment", None, TypeError),
        ("risk_assessment", {"assessment_id": "assessment-1"}, TypeError),
        ("forecasting_success", object(), TypeError),
        ("forecasting_success", None, TypeError),
        ("generation_availability", [], TypeError),
        ("generation_availability", (object(),), TypeError),
        ("generation_availability", (constraint(),), TypeError),
        ("regulatory_constraints", [], TypeError),
        ("regulatory_constraints", (object(),), TypeError),
        ("regulatory_constraints", (availability(),), TypeError),
    ],
)
def test_request_fails_closed_on_wrong_input_shapes(
    field_name: str,
    value: object,
    error_type: type[Exception],
) -> None:
    with pytest.raises(error_type):
        _request(**{field_name: value})


def test_bid_port_is_nongeneric_typing_protocol() -> None:
    assert [base.__name__ for base in TradingStrategyBidPort.__bases__] == ["Protocol"]
    assert vars(TradingStrategyBidPort)["_is_protocol"] is True
    assert vars(TradingStrategyBidPort)["__parameters__"] == ()
    assert TradingStrategyBidPort.__type_params__ == ()


def test_bid_port_exposes_keyword_only_async_propose_bids() -> None:
    defined_methods = {
        name
        for name, value in vars(TradingStrategyBidPort).items()
        if callable(value) and not name.startswith("_")
    }
    assert defined_methods == {"propose_bids"}
    assert inspect.iscoroutinefunction(TradingStrategyBidPort.propose_bids)
    signature = inspect.signature(TradingStrategyBidPort.propose_bids)
    assert tuple(signature.parameters) == ("self", "request")
    parameter = signature.parameters["request"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is inspect.Parameter.empty
    hints = get_type_hints(TradingStrategyBidPort.propose_bids)
    assert hints["request"] is TradingStrategyBidRequest
    assert hints["return"] == tuple[MarketBid, ...]


def test_structural_fake_does_not_inherit_the_port() -> None:
    assert TradingStrategyBidPort not in _StructuralTradingStrategyBidFake.__mro__
    assert _StructuralTradingStrategyBidFake.__bases__ == (object,)


async def test_fake_receives_exact_request_and_returns_exact_proposals() -> None:
    first = bid(bid_id="bid-1")
    second = bid(bid_id="bid-2", delivery_timestamp=utc(hour=17))
    proposals = (first, second)
    request = _request()
    fake = _StructuralTradingStrategyBidFake(result=proposals)
    port = _as_bid_port(fake)
    assert inspect.iscoroutinefunction(port.propose_bids)
    result = await port.propose_bids(request=request)
    assert result is proposals
    assert result[0] is first
    assert result[1] is second
    assert len(fake.received_requests) == 1
    assert fake.received_requests[0] is request


async def test_empty_proposal_tuple_passes_through_without_fabricated_bids() -> None:
    proposals: tuple[MarketBid, ...] = ()
    request = _request()
    fake = _StructuralTradingStrategyBidFake(result=proposals)
    port = _as_bid_port(fake)
    result = await port.propose_bids(request=request)
    assert result is proposals
    assert result == ()
    assert fake.received_requests == [request]


async def test_fake_application_error_propagates_unchanged() -> None:
    error = DependencyUnavailableError("Trading strategy backend is unavailable.")
    request = _request()
    fake = _StructuralTradingStrategyBidFake(error=error)
    port = _as_bid_port(fake)
    with pytest.raises(DependencyUnavailableError) as excinfo:
        await port.propose_bids(request=request)
    assert excinfo.value is error
    assert fake.received_requests == [request]
