"""Risk, bid, and clearing contracts. No market-gateway or VaR math."""

from enum import StrEnum
from typing import Self

from pydantic import model_validator

from energy_trading.domain.models.base import CanonicalModel
from energy_trading.domain.value_objects.money import EnergyPrice, MoneyAmount
from energy_trading.domain.value_objects.quantities import (
    EntityId,
    FiniteDecimal,
    NonEmptyString,
    NonNegativeMW,
    PositiveMW,
    UnitInterval,
)
from energy_trading.domain.value_objects.time import UtcDateTime


class BidSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class ClearingStatus(StrEnum):
    CLEARED = "cleared"
    PARTIALLY_CLEARED = "partially_cleared"
    REJECTED = "rejected"


class RiskAssessment(CanonicalModel):
    """Portfolio risk snapshot. Optional monetary fields are not calculated here."""

    assessment_id: EntityId
    assessed_at: UtcDateTime
    delivery_timestamp: UtcDateTime
    risk_score: UnitInterval
    expected_margin: MoneyAmount | None = None
    price_volatility: FiniteDecimal | None = None
    expected_balancing_penalty: MoneyAmount | None = None
    value_at_risk: MoneyAmount | None = None
    notes: NonEmptyString | None = None


class MarketBid(CanonicalModel):
    """Intention to buy or sell for one delivery timestamp. Gate rules are not encoded."""

    bid_id: EntityId
    created_at: UtcDateTime
    delivery_timestamp: UtcDateTime
    side: BidSide
    quantity_mw: PositiveMW
    limit_price: EnergyPrice


class MarketClearingResult(CanonicalModel):
    """Canonical internal clearing outcome for a bid. Not an external gateway schema."""

    bid_id: EntityId
    delivery_timestamp: UtcDateTime
    cleared_at: UtcDateTime
    status: ClearingStatus
    cleared_quantity_mw: NonNegativeMW
    clearing_price: EnergyPrice | None = None

    @model_validator(mode="after")
    def rejected_may_omit_price(self) -> Self:
        if self.status is not ClearingStatus.REJECTED and self.clearing_price is None:
            msg = "clearing_price is required unless status is rejected"
            raise ValueError(msg)
        return self
