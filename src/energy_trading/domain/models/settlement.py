"""Settlement result contract. Validates a result; it does not compute one."""

from typing import Self

from pydantic import model_validator

from energy_trading.domain.models.base import CanonicalModel
from energy_trading.domain.value_objects.money import MoneyAmount
from energy_trading.domain.value_objects.quantities import EntityId, NonNegativeMWh
from energy_trading.domain.value_objects.time import UtcDateTime


class SettlementResult(CanonicalModel):
    """Financial and energy settlement outcome for a period.

    ``profit`` is supplied by a future settlement service. This model does not
    set profit from revenue and costs.
    """

    settlement_id: EntityId
    period_start: UtcDateTime
    period_end: UtcDateTime
    delivered_energy_mwh: NonNegativeMWh
    revenue: MoneyAmount
    procurement_cost: MoneyAmount
    balancing_cost: MoneyAmount
    profit: MoneyAmount

    @model_validator(mode="after")
    def validate_period_and_currency(self) -> Self:
        if self.period_end <= self.period_start:
            msg = "period_end must be after period_start"
            raise ValueError(msg)
        currencies = {
            self.revenue.currency,
            self.procurement_cost.currency,
            self.balancing_cost.currency,
            self.profit.currency,
        }
        if len(currencies) != 1:
            msg = "all monetary fields in a settlement result must use the same currency"
            raise ValueError(msg)
        return self
