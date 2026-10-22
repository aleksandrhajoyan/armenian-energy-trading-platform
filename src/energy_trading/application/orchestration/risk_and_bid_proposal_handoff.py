"""Application-owned Risk & Bid proposal handoff record.

``RiskAndBidProposalHandoff`` carries, for one workflow, the already-published
Phase 3 forecasting aggregate, the already-obtained canonical risk
assessment, and the already-generated canonical bid proposals as one
immutable data handoff for a future Risk & Bid proposal coordinator.

Ownership:

* Application: owns ``RiskAndBidProposalHandoff``.
* Existing contracts: ``ForecastingSuccess``, ``RiskAssessment``, and
  ``MarketBid`` are reused unchanged. This module does not define duplicate
  forecast, risk, or bid DTOs.
* Producers: a future coordinator supplies every value. This module does
  not read forecasts, run a risk assessment, generate proposals, or invoke
  any agent, execution service, or port.

The record is a data handoff only. A present ``RiskAssessment`` is not risk
approval, a present ``MarketBid`` is not submission eligibility, and an
empty proposal tuple is not risk acceptance, a successful trading decision,
or regulatory clearance. The record carries no approval, authorization,
readiness, eligibility, submission, exchange-acceptance, or settlement
state and infers none. Supplied objects and tuples are preserved exactly;
nothing is copied, sorted, filtered, deduplicated, aggregated, normalized,
or reconstructed, and no cross-object currency, horizon, delivery, or
identity-matching rule is imposed.
"""

from dataclasses import dataclass
from datetime import date

from energy_trading.application.orchestration.forecasting_success import ForecastingSuccess
from energy_trading.domain.models.trading import MarketBid, RiskAssessment
from energy_trading.domain.value_objects.quantities import EntityId


@dataclass(frozen=True, slots=True, kw_only=True)
class RiskAndBidProposalHandoff:
    """Immutable Risk & Bid proposal output record over canonical values.

    This is an application orchestration DTO, not a domain entity, not a
    workflow snapshot, and not a persistence record. ``workflow_id`` uses the
    published ``WorkflowState.workflow_id`` type. ``portfolio_id`` is the
    caller-supplied opaque portfolio identity. ``delivery_date`` is a
    calendar date without timezone or DAM interval inference.
    ``forecasting_success``, ``risk_assessment``, and ``bid_proposals`` are
    already-produced canonical results carried exactly as supplied.

    Construction fails closed on wrong types and blank identifiers. It does
    not strip, generate, default, or derive any value.
    """

    workflow_id: str
    portfolio_id: EntityId
    delivery_date: date
    forecasting_success: ForecastingSuccess
    risk_assessment: RiskAssessment
    bid_proposals: tuple[MarketBid, ...]

    def __post_init__(self) -> None:
        _require_non_blank("workflow_id", self.workflow_id)
        _require_non_blank("portfolio_id", self.portfolio_id)
        if type(self.delivery_date) is not date:
            msg = "delivery_date must be a date"
            raise TypeError(msg)
        _require_instance("forecasting_success", self.forecasting_success, ForecastingSuccess)
        _require_instance("risk_assessment", self.risk_assessment, RiskAssessment)
        _require_tuple_of("bid_proposals", self.bid_proposals, MarketBid)


def _require_non_blank(field_name: str, value: object) -> None:
    if not isinstance(value, str):
        msg = f"{field_name} must be a string"
        raise TypeError(msg)
    if not value.strip():
        msg = f"{field_name} must be a non-empty string"
        raise ValueError(msg)


def _require_instance(field_name: str, value: object, item_type: type[object]) -> None:
    if not isinstance(value, item_type):
        msg = f"{field_name} must be a {item_type.__name__}"
        raise TypeError(msg)


def _require_tuple_of(field_name: str, value: object, item_type: type[object]) -> None:
    if not isinstance(value, tuple):
        msg = f"{field_name} must be an immutable tuple"
        raise TypeError(msg)
    if not all(isinstance(item, item_type) for item in value):
        msg = f"{field_name} must contain {item_type.__name__} values"
        raise TypeError(msg)
