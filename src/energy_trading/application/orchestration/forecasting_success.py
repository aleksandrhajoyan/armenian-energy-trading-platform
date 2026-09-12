"""Application-owned forecasting-phase success aggregate.

``ForecastingSuccess`` carries the two already-canonical Phase 3 forecast
output tuples for one future successful forecasting-phase execution.

Ownership:

* Application: owns ``ForecastingSuccess``.
* Existing canonical points: reused as-is. This module does not shadow or
  replace ``LoadForecastPoint`` or ``PriceForecastPoint``.
* Future execution: a separately reviewed module may produce these tuples.
  This module does not execute agents, does not choose concurrency, and
  does not encode Consumer → DAM ordering.

The aggregate does not equalize tuple lengths, timestamps, or horizons,
derive market identity from consumer identity, convert MW/MWh or
currencies, or imply a dependency between the two forecasts. Chunk 118
and Chunk 120 remain the semantic authorities for their own output
tuples.
"""

from dataclasses import dataclass

from energy_trading.domain.models.forecasting import LoadForecastPoint, PriceForecastPoint


@dataclass(frozen=True, slots=True)
class ForecastingSuccess:
    """Immutable all-two-success aggregate of canonical forecast tuples.

    This is an application orchestration DTO, not ``WorkflowState``, not a
    domain contract, and not a graph runtime object. It represents only
    the case where both Phase 3 forecasting operations have already
    produced their canonical output tuples. Supplied tuples are preserved
    exactly. The aggregate does not execute agents and does not encode
    failure, degraded, or partial-completion semantics.
    """

    consumer_load_forecast: tuple[LoadForecastPoint, ...]
    dam_price_forecast: tuple[PriceForecastPoint, ...]

    def __post_init__(self) -> None:
        _require_tuple_of(
            "consumer_load_forecast",
            self.consumer_load_forecast,
            LoadForecastPoint,
        )
        _require_tuple_of(
            "dam_price_forecast",
            self.dam_price_forecast,
            PriceForecastPoint,
        )


def _require_tuple_of(field_name: str, value: object, item_type: type[object]) -> None:
    if not isinstance(value, tuple):
        msg = f"{field_name} must be an immutable tuple"
        raise TypeError(msg)
    if not all(isinstance(item, item_type) for item in value):
        msg = f"{field_name} must contain {item_type.__name__} values"
        raise TypeError(msg)
