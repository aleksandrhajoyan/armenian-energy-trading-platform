"""Application-owned Trading Strategy bid proposal boundary.

A future Trading Strategy implementation structurally implements this
protocol and returns already-canonical ``MarketBid`` proposals. This module
is the first typed application-facing seam a future Trading Strategy Agent
or use case may use to request bid proposals.

Ownership:

* Application: owns ``TradingStrategyBidPort`` and
  ``TradingStrategyBidRequest``.
* Existing contracts: ``RiskAssessment``, ``MarketBid``,
  ``GenerationAvailabilityRecord``, ``RegulatoryConstraint``, and
  ``ForecastingSuccess`` are reused unchanged. This module does not define
  duplicate bid, risk, or forecast-point DTOs.
* Inputs: the request accepts an already-obtained ``RiskAssessment`` and an
  already-obtained ``ForecastingSuccess``. It does not retrieve forecasts,
  run a risk assessment, depend on ``WorkflowState``, or own a workflow
  context.
* Future implementation: owns proposal generation and every verified
  business eligibility rule. There is no concrete implementation, bid MW or
  price calculation, interval, side, or product selection, risk threshold,
  unit or currency conversion, or market submission in this module.

Bid proposal is not bid authorization, submission, clearing, or settlement.
The request does not assert that risk is complete or approved, and it does
not declare that portfolio positions or commercial constraints are modeled.
Empty tuples remain representable and never mean that inputs are sufficient
for trading. Supplied objects and tuples are preserved exactly; nothing is
sorted, aggregated, normalized, or reconstructed, and no cross-object
currency, horizon, or market-interval rule is imposed.
"""

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from energy_trading.application.orchestration.forecasting_success import ForecastingSuccess
from energy_trading.domain.models.observations import GenerationAvailabilityRecord
from energy_trading.domain.models.regulatory import RegulatoryConstraint
from energy_trading.domain.models.trading import MarketBid, RiskAssessment
from energy_trading.domain.value_objects.quantities import EntityId


@dataclass(frozen=True, slots=True, kw_only=True)
class TradingStrategyBidRequest:
    """Immutable bid proposal request over explicit canonical inputs.

    This is an application DTO, not a domain entity, not a workflow
    snapshot, and not a persistence record. ``workflow_id`` uses the
    published ``WorkflowState.workflow_id`` type. ``portfolio_id`` is the
    caller-supplied opaque portfolio identity. ``delivery_date`` is a
    calendar date without timezone or DAM interval inference.
    ``risk_assessment`` and ``forecasting_success`` are already-obtained
    canonical results. The remaining tuples carry existing canonical records
    exactly as supplied.

    Construction fails closed on wrong types and blank identifiers. It does
    not strip, generate, default, or derive any value.
    """

    workflow_id: str
    portfolio_id: EntityId
    delivery_date: date
    risk_assessment: RiskAssessment
    forecasting_success: ForecastingSuccess
    generation_availability: tuple[GenerationAvailabilityRecord, ...]
    regulatory_constraints: tuple[RegulatoryConstraint, ...]

    def __post_init__(self) -> None:
        _require_non_blank("workflow_id", self.workflow_id)
        _require_non_blank("portfolio_id", self.portfolio_id)
        if type(self.delivery_date) is not date:
            msg = "delivery_date must be a date"
            raise TypeError(msg)
        _require_instance("risk_assessment", self.risk_assessment, RiskAssessment)
        _require_instance("forecasting_success", self.forecasting_success, ForecastingSuccess)
        _require_tuple_of(
            "generation_availability",
            self.generation_availability,
            GenerationAvailabilityRecord,
        )
        _require_tuple_of(
            "regulatory_constraints",
            self.regulatory_constraints,
            RegulatoryConstraint,
        )


class TradingStrategyBidPort(Protocol):
    """Application-owned port for future Trading Strategy bid proposals.

    Implementations satisfy this protocol structurally. The application
    depends on the protocol, never on a concrete bid algorithm.

    ``propose_bids`` accepts only ``TradingStrategyBidRequest`` and returns
    a tuple of existing canonical ``MarketBid`` proposals. Tuple order is
    the implementation's own and carries no contract meaning. An empty
    tuple is representable but is not regulatory approval, risk acceptance,
    or a successful trading decision. The port does not decide whether bids
    may be submitted, accepted, or settled. Conforming implementations must
    not ask an LLM to invent bid MW or prices. Retries and fallback belong
    to later orchestration.
    """

    async def propose_bids(self, *, request: TradingStrategyBidRequest) -> tuple[MarketBid, ...]:
        """Return canonical bid proposals for one request."""
        ...


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
