"""Application-owned Risk & Bid proposal handoff record.

These are contract-level tests over normally validated canonical fixtures.
They do not prove any risk methodology, bid profitability, regulatory
compliance, or exchange acceptance: the record only carries values that a
future coordinator already obtained.
"""

from __future__ import annotations

import dataclasses
import inspect
from datetime import date, datetime
from decimal import Decimal
from typing import get_type_hints

import pytest

from energy_trading.application.orchestration.forecasting_success import ForecastingSuccess
from energy_trading.application.orchestration.risk_and_bid_proposal_handoff import (
    RiskAndBidProposalHandoff,
)
from energy_trading.domain.models import (
    LoadForecastPoint,
    MarketBid,
    PriceForecastPoint,
    RiskAssessment,
)
from tests.unit.domain._factories import amd_price, availability, bid, constraint, utc

_FIELD_NAMES = (
    "workflow_id",
    "portfolio_id",
    "delivery_date",
    "forecasting_success",
    "risk_assessment",
    "bid_proposals",
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


def _risk_assessment(assessment_id: str = "assessment-1") -> RiskAssessment:
    return RiskAssessment.model_validate(
        {
            "assessment_id": assessment_id,
            "assessed_at": utc(hour=9),
            "delivery_timestamp": utc(day=2, hour=16),
            "risk_score": Decimal("0.4"),
        }
    )


def _handoff(**overrides: object) -> RiskAndBidProposalHandoff:
    values: dict[str, object] = {
        "workflow_id": "workflow-handoff-1",
        "portfolio_id": "portfolio-1",
        "delivery_date": date(2026, 10, 2),
        "forecasting_success": _success(),
        "risk_assessment": _risk_assessment(),
        "bid_proposals": (bid(),),
    }
    values.update(overrides)
    return RiskAndBidProposalHandoff(**values)  # type: ignore[arg-type]


def test_handoff_declares_exact_canonical_field_types() -> None:
    hints = get_type_hints(RiskAndBidProposalHandoff)
    assert tuple(hints) == _FIELD_NAMES
    assert hints["workflow_id"] is str
    assert hints["portfolio_id"] is str
    assert hints["delivery_date"] is date
    assert hints["forecasting_success"] is ForecastingSuccess
    assert hints["risk_assessment"] is RiskAssessment
    assert hints["bid_proposals"] == tuple[MarketBid, ...]
    assert isinstance(_handoff(), RiskAndBidProposalHandoff)


def test_handoff_is_frozen() -> None:
    handoff = _handoff()
    with pytest.raises(dataclasses.FrozenInstanceError):
        handoff.bid_proposals = ()  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        handoff.workflow_id = "workflow-other"  # type: ignore[misc]


def test_handoff_uses_slots() -> None:
    handoff = _handoff()
    assert RiskAndBidProposalHandoff.__slots__ == _FIELD_NAMES
    assert not hasattr(handoff, "__dict__")


def test_handoff_fields_are_keyword_only_without_defaults() -> None:
    fields = dataclasses.fields(RiskAndBidProposalHandoff)
    assert tuple(field.name for field in fields) == _FIELD_NAMES
    for field in fields:
        assert field.kw_only is True
        assert field.default is dataclasses.MISSING
        assert field.default_factory is dataclasses.MISSING
    signature = inspect.signature(RiskAndBidProposalHandoff)
    for parameter in signature.parameters.values():
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty
    with pytest.raises(TypeError):
        RiskAndBidProposalHandoff()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        RiskAndBidProposalHandoff(  # type: ignore[call-arg]
            "workflow-handoff-1",
            "portfolio-1",
            date(2026, 10, 2),
            _success(),
            _risk_assessment(),
            (),
        )


@pytest.mark.parametrize("missing", _FIELD_NAMES)
def test_handoff_requires_every_field(missing: str) -> None:
    values: dict[str, object] = {
        "workflow_id": "workflow-handoff-1",
        "portfolio_id": "portfolio-1",
        "delivery_date": date(2026, 10, 2),
        "forecasting_success": _success(),
        "risk_assessment": _risk_assessment(),
        "bid_proposals": (),
    }
    del values[missing]
    with pytest.raises(TypeError):
        RiskAndBidProposalHandoff(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field_name", "value", "error_type"),
    [
        ("workflow_id", 7, TypeError),
        ("workflow_id", None, TypeError),
        ("workflow_id", "", ValueError),
        ("workflow_id", "   ", ValueError),
        ("portfolio_id", 7, TypeError),
        ("portfolio_id", None, TypeError),
        ("portfolio_id", "", ValueError),
        ("portfolio_id", "  ", ValueError),
        ("delivery_date", datetime(2026, 10, 2, 0, 0), TypeError),
        ("delivery_date", "2026-10-02", TypeError),
        ("delivery_date", None, TypeError),
        ("forecasting_success", object(), TypeError),
        ("forecasting_success", None, TypeError),
        ("forecasting_success", {"consumer_load_forecast": ()}, TypeError),
        ("risk_assessment", object(), TypeError),
        ("risk_assessment", None, TypeError),
        ("risk_assessment", {"assessment_id": "assessment-1"}, TypeError),
        ("bid_proposals", [], TypeError),
        ("bid_proposals", None, TypeError),
        ("bid_proposals", frozenset(), TypeError),
        ("bid_proposals", (object(),), TypeError),
        ("bid_proposals", (availability(),), TypeError),
        ("bid_proposals", (constraint(),), TypeError),
        ("bid_proposals", ({"bid_id": "bid-1"},), TypeError),
    ],
)
def test_handoff_fails_closed_on_wrong_input_shapes(
    field_name: str,
    value: object,
    error_type: type[Exception],
) -> None:
    with pytest.raises(error_type):
        _handoff(**{field_name: value})


def test_handoff_rejects_mutable_list_of_valid_bids() -> None:
    with pytest.raises(TypeError, match="bid_proposals must be an immutable tuple"):
        _handoff(bid_proposals=[bid()])


def test_handoff_rejects_foreign_element_mixed_with_valid_bids() -> None:
    with pytest.raises(TypeError, match="bid_proposals must contain MarketBid values"):
        _handoff(bid_proposals=(bid(), _risk_assessment()))


def test_handoff_rejects_risk_assessment_in_forecast_slot_and_vice_versa() -> None:
    with pytest.raises(TypeError, match="forecasting_success"):
        _handoff(forecasting_success=_risk_assessment())
    with pytest.raises(TypeError, match="risk_assessment"):
        _handoff(risk_assessment=_success())


def test_handoff_preserves_forecasting_success_by_identity() -> None:
    success = _success()
    handoff = _handoff(forecasting_success=success)
    assert handoff.forecasting_success is success
    assert handoff.forecasting_success.consumer_load_forecast is success.consumer_load_forecast
    assert handoff.forecasting_success.dam_price_forecast is success.dam_price_forecast


def test_handoff_preserves_risk_assessment_by_identity() -> None:
    assessment = _risk_assessment()
    handoff = _handoff(risk_assessment=assessment)
    assert handoff.risk_assessment is assessment


def test_handoff_preserves_proposal_tuple_and_bid_instances_in_order() -> None:
    later = bid(bid_id="bid-2", delivery_timestamp=utc(hour=17))
    earlier = bid(bid_id="bid-1", delivery_timestamp=utc(hour=11))
    duplicate = bid(bid_id="bid-2", delivery_timestamp=utc(hour=17))
    proposals = (later, earlier, duplicate)
    handoff = _handoff(bid_proposals=proposals)
    assert handoff.bid_proposals is proposals
    assert len(handoff.bid_proposals) == 3
    assert handoff.bid_proposals[0] is later
    assert handoff.bid_proposals[1] is earlier
    assert handoff.bid_proposals[2] is duplicate


def test_handoff_preserves_explicit_identity_and_delivery_date_without_normalizing() -> None:
    delivery_date = date(2026, 10, 2)
    workflow_id = " workflow-handoff-7 "
    portfolio_id = " portfolio-9 "
    handoff = _handoff(
        workflow_id=workflow_id,
        portfolio_id=portfolio_id,
        delivery_date=delivery_date,
    )
    assert handoff.workflow_id is workflow_id
    assert handoff.portfolio_id is portfolio_id
    assert handoff.delivery_date is delivery_date


def test_handoff_represents_empty_proposal_tuple_without_generating_bids() -> None:
    proposals: tuple[MarketBid, ...] = ()
    success = ForecastingSuccess(consumer_load_forecast=(), dam_price_forecast=())
    handoff = _handoff(bid_proposals=proposals, forecasting_success=success)
    assert handoff.bid_proposals is proposals
    assert handoff.bid_proposals == ()
    assert handoff.forecasting_success is success


def test_independent_handoffs_share_no_mutable_state() -> None:
    first_bids = (bid(bid_id="bid-a"),)
    second_bids = (bid(bid_id="bid-b"), bid(bid_id="bid-c"))
    first = _handoff(workflow_id="workflow-a", bid_proposals=first_bids)
    second = _handoff(
        workflow_id="workflow-b",
        risk_assessment=_risk_assessment("assessment-2"),
        bid_proposals=second_bids,
    )
    assert first.workflow_id == "workflow-a"
    assert second.workflow_id == "workflow-b"
    assert first.bid_proposals is first_bids
    assert second.bid_proposals is second_bids
    assert first.risk_assessment is not second.risk_assessment
    assert first.forecasting_success is not second.forecasting_success
    assert first != second


def test_handoff_does_not_modify_supplied_canonical_values() -> None:
    success = _success()
    assessment = _risk_assessment()
    proposal = bid()
    before = (
        success.consumer_load_forecast,
        success.dam_price_forecast,
        assessment.model_dump(),
        proposal.model_dump(),
    )
    handoff = _handoff(
        forecasting_success=success,
        risk_assessment=assessment,
        bid_proposals=(proposal,),
    )
    assert handoff.bid_proposals == (proposal,)
    assert (
        success.consumer_load_forecast,
        success.dam_price_forecast,
        assessment.model_dump(),
        proposal.model_dump(),
    ) == before


def test_handoff_carries_no_approval_eligibility_submission_or_settlement_state() -> None:
    handoff = _handoff()
    field_names = {field.name for field in dataclasses.fields(RiskAndBidProposalHandoff)}
    assert field_names == set(_FIELD_NAMES)
    public_members = {name for name in dir(handoff) if not name.startswith("_")}
    assert public_members == set(_FIELD_NAMES)
    for forbidden in (
        "approved",
        "is_approved",
        "is_trade_authorized",
        "authorized",
        "eligible",
        "is_eligible",
        "ready",
        "status",
        "submission_id",
        "exchange_acceptance_id",
        "settlement_status",
        "succeeded",
    ):
        assert not hasattr(handoff, forbidden), forbidden


def test_empty_proposals_do_not_imply_acceptance_or_success() -> None:
    empty = _handoff(bid_proposals=())
    non_empty = _handoff(bid_proposals=(bid(),))
    assert not hasattr(empty, "status")
    assert not hasattr(non_empty, "status")
    assert {field.name for field in dataclasses.fields(empty)} == {
        field.name for field in dataclasses.fields(non_empty)
    }
