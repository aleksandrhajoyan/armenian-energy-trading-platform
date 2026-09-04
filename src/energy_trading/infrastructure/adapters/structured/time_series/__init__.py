"""Consumption time-series structural validation inside the structured ACL."""

from energy_trading.infrastructure.adapters.structured.time_series.consumption import (
    validate_consumption_series,
)
from energy_trading.infrastructure.adapters.structured.time_series.models import (
    ConsumptionRecordCandidate,
    ConsumptionSeriesIssue,
    ConsumptionSeriesIssueCode,
    ConsumptionSeriesValidationResult,
    IntervalGrid,
)

__all__ = [
    "ConsumptionRecordCandidate",
    "ConsumptionSeriesIssue",
    "ConsumptionSeriesIssueCode",
    "ConsumptionSeriesValidationResult",
    "IntervalGrid",
    "validate_consumption_series",
]
