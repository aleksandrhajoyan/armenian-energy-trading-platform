"""Infrastructure-only source-representation guards for Consumption adapters.

These rules answer which CSV/Excel cell representations the adapters claim to
understand. They do not duplicate domain validation, convert units, interpret
Unix epochs or Excel serial dates, or attach timezones.
"""

from __future__ import annotations

from datetime import datetime


class UnrecognizedConsumptionSourceValue(Exception):
    """Selected cell is not a source representation this adapter understands."""


def consumption_timestamp_from_csv(value: str) -> str:
    """Accept a textual datetime form; reject bare numeric epoch strings."""

    if _is_bare_numeric_text(value):
        raise UnrecognizedConsumptionSourceValue
    return value


def consumption_timestamp_from_excel(value: object) -> str | datetime:
    """Accept only ``str`` or ``datetime`` timestamp cells.

    Canonical ``UtcDateTime`` still decides awareness, syntax, and UTC
    normalization. Numeric cells, booleans, and ``date`` values are rejected.
    """

    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return consumption_timestamp_from_csv(value)
    raise UnrecognizedConsumptionSourceValue


def consumption_mw_from_excel(value: object) -> object:
    """Reject boolean cells; leave numeric/text measurement checks to the domain."""

    if isinstance(value, bool):
        raise UnrecognizedConsumptionSourceValue
    return value


def _is_bare_numeric_text(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    try:
        float(text)
    except ValueError:
        return False
    return True
