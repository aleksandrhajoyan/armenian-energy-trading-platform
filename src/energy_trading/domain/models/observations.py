"""Canonical observation and situational contracts."""

from enum import StrEnum
from typing import Self

from pydantic import model_validator

from energy_trading.domain.models.base import CanonicalModel
from energy_trading.domain.value_objects.money import EnergyPrice
from energy_trading.domain.value_objects.quantities import (
    EntityId,
    FiniteNumber,
    NonEmptyString,
    NonNegativeMW,
    NonNegativeMWh,
    NonNegativeNumber,
)
from energy_trading.domain.value_objects.time import UtcDateTime


class GenerationStatus(StrEnum):
    AVAILABLE = "available"
    MAINTENANCE = "maintenance"
    OUTAGE = "outage"
    UNKNOWN = "unknown"


class NewsSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ConsumptionRecord(CanonicalModel):
    """Observed consumer load at one canonical timestamp."""

    consumer_id: EntityId
    timestamp: UtcDateTime
    value_mw: NonNegativeMW


class WeatherRecord(CanonicalModel):
    """Weather observation or forecast point. Provider identity is not modeled."""

    location_id: EntityId
    timestamp: UtcDateTime
    temperature_c: FiniteNumber
    solar_irradiance_w_m2: NonNegativeNumber | None = None
    precipitation_mm: NonNegativeNumber | None = None


class HydroRecord(CanonicalModel):
    """Hydro storage/flow context. No hydrological calculations."""

    resource_id: EntityId
    timestamp: UtcDateTime
    reservoir_level_m: NonNegativeNumber | None = None
    river_flow_m3_s: NonNegativeNumber | None = None
    available_generation_mw: NonNegativeMW | None = None


class GenerationAvailabilityRecord(CanonicalModel):
    """Available capacity of an unnamed asset at one canonical timestamp."""

    asset_id: EntityId
    timestamp: UtcDateTime
    status: GenerationStatus
    available_capacity_mw: NonNegativeMW
    total_capacity_mw: NonNegativeMW | None = None

    @model_validator(mode="after")
    def available_cannot_exceed_total(self) -> Self:
        if (
            self.total_capacity_mw is not None
            and self.available_capacity_mw > self.total_capacity_mw
        ):
            msg = "available_capacity_mw must be less than or equal to total_capacity_mw"
            raise ValueError(msg)
        return self


class MarketPriceRecord(CanonicalModel):
    """Observed market price. Currency is explicit; interval length is not assumed."""

    market_id: EntityId
    timestamp: UtcDateTime
    price: EnergyPrice
    volume_mwh: NonNegativeMWh | None = None


class NewsEvent(CanonicalModel):
    """Qualitative public-information event. Not a forecast and not raw HTML."""

    event_id: EntityId
    timestamp: UtcDateTime
    headline: NonEmptyString
    summary: NonEmptyString
    category: NonEmptyString | None = None
    severity: NewsSeverity | None = None
