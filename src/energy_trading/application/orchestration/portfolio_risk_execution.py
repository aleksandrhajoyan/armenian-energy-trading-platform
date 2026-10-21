"""Application-owned Portfolio & Risk forecast-to-assessment execution.

This module composes the already-published forecasting-success read
boundary with the Portfolio & Risk agent invocation contract into one
framework-neutral application use case.

Ownership:

* Application: owns ``PortfolioRiskExecutionService``.
* Injected ports: ``ForecastingSuccessReadPort`` and the shared generic
  ``AgentPort`` specialized to ``PortfolioRiskAssessmentRequest`` and
  ``RiskAssessment``.
* Callers: supply workflow identity, portfolio identity, delivery date, and
  the already-canonical generation, hydro, and regulatory inputs.
* Injected agent: owns delegation to the underlying assessment port. The
  quantitative assessment remains absent.
* Graph runtime, workflow context, persistence, retry, fallback, degraded
  mode, Trading Strategy, and API composition remain deferred.

The service reads exactly one forecasting success by exact workflow
identity, constructs exactly one assessment request from it, invokes the
agent exactly once, and returns the agent's assessment unchanged. Failures
propagate naturally; no substitute forecast or assessment is fabricated.
It does not inherit a base class and does not change ``WorkflowState``.
"""

from datetime import date

from energy_trading.application.agents.base import AgentPort
from energy_trading.application.orchestration.forecasting_success_read import (
    ForecastingSuccessReadPort,
)
from energy_trading.application.ports.portfolio_risk_assessment import (
    PortfolioRiskAssessmentRequest,
)
from energy_trading.domain.models.observations import GenerationAvailabilityRecord, HydroRecord
from energy_trading.domain.models.regulatory import RegulatoryConstraint
from energy_trading.domain.models.trading import RiskAssessment
from energy_trading.domain.value_objects.quantities import EntityId


class PortfolioRiskExecutionService:
    """Framework-neutral Phase 3-to-Phase 4 forecast-to-assessment composition.

    Constructor dependencies are the published forecasting-success read
    port and a Portfolio & Risk agent satisfying ``AgentPort`` structurally.
    ``execute`` reads, constructs, delegates, and returns the exact
    assessment.
    """

    def __init__(
        self,
        *,
        forecast_reader: ForecastingSuccessReadPort,
        risk_agent: AgentPort[PortfolioRiskAssessmentRequest, RiskAssessment],
    ) -> None:
        self._forecast_reader = forecast_reader
        self._risk_agent = risk_agent

    async def execute(
        self,
        *,
        workflow_id: str,
        portfolio_id: EntityId,
        delivery_date: date,
        generation_availability: tuple[GenerationAvailabilityRecord, ...],
        hydro_resources: tuple[HydroRecord, ...],
        regulatory_constraints: tuple[RegulatoryConstraint, ...],
    ) -> RiskAssessment:
        """Read the forecast for ``workflow_id`` and return the agent's assessment.

        Failures from the reader, request construction, or the agent
        propagate unchanged.
        """

        forecasting_success = await self._forecast_reader.get_success(workflow_id=workflow_id)
        request = PortfolioRiskAssessmentRequest(
            workflow_id=workflow_id,
            portfolio_id=portfolio_id,
            delivery_date=delivery_date,
            forecasting_success=forecasting_success,
            generation_availability=generation_availability,
            hydro_resources=hydro_resources,
            regulatory_constraints=regulatory_constraints,
        )
        return await self._risk_agent.run(request)
