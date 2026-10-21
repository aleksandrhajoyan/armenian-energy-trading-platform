"""Application-owned Portfolio & Risk assessment boundary.

A future Portfolio & Risk implementation structurally implements this
protocol and returns an already-canonical ``RiskAssessment``. This module is
the first typed application-facing seam a future Portfolio & Risk Agent or
use case may use to request a risk assessment.

Ownership:

* Application: owns ``PortfolioRiskAssessmentPort`` and
  ``PortfolioRiskAssessmentRequest``.
* Existing contracts: ``RiskAssessment``, ``GenerationAvailabilityRecord``,
  ``HydroRecord``, ``RegulatoryConstraint``, and ``ForecastingSuccess`` are
  reused unchanged. This module does not define duplicate forecast-point or
  risk DTOs.
* Forecast retrieval: ``ForecastingSuccessReadPort`` remains the canonical
  way to obtain a completed forecasting result by workflow identity. This
  request accepts an already-obtained ``ForecastingSuccess``; it does not
  read forecasts, depend on ``WorkflowState``, or own a workflow context.
* Future implementation: owns the quantitative assessment. There is no
  concrete implementation, risk formula, VaR or exposure calculation, unit
  or currency conversion, or bid construction in this module.

The request represents currently available typed inputs only. It is not a
declaration that portfolio positions, commercial constraints, or risk
policy are modeled, and it does not certify that enough inputs exist to
calculate or approve portfolio risk. Empty tuples remain representable and
never mean that risk is zero, complete, or acceptable. Supplied objects and
tuples are preserved exactly; nothing is sorted, aggregated, normalized, or
reconstructed, and no matching-horizon, currency, or market-interval rule is
imposed.
"""

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from energy_trading.application.orchestration.forecasting_success import ForecastingSuccess
from energy_trading.domain.models.observations import GenerationAvailabilityRecord, HydroRecord
from energy_trading.domain.models.regulatory import RegulatoryConstraint
from energy_trading.domain.models.trading import RiskAssessment
from energy_trading.domain.value_objects.quantities import EntityId


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioRiskAssessmentRequest:
    """Immutable assessment request over explicit canonical inputs.

    This is an application DTO, not a domain entity, not a workflow
    snapshot, and not a persistence record. ``workflow_id`` uses the
    published ``WorkflowState.workflow_id`` type. ``portfolio_id`` is the
    caller-supplied opaque portfolio identity. ``delivery_date`` is a
    calendar date without timezone or DAM interval inference.
    ``forecasting_success`` is the already-obtained Phase 3 aggregate. The
    remaining tuples carry existing canonical records exactly as supplied.

    Construction fails closed on wrong types and blank identifiers. It does
    not strip, generate, default, or derive any value.
    """

    workflow_id: str
    portfolio_id: EntityId
    delivery_date: date
    forecasting_success: ForecastingSuccess
    generation_availability: tuple[GenerationAvailabilityRecord, ...]
    hydro_resources: tuple[HydroRecord, ...]
    regulatory_constraints: tuple[RegulatoryConstraint, ...]

    def __post_init__(self) -> None:
        _require_non_blank("workflow_id", self.workflow_id)
        _require_non_blank("portfolio_id", self.portfolio_id)
        if type(self.delivery_date) is not date:
            msg = "delivery_date must be a date"
            raise TypeError(msg)
        _require_instance("forecasting_success", self.forecasting_success, ForecastingSuccess)
        _require_tuple_of(
            "generation_availability",
            self.generation_availability,
            GenerationAvailabilityRecord,
        )
        _require_tuple_of("hydro_resources", self.hydro_resources, HydroRecord)
        _require_tuple_of(
            "regulatory_constraints",
            self.regulatory_constraints,
            RegulatoryConstraint,
        )


class PortfolioRiskAssessmentPort(Protocol):
    """Application-owned port for a future Portfolio & Risk assessment.

    Implementations satisfy this protocol structurally. The application
    depends on the protocol, never on a concrete risk engine.

    ``assess`` accepts only ``PortfolioRiskAssessmentRequest`` and returns
    the existing canonical ``RiskAssessment``. Conforming implementations
    must not fabricate a "risk OK" result when inputs are insufficient and
    must not ask an LLM to compute exposure, VaR, or MW figures. Retries and
    fallback belong to later orchestration.
    """

    async def assess(self, *, request: PortfolioRiskAssessmentRequest) -> RiskAssessment:
        """Return the canonical risk assessment for one request."""
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
