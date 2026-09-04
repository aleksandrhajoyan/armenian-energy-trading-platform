"""Constrained identifiers, quantities, and unit-bearing scalars.

Power is MW. Energy is MWh. The two are not interchangeable.
"""

from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator, Field, PlainSerializer, StringConstraints

EntityId = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]
NonEmptyString = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]
CurrencyCode = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Z]{3}$", min_length=3, max_length=3),
]

NonNegativeMW = Annotated[float, Field(ge=0, allow_inf_nan=False)]
PositiveMW = Annotated[float, Field(gt=0, allow_inf_nan=False)]
NonNegativeMWh = Annotated[float, Field(ge=0, allow_inf_nan=False)]
UnitInterval = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
FiniteNumber = Annotated[float, Field(allow_inf_nan=False)]
NonNegativeNumber = Annotated[float, Field(ge=0, allow_inf_nan=False)]


def parse_finite_decimal(value: object) -> Decimal:
    """Accept Decimal, int, or numeric strings. Reject float, bool, NaN, and Infinity."""

    if isinstance(value, (bool, float)):
        msg = "monetary values must be Decimal, int, or str; float is not allowed"
        raise ValueError(msg)
    if isinstance(value, Decimal):
        decimal_value = value
    elif isinstance(value, int):
        decimal_value = Decimal(value)
    elif isinstance(value, str):
        decimal_value = Decimal(value)
    else:
        msg = "unsupported monetary value type"
        raise TypeError(msg)
    if not decimal_value.is_finite():
        msg = "monetary values must be finite"
        raise ValueError(msg)
    return decimal_value


def require_finite_decimal(value: Decimal) -> Decimal:
    if not value.is_finite():
        msg = "monetary values must be finite"
        raise ValueError(msg)
    return value


def serialize_decimal(value: Decimal) -> str:
    return format(value, "f")


FiniteDecimal = Annotated[
    Decimal,
    BeforeValidator(parse_finite_decimal),
    AfterValidator(require_finite_decimal),
    PlainSerializer(serialize_decimal, return_type=str, when_used="json"),
]
