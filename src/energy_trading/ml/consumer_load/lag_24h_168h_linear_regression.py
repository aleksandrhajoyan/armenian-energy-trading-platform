"""Lag-24h plus lag-168h ordinary least-squares Consumer Load parameter fit.

This outer ML transformation fits two coefficients and one intercept from
already-built Chunk 141 ``ConsumerLoadLag24h168hFeatureRow`` training
values. It does not emit forecasts and does not calculate metrics.

Ownership:

* Application: owns live inference via ``ConsumerLoadForecastModelPort``.
* ML: owns this offline two-feature OLS fit. Returned values are ML
  fitted parameters, not workflow state and not a live forecast point.
* Already-built two-lag feature rows are the only input. This module
  does not rebuild features, does not own chronological splitting, and
  does not belong to application orchestration.

Ordinary least squares:

* ``x1 = lag_24h_mw``
* ``x2 = lag_168h_mw``
* ``y = target_value_mw``
* centered two-feature normal equations with intercept
* ``intercept_mw = y_mean - lag_24h_coefficient * x1_mean - lag_168h_coefficient * x2_mean``

Negative coefficients and a negative intercept are mathematically valid
and are preserved. Fewer than three rows, non-finite intermediate
aggregates, a non-positive centered determinant, mixed consumers, and
malformed chronology fail closed.
External ML libraries are not used.

This contract is independent of the published one-feature OLS fit. The
fitter remains unwired from agents, API composition, FastAPI,
LangGraph, and ``ForecastingExecutionPort``.
"""

from dataclasses import dataclass
from math import isfinite

from energy_trading.application.errors import InvalidRequestError
from energy_trading.ml.consumer_load.lag_24h_168h_features import (
    ConsumerLoadLag24h168hFeatureRow,
)

_TOO_FEW_ROWS_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression requires "
    "at least three training rows."
)
_MIXED_CONSUMER_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression requires "
    "rows from exactly one consumer."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression requires unique target timestamps."
)
_OUT_OF_ORDER_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression requires "
    "strictly increasing target timestamps."
)
_SINGULAR_DESIGN_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression requires "
    "a full-rank two-feature design."
)
_NON_FINITE_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression requires "
    "finite fitted coefficients and intercept."
)


@dataclass(frozen=True, slots=True)
class ConsumerLoadLag24h168hLinearRegressionFit:
    """Fitted two-feature OLS coefficients and intercept for Consumer Load."""

    lag_24h_coefficient: float
    lag_168h_coefficient: float
    intercept_mw: float


def fit_consumer_load_lag_24h_168h_linear_regression(
    *,
    training_rows: tuple[ConsumerLoadLag24h168hFeatureRow, ...],
) -> ConsumerLoadLag24h168hLinearRegressionFit:
    """Fit OLS coefficients and intercept from chronological two-lag rows."""

    if len(training_rows) < 3:
        raise InvalidRequestError(_TOO_FEW_ROWS_MESSAGE)
    _require_single_consumer(training_rows)
    _require_strict_chronology(training_rows)
    lag_24h_values = tuple(row.lag_24h_mw for row in training_rows)
    lag_168h_values = tuple(row.lag_168h_mw for row in training_rows)
    targets = tuple(row.target_value_mw for row in training_rows)
    count = len(training_rows)
    x1_mean = sum(lag_24h_values) / count
    x2_mean = sum(lag_168h_values) / count
    y_mean = sum(targets) / count
    s11 = 0.0
    s22 = 0.0
    s12 = 0.0
    t1 = 0.0
    t2 = 0.0
    for index in range(count):
        dx1 = lag_24h_values[index] - x1_mean
        dx2 = lag_168h_values[index] - x2_mean
        dy = targets[index] - y_mean
        s11 += dx1 * dx1
        s22 += dx2 * dx2
        s12 += dx1 * dx2
        t1 += dx1 * dy
        t2 += dx2 * dy
    determinant = s11 * s22 - s12 * s12
    if not all(
        isfinite(value) for value in (x1_mean, x2_mean, y_mean, s11, s22, s12, t1, t2, determinant)
    ):
        raise InvalidRequestError(_NON_FINITE_MESSAGE)
    if determinant <= 0.0:
        raise InvalidRequestError(_SINGULAR_DESIGN_MESSAGE)
    lag_24h_coefficient = (t1 * s22 - t2 * s12) / determinant
    lag_168h_coefficient = (t2 * s11 - t1 * s12) / determinant
    intercept_mw = y_mean - lag_24h_coefficient * x1_mean - lag_168h_coefficient * x2_mean
    if (
        not isfinite(lag_24h_coefficient)
        or not isfinite(lag_168h_coefficient)
        or not isfinite(intercept_mw)
    ):
        raise InvalidRequestError(_NON_FINITE_MESSAGE)
    return ConsumerLoadLag24h168hLinearRegressionFit(
        lag_24h_coefficient=lag_24h_coefficient,
        lag_168h_coefficient=lag_168h_coefficient,
        intercept_mw=intercept_mw,
    )


def _require_single_consumer(rows: tuple[ConsumerLoadLag24h168hFeatureRow, ...]) -> None:
    consumer_ids = {row.consumer_id for row in rows}
    if len(consumer_ids) > 1:
        raise InvalidRequestError(_MIXED_CONSUMER_MESSAGE)


def _require_strict_chronology(rows: tuple[ConsumerLoadLag24h168hFeatureRow, ...]) -> None:
    previous = rows[0]
    for current in rows[1:]:
        if previous.target_timestamp == current.target_timestamp:
            raise InvalidRequestError(_DUPLICATE_TIMESTAMP_MESSAGE)
        if previous.target_timestamp > current.target_timestamp:
            raise InvalidRequestError(_OUT_OF_ORDER_MESSAGE)
        previous = current
