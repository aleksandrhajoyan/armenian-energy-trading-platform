"""Outer Phase 3 forecasting stack object composition.

This module chains the two already-published forecasting composition
builders: caller-supplied model ports become a parallel forecasting executor
through ``build_parallel_forecasting_execution_service``, and that exact
executor plus a caller-supplied workflow-context port become a forecasting
workflow step through ``build_forecasting_workflow_step``. It does not choose
a model, choose a context implementation, load configuration, or invoke
forecasting.

Ownership:

* API composition root: owns ``build_forecasting_workflow_step_from_model_ports``.
* Injected: ``ConsumerLoadForecastModelPort``.
* Injected: ``DAMPriceForecastModelPort``.
* Injected: ``ForecastingWorkflowContextPort``.
* API composition root: the two delegated builders own all object construction.
* Concrete model choice, context implementation, graph routing, and HTTP
  routes remain deferred.

The builder delegates construction only. It does not call application runtime
methods.
"""

from energy_trading.api.composition.forecasting_execution import (
    build_parallel_forecasting_execution_service,
)
from energy_trading.api.composition.forecasting_workflow import build_forecasting_workflow_step
from energy_trading.application.orchestration.forecasting_context import (
    ForecastingWorkflowContextPort,
)
from energy_trading.application.orchestration.forecasting_workflow import (
    ForecastingWorkflowStep,
)
from energy_trading.application.ports.consumer_load_forecast_model import (
    ConsumerLoadForecastModelPort,
)
from energy_trading.application.ports.dam_price_forecast_model import DAMPriceForecastModelPort


def build_forecasting_workflow_step_from_model_ports(
    *,
    consumer_load_model: ConsumerLoadForecastModelPort,
    dam_price_model: DAMPriceForecastModelPort,
    context: ForecastingWorkflowContextPort,
) -> ForecastingWorkflowStep:
    """Return a forecasting workflow step wired from the supplied ports.

    The three arguments are already-constructed application port
    implementations. This function does not discover, select, configure, or
    invoke them, and the caller keeps ownership of their lifetime.
    """

    executor = build_parallel_forecasting_execution_service(
        consumer_load_model=consumer_load_model,
        dam_price_model=dam_price_model,
    )
    return build_forecasting_workflow_step(
        context=context,
        executor=executor,
    )
