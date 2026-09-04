"""Forecast output contracts. These are not calculators and embed no ML types."""

from energy_trading.domain.models.base import CanonicalModel
from energy_trading.domain.value_objects.money import EnergyPrice
from energy_trading.domain.value_objects.quantities import EntityId, NonNegativeMW
from energy_trading.domain.value_objects.time import UtcDateTime


class LoadForecastPoint(CanonicalModel):
    """ML-produced consumer load forecast for one target timestamp."""

    forecast_run_id: EntityId
    consumer_id: EntityId
    generated_at: UtcDateTime
    target_timestamp: UtcDateTime
    value_mw: NonNegativeMW


class PriceForecastPoint(CanonicalModel):
    """ML-produced market price forecast for one target timestamp."""

    forecast_run_id: EntityId
    market_id: EntityId
    generated_at: UtcDateTime
    target_timestamp: UtcDateTime
    price: EnergyPrice
