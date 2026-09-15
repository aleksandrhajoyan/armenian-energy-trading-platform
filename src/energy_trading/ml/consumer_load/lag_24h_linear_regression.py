"""Lag-24h ordinary least-squares Consumer Load parameter fit.

This outer ML transformation fits one slope and one intercept from
already-built Chunk 135 ``ConsumerLoadLag24hFeatureRow`` training values.
It does not emit forecasts and does not calculate metrics.

Ownership:

* Application: owns live inference via ``ConsumerLoadForecastModelPort``.
* ML: owns this offline one-feature OLS fit. Returned values are ML
  fitted parameters, not workflow state and not a live forecast point.
* Already-built feature rows are the only input. This module does not
  rebuild history, does not own chronological splitting, and does not
  belong to application orchestration.

Ordinary least squares:

* ``x_i = lag_24h_mw``
* ``y_i = target_value_mw``
* ``slope = numerator / denominator``
* ``intercept_mw = y_mean - slope * x_mean``

A negative intercept is mathematically valid and is not clamped. Zero
feature variance, fewer than two rows, mixed consumers, and malformed
chronology fail closed. External ML libraries are not used.

The fitter remains unwired from agents, API composition, FastAPI,
LangGraph, and ``ForecastingExecutionPort``.
"""

from dataclasses import dataclass
from math import isfinite

from energy_trading.application.errors import InvalidRequestError
from energy_trading.ml.consumer_load.lag_24h_features import ConsumerLoadLag24hFeatureRow

_TOO_FEW_ROWS_MESSAGE = (
    "Consumer Load lag-24h linear regression requires at least two training rows."
)
_MIXED_CONSUMER_MESSAGE = (
    "Consumer Load lag-24h linear regression requires rows from exactly one consumer."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "Consumer Load lag-24h linear regression requires unique target timestamps."
)
_OUT_OF_ORDER_MESSAGE = (
    "Consumer Load lag-24h linear regression requires strictly increasing target timestamps."
)
_ZERO_VARIANCE_MESSAGE = (
    "Consumer Load lag-24h linear regression requires non-zero variance in lag_24h_mw."
)
_NON_FINITE_MESSAGE = (
    "Consumer Load lag-24h linear regression requires finite fitted slope and intercept."
)


@dataclass(frozen=True, slots=True)
class ConsumerLoadLag24hLinearRegressionFit:
    """Fitted one-feature OLS slope and intercept for Consumer Load."""

    slope: float
    intercept_mw: float


def fit_consumer_load_lag_24h_linear_regression(
    *,
    training_rows: tuple[ConsumerLoadLag24hFeatureRow, ...],
) -> ConsumerLoadLag24hLinearRegressionFit:
    """Fit OLS slope and intercept from chronological lag-24h training rows."""

    if len(training_rows) < 2:
        raise InvalidRequestError(_TOO_FEW_ROWS_MESSAGE)
    _require_single_consumer(training_rows)
    _require_strict_chronology(training_rows)
    features = tuple(row.lag_24h_mw for row in training_rows)
    targets = tuple(row.target_value_mw for row in training_rows)
    count = len(training_rows)
    x_mean = sum(features) / count
    y_mean = sum(targets) / count
    numerator = sum(
        (features[index] - x_mean) * (targets[index] - y_mean) for index in range(count)
    )
    denominator = sum((x_i - x_mean) ** 2 for x_i in features)
    if denominator == 0.0:
        raise InvalidRequestError(_ZERO_VARIANCE_MESSAGE)
    slope = numerator / denominator
    intercept_mw = y_mean - slope * x_mean
    if not isfinite(slope) or not isfinite(intercept_mw):
        raise InvalidRequestError(_NON_FINITE_MESSAGE)
    return ConsumerLoadLag24hLinearRegressionFit(slope=slope, intercept_mw=intercept_mw)


def _require_single_consumer(rows: tuple[ConsumerLoadLag24hFeatureRow, ...]) -> None:
    consumer_ids = {row.consumer_id for row in rows}
    if len(consumer_ids) > 1:
        raise InvalidRequestError(_MIXED_CONSUMER_MESSAGE)


def _require_strict_chronology(rows: tuple[ConsumerLoadLag24hFeatureRow, ...]) -> None:
    previous = rows[0]
    for current in rows[1:]:
        if previous.target_timestamp == current.target_timestamp:
            raise InvalidRequestError(_DUPLICATE_TIMESTAMP_MESSAGE)
        if previous.target_timestamp > current.target_timestamp:
            raise InvalidRequestError(_OUT_OF_ORDER_MESSAGE)
        previous = current
