"""Outer Phase 3 forecasting workflow-step object composition.

This module wires a caller-supplied application workflow-context port and a
caller-supplied application execution port into the already-published
forecasting workflow step. It does not construct agents, executors, model
ports, context storage, or graph objects, and it does not invoke the step.

Ownership:

* API composition root: owns ``build_forecasting_workflow_step``.
* Injected: ``ForecastingWorkflowContextPort``.
* Injected: ``ForecastingExecutionPort``.
* Application: owns ``ForecastingWorkflowStep``.
* Model choice, executor construction, context implementation, graph
  routing, and HTTP routes remain deferred or owned elsewhere.

The builder constructs one object only. It does not call application runtime
methods.
"""

from energy_trading.application.orchestration.forecasting_context import (
    ForecastingWorkflowContextPort,
)
from energy_trading.application.orchestration.forecasting_execution import (
    ForecastingExecutionPort,
)
from energy_trading.application.orchestration.forecasting_workflow import (
    ForecastingWorkflowStep,
)


def build_forecasting_workflow_step(
    *,
    context: ForecastingWorkflowContextPort,
    executor: ForecastingExecutionPort,
) -> ForecastingWorkflowStep:
    """Return a forecasting workflow step wired to the supplied ports.

    The two arguments are already-constructed application port
    implementations. This function does not discover, configure, or invoke
    them, and the caller keeps ownership of their lifetime.
    """

    return ForecastingWorkflowStep(context, executor)
