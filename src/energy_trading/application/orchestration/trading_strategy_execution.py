"""Application-owned Trading Strategy bid proposal execution.

This module assembles the already-published Trading Strategy bid proposal
request from explicit caller-supplied canonical inputs and delegates it to
the Trading Strategy agent invocation contract as one framework-neutral
application use case.

Ownership:

* Application: owns ``TradingStrategyExecutionService``.
* Injected port: the shared generic ``AgentPort`` specialized to
  ``TradingStrategyBidRequest`` and a tuple of ``MarketBid`` proposals.
* Callers: supply workflow identity, portfolio identity, delivery date, the
  already-obtained ``RiskAssessment`` and ``ForecastingSuccess``, and the
  already-canonical generation and regulatory inputs. The service does not
  read forecasts or run a risk assessment.
* Injected agent: owns delegation to the underlying bid proposal port. The
  bid proposal algorithm remains absent.
* Graph runtime, workflow context, persistence, market submission, retry,
  fallback, and API composition remain deferred.

The service constructs exactly one bid proposal request, invokes the agent
exactly once, and returns the agent's proposal tuple unchanged. A valid
risk assessment is not trading authorization, and an empty proposal tuple
is not approval. Failures propagate naturally; no substitute request or
proposal is fabricated. It does not inherit a base class and does not
change ``WorkflowState``.
"""

from datetime import date

from energy_trading.application.agents.base import AgentPort
from energy_trading.application.orchestration.forecasting_success import ForecastingSuccess
from energy_trading.application.ports.trading_strategy_bid import TradingStrategyBidRequest
from energy_trading.domain.models.observations import GenerationAvailabilityRecord
from energy_trading.domain.models.regulatory import RegulatoryConstraint
from energy_trading.domain.models.trading import MarketBid, RiskAssessment
from energy_trading.domain.value_objects.quantities import EntityId


class TradingStrategyExecutionService:
    """Framework-neutral Phase 4 request-to-proposal composition.

    The constructor dependency is a Trading Strategy agent satisfying
    ``AgentPort`` structurally. ``execute`` constructs, delegates, and
    returns the exact proposal tuple.
    """

    def __init__(
        self,
        *,
        bid_agent: AgentPort[TradingStrategyBidRequest, tuple[MarketBid, ...]],
    ) -> None:
        self._bid_agent = bid_agent

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
        """Return the agent's bid proposals for the supplied canonical inputs.

        Failures from request construction or the agent propagate unchanged.
        """

        request = TradingStrategyBidRequest(
            workflow_id=workflow_id,
            portfolio_id=portfolio_id,
            delivery_date=delivery_date,
            risk_assessment=risk_assessment,
            forecasting_success=forecasting_success,
            generation_availability=generation_availability,
            regulatory_constraints=regulatory_constraints,
        )
        return await self._bid_agent.run(request)
