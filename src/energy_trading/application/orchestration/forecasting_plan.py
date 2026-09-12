"""Application-owned forecasting-phase plan contract.

``ForecastingPlan`` carries the two already-published Phase 3 forecast
model-request DTOs for one future forecasting-phase execution.

Ownership:

* Application: owns ``ForecastingPlan``.
* Existing request DTOs: reused as-is. This module does not shadow or
  replace them.
* Future execution: a separately reviewed module may execute the two
  requests. This module does not execute agents, does not choose
  concurrency, and does not encode Consumer → DAM ordering.

The plan does not equalize target timestamps or horizons, derive market
identity from consumer identity, or imply a dependency between the two
forecasts. Chunk 118 and Chunk 120 remain the semantic authorities for
their own request DTOs.
"""

from dataclasses import dataclass

from energy_trading.application.ports.consumer_load_forecast_model import (
    ConsumerLoadForecastModelRequest,
)
from energy_trading.application.ports.dam_price_forecast_model import (
    DAMPriceForecastModelRequest,
)


@dataclass(frozen=True, slots=True)
class ForecastingPlan:
    """Immutable plan of prepared Consumer Load and DAM Price requests.

    This is an application orchestration DTO, not ``WorkflowState``, not a
    domain contract, and not a graph runtime object. Supplied request
    objects are preserved exactly. The plan does not execute agents.
    """

    consumer_load_request: ConsumerLoadForecastModelRequest
    dam_price_request: DAMPriceForecastModelRequest

    def __post_init__(self) -> None:
        _require_type(
            "consumer_load_request",
            self.consumer_load_request,
            ConsumerLoadForecastModelRequest,
        )
        _require_type(
            "dam_price_request",
            self.dam_price_request,
            DAMPriceForecastModelRequest,
        )


def _require_type(field_name: str, value: object, expected: type[object]) -> None:
    if not isinstance(value, expected):
        msg = f"{field_name} must be a {expected.__name__}"
        raise TypeError(msg)
