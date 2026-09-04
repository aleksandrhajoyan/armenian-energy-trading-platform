"""Deterministic power-unit conversion to canonical MW.

Energy units (MWh, kWh) are not power and are not supported. Interval length
is not assumed. Conversion uses ``Decimal`` arithmetic; the returned value is
a finite ``float`` for subsequent canonical ``NonNegativeMW`` validation.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from enum import StrEnum
from math import isfinite

from energy_trading.infrastructure.adapters.structured.normalization.errors import (
    NormalizationConfigurationError,
    SourceValueNormalizationError,
)

_KW_PER_MW = Decimal("1000")


class PowerUnit(StrEnum):
    """Explicit source power unit. Not an energy unit and not a domain type."""

    MW = "MW"
    KW = "KW"


def normalize_power_to_mw(value: object, source_unit: PowerUnit) -> float:
    """Convert an explicit source power measurement to MW.

    Boolean values are rejected. Non-negative/finite canonical constraints
    remain the domain's responsibility.
    """

    unit = _require_power_unit(source_unit)
    amount = _decimal_power(value)
    if unit is PowerUnit.KW:
        amount = amount / _KW_PER_MW
    return float(amount)


def _require_power_unit(value: object) -> PowerUnit:
    if isinstance(value, PowerUnit):
        return value
    raise NormalizationConfigurationError("source_power_unit must be a PowerUnit")


def _decimal_power(value: object) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise SourceValueNormalizationError("power source representation is invalid")
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        if not isfinite(value):
            raise SourceValueNormalizationError("power source representation is invalid")
        return Decimal(str(value))
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise SourceValueNormalizationError("power source representation is invalid")
        try:
            parsed = Decimal(text)
        except InvalidOperation as exc:
            raise SourceValueNormalizationError("power source representation is invalid") from exc
        if not parsed.is_finite():
            raise SourceValueNormalizationError("power source representation is invalid")
        return parsed
    raise SourceValueNormalizationError("power source representation is invalid")
