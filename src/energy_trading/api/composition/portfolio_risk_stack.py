"""Outer Portfolio & Risk execution object composition.

This module wires a caller-supplied forecasting-success read port and a
caller-supplied Portfolio & Risk assessment port into the already-published
Portfolio & Risk agent and forecast-to-assessment execution service. It does
not choose a reader, choose an assessment implementation, load
configuration, or execute an assessment.

Ownership:

* API composition root: owns ``build_portfolio_risk_execution_service``.
* Injected: ``ForecastingSuccessReadPort``.
* Injected: ``PortfolioRiskAssessmentPort``.
* Application: owns ``PortfolioRiskAgent``, ``PortfolioRiskExecutionService``,
  and both port contracts.
* Concrete reader and assessment choice, numerical risk methodology, graph
  routing, and HTTP routes remain deferred.

The builder constructs objects only. It does not call application runtime
methods.
"""

from energy_trading.application.agents.portfolio_risk import PortfolioRiskAgent
from energy_trading.application.orchestration.forecasting_success_read import (
    ForecastingSuccessReadPort,
)
from energy_trading.application.orchestration.portfolio_risk_execution import (
    PortfolioRiskExecutionService,
)
from energy_trading.application.ports.portfolio_risk_assessment import (
    PortfolioRiskAssessmentPort,
)


def build_portfolio_risk_execution_service(
    *,
    forecast_reader: ForecastingSuccessReadPort,
    assessment_port: PortfolioRiskAssessmentPort,
) -> PortfolioRiskExecutionService:
    """Return a wired Portfolio & Risk execution service.

    The two arguments are already-constructed application port
    implementations. This function does not discover, select, configure, or
    invoke them, and the caller keeps ownership of their lifetime.
    """

    risk_agent = PortfolioRiskAgent(assessment_port=assessment_port)
    return PortfolioRiskExecutionService(
        forecast_reader=forecast_reader,
        risk_agent=risk_agent,
    )
