"""Application-owned Trading Strategy proposal handoff execution.

This module invokes the already-published Trading Strategy execution
service with explicit caller-supplied canonical inputs and places the
returned bid proposals, beside the caller-supplied forecasting result and
risk assessment, into the already-published Risk & Bid proposal handoff
record.

Ownership:

* Application: owns ``TradingStrategyProposalHandoffService``.
* Injected service: ``TradingStrategyExecutionService`` owns bid proposal
  request assembly and Trading Strategy agent delegation.
* Existing contract: ``RiskAndBidProposalHandoff`` owns structural
  validation of the handoff fields.
* Callers: supply workflow identity, portfolio identity, delivery date, the
  already-obtained ``RiskAssessment`` and ``ForecastingSuccess``, and the
  already-canonical generation and regulatory inputs. The service does not
  read forecasts, run a risk assessment, or coordinate Phase 4.
* Graph runtime, workflow context, persistence, market submission, retry,
  fallback, and API composition remain deferred.

The service awaits the injected execution service exactly once, constructs
exactly one handoff from the original inputs and the exact returned
proposal tuple, and returns that handoff unchanged. The handoff is a
proposal result, not an authorized trading decision: it carries no
approval, eligibility, submission, or settlement state. Failures propagate
naturally; no substitute proposal or partial handoff is fabricated. It
does not inherit a base class and does not change ``WorkflowState``.
"""

from datetime import date

from energy_trading.application.orchestration.forecasting_success import ForecastingSuccess
from energy_trading.application.orchestration.risk_and_bid_proposal_handoff import (
    RiskAndBidProposalHandoff,
)
from energy_trading.application.orchestration.trading_strategy_execution import (
    TradingStrategyExecutionService,
)
from energy_trading.domain.models.observations import GenerationAvailabilityRecord
from energy_trading.domain.models.regulatory import RegulatoryConstraint
from energy_trading.domain.models.trading import RiskAssessment
from energy_trading.domain.value_objects.quantities import EntityId


class TradingStrategyProposalHandoffService:
    """Framework-neutral Trading Strategy proposal-to-handoff composition.

    The constructor dependency is the published Trading Strategy execution
    service. ``execute`` delegates once, then wraps the exact proposal tuple
    in one ``RiskAndBidProposalHandoff``.
    """

    def __init__(
        self,
        *,
        trading_strategy_service: TradingStrategyExecutionService,
    ) -> None:
        self._trading_strategy_service = trading_strategy_service

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
    ) -> RiskAndBidProposalHandoff:
        """Return the proposal handoff for the supplied canonical inputs.

        Failures from the execution service or handoff validation propagate
        unchanged.
        """

        bid_proposals = await self._trading_strategy_service.execute(
            workflow_id=workflow_id,
            portfolio_id=portfolio_id,
            delivery_date=delivery_date,
            risk_assessment=risk_assessment,
            forecasting_success=forecasting_success,
            generation_availability=generation_availability,
            regulatory_constraints=regulatory_constraints,
        )
        return RiskAndBidProposalHandoff(
            workflow_id=workflow_id,
            portfolio_id=portfolio_id,
            delivery_date=delivery_date,
            forecasting_success=forecasting_success,
            risk_assessment=risk_assessment,
            bid_proposals=bid_proposals,
        )
