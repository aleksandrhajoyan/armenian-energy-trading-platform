"""Immutable monetary and energy-price value objects using Decimal."""

from energy_trading.domain.models.base import CanonicalModel
from energy_trading.domain.value_objects.quantities import CurrencyCode, FiniteDecimal


class MoneyAmount(CanonicalModel):
    """A currency-tagged monetary amount. Sign is not constrained."""

    amount: FiniteDecimal
    currency: CurrencyCode


class EnergyPrice(CanonicalModel):
    """A currency-tagged price per megawatt-hour. Sign is not constrained."""

    amount_per_mwh: FiniteDecimal
    currency: CurrencyCode
