"""Portfolio & Risk Agent application boundary.

This module is the ninth concrete application agent. It consumes the
already-published ``PortfolioRiskAssessmentRequest``, calls the injected
application assessment port once, and returns the exact canonical
``RiskAssessment``. Risk formulas, exposure, VaR, scenarios, thresholds,
and completeness rules never enter here.

Ownership:

* Application: owns the concrete agent.
* Injected ``PortfolioRiskAssessmentPort``: supplies the already-canonical
  assessment for the published request.
* Future assessment implementation: structurally implements that port. No
  concrete implementation exists yet.
* Callers: obtain forecasts and assemble the request. The agent does not
  read forecasts, inspect workflow state, or resolve a workflow plan.
* LangGraph, workflow context, persistence, retry, fallback, API composition,
  and Phase-4 routing remain deferred.

The agent satisfies ``AgentPort`` structurally. It does not inherit a base
class and is not registered in a factory. It does not calculate risk.
"""

from energy_trading.application.agents.base import AgentName
from energy_trading.application.ports.portfolio_risk_assessment import (
    PortfolioRiskAssessmentPort,
    PortfolioRiskAssessmentRequest,
)
from energy_trading.domain.models.trading import RiskAssessment


class PortfolioRiskAgent:
    """Thin application agent over the Portfolio & Risk assessment port.

    ``run`` awaits ``PortfolioRiskAssessmentPort.assess`` exactly once with
    the supplied request and returns that assessment unchanged. It does not
    reconstruct the assessment, default a risk result, translate errors,
    retry, or call an LLM.
    """

    def __init__(self, *, assessment_port: PortfolioRiskAssessmentPort) -> None:
        self._assessment_port = assessment_port

    @property
    def name(self) -> AgentName:
        return AgentName.PORTFOLIO_AND_RISK

    async def run(self, request: PortfolioRiskAssessmentRequest) -> RiskAssessment:
        return await self._assessment_port.assess(request=request)
