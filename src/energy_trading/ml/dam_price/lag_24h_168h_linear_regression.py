"""Lag-24h plus lag-168h ordinary least-squares DAM Price parameter fit.

This outer ML transformation fits two coefficients and one intercept from
already-built Chunk 179 ``DAMPriceLag24h168hFeatureRow`` training values. It
does not emit forecasts and does not calculate metrics.

Ownership:

* Application: owns live inference via ``DAMPriceForecastModelPort``.
* ML: owns this offline two-feature OLS fit. Returned values are ML fitted
  parameters, not workflow state and not a live forecast price.
* Already-built two-lag feature rows are the only input. This module does not
  rebuild history, does not own chronological splitting, does not consume the
  Chunk 180 split object, and does not belong to application orchestration.
  It is independent of the published one-feature Chunk 175 fit and does not
  fall back to it.

Ordinary least squares with intercept:

* ``x1 = lag_24h_amount_per_mwh``
* ``x2 = lag_168h_amount_per_mwh``
* ``y = target_amount_per_mwh``
* centered aggregates ``s11``, ``s22``, ``s12``, ``t1``, ``t2``
* ``determinant = s11 * s22 - s12 * s12``
* ``lag_24h_coefficient = (t1 * s22 - t2 * s12) / determinant``
* ``lag_168h_coefficient = (t2 * s11 - t1 * s12) / determinant``
* ``intercept_amount_per_mwh = y_mean - lag_24h_coefficient * x1_mean
  - lag_168h_coefficient * x2_mean``

All arithmetic stays in canonical ``Decimal``: no float conversion, rounding,
quantization, scaling, standardization, normalization, stabilization, or
regularization is performed. The intercept is an ML parameter derived from a
currency-qualified price scale, not a canonical market-price observation, so
it is not wrapped as ``EnergyPrice``. Negative or zero coefficients and a
negative or zero intercept are mathematically valid and are not clamped.

Fewer than three rows, a non-positive centered determinant (including zero
variance in either feature and perfect collinearity), mixed markets, mixed
currencies, malformed chronology, and non-finite inputs, aggregates, or fitted
parameters all fail closed. External ML libraries are not used.

The fitter remains unwired from agents, API composition, FastAPI, LangGraph,
and ``ForecastingExecutionPort``.
"""

from dataclasses import dataclass
from decimal import Decimal, DecimalException

from energy_trading.application.errors import InvalidRequestError
from energy_trading.domain.value_objects.quantities import FiniteDecimal
from energy_trading.ml.dam_price.lag_24h_168h_features import DAMPriceLag24h168hFeatureRow

_TOO_FEW_ROWS_MESSAGE = (
    "DAM Price 24h+168h linear regression requires at least three training rows."
)
_MIXED_MARKET_MESSAGE = (
    "DAM Price 24h+168h linear regression requires rows from exactly one market."
)
_MIXED_CURRENCY_MESSAGE = (
    "DAM Price 24h+168h linear regression requires rows in exactly one currency."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "DAM Price 24h+168h linear regression requires unique target timestamps."
)
_OUT_OF_ORDER_MESSAGE = (
    "DAM Price 24h+168h linear regression requires strictly increasing target timestamps."
)
_SINGULAR_DESIGN_MESSAGE = (
    "DAM Price 24h+168h linear regression requires a full-rank two-feature design."
)
_NON_FINITE_INPUT_MESSAGE = (
    "DAM Price 24h+168h linear regression requires finite feature and target values."
)
_NON_FINITE_FIT_MESSAGE = (
    "DAM Price 24h+168h linear regression requires finite fitted coefficients and intercept."
)


@dataclass(frozen=True, slots=True)
class DAMPriceLag24h168hLinearRegressionFit:
    """Fitted two-feature OLS coefficients and intercept for DAM Price."""

    lag_24h_coefficient: FiniteDecimal
    lag_168h_coefficient: FiniteDecimal
    intercept_amount_per_mwh: FiniteDecimal


def fit_dam_price_lag_24h_168h_linear_regression(
    *,
    training_rows: tuple[DAMPriceLag24h168hFeatureRow, ...],
) -> DAMPriceLag24h168hLinearRegressionFit:
    """Fit OLS coefficients and intercept from chronological two-lag rows."""

    if len(training_rows) < 3:
        raise InvalidRequestError(_TOO_FEW_ROWS_MESSAGE)
    _require_single_market(training_rows)
    _require_single_currency(training_rows)
    _require_strict_chronology(training_rows)
    lag_24h_values = tuple(row.lag_24h_amount_per_mwh for row in training_rows)
    lag_168h_values = tuple(row.lag_168h_amount_per_mwh for row in training_rows)
    targets = tuple(row.target_amount_per_mwh for row in training_rows)
    _require_finite_values(lag_24h_values, lag_168h_values, targets)
    lag_24h_coefficient, lag_168h_coefficient, intercept = _compute_ols(
        lag_24h_values, lag_168h_values, targets
    )
    if (
        not lag_24h_coefficient.is_finite()
        or not lag_168h_coefficient.is_finite()
        or not intercept.is_finite()
    ):
        raise InvalidRequestError(_NON_FINITE_FIT_MESSAGE)
    return DAMPriceLag24h168hLinearRegressionFit(
        lag_24h_coefficient=lag_24h_coefficient,
        lag_168h_coefficient=lag_168h_coefficient,
        intercept_amount_per_mwh=intercept,
    )


def _compute_ols(
    lag_24h_values: tuple[Decimal, ...],
    lag_168h_values: tuple[Decimal, ...],
    targets: tuple[Decimal, ...],
) -> tuple[Decimal, Decimal, Decimal]:
    """Compute centered two-feature OLS parameters in canonical Decimal.

    Decimal arithmetic can raise a signal for a valid-looking cohort whose
    intermediate products or quotients leave the representable range. Every
    arithmetic step is therefore performed under a narrowed Decimal-exception
    guard so that such a cohort becomes the same sanitized failure family
    rather than leaking raw numeric inputs. Only ``DecimalException`` is
    translated, so no broad exception handling is introduced.
    """

    try:
        count = Decimal(len(targets))
        x1_mean = _mean(lag_24h_values, count)
        x2_mean = _mean(lag_168h_values, count)
        y_mean = _mean(targets, count)
        s11 = _zero()
        s22 = _zero()
        s12 = _zero()
        t1 = _zero()
        t2 = _zero()
        for index in range(len(targets)):
            dx1 = lag_24h_values[index] - x1_mean
            dx2 = lag_168h_values[index] - x2_mean
            dy = targets[index] - y_mean
            s11 += dx1 * dx1
            s22 += dx2 * dx2
            s12 += dx1 * dx2
            t1 += dx1 * dy
            t2 += dx2 * dy
        determinant = s11 * s22 - s12 * s12
    except DecimalException as error:
        msg = _NON_FINITE_FIT_MESSAGE
        raise InvalidRequestError(msg) from error
    for aggregate in (x1_mean, x2_mean, y_mean, s11, s22, s12, t1, t2, determinant):
        if not aggregate.is_finite():
            raise InvalidRequestError(_NON_FINITE_FIT_MESSAGE)
    if determinant <= 0:
        raise InvalidRequestError(_SINGULAR_DESIGN_MESSAGE)
    try:
        lag_24h_coefficient = (t1 * s22 - t2 * s12) / determinant
        lag_168h_coefficient = (t2 * s11 - t1 * s12) / determinant
        intercept = y_mean - lag_24h_coefficient * x1_mean - lag_168h_coefficient * x2_mean
    except DecimalException as error:
        msg = _NON_FINITE_FIT_MESSAGE
        raise InvalidRequestError(msg) from error
    return lag_24h_coefficient, lag_168h_coefficient, intercept


def _mean(values: tuple[Decimal, ...], count: Decimal) -> Decimal:
    total = _zero()
    for value in values:
        total += value
    return total / count


def _zero() -> Decimal:
    """Return a typed Decimal zero accumulator seed.

    Written explicitly so the accumulator keeps the canonical Decimal type
    instead of the ``Decimal | Literal[0]`` that a bare builtin aggregate
    would infer.
    """

    return Decimal(0)


def _require_finite_values(
    lag_24h_values: tuple[Decimal, ...],
    lag_168h_values: tuple[Decimal, ...],
    targets: tuple[Decimal, ...],
) -> None:
    for values in (lag_24h_values, lag_168h_values, targets):
        for value in values:
            if not value.is_finite():
                raise InvalidRequestError(_NON_FINITE_INPUT_MESSAGE)


def _require_single_market(rows: tuple[DAMPriceLag24h168hFeatureRow, ...]) -> None:
    market_ids = {row.market_id for row in rows}
    if len(market_ids) > 1:
        raise InvalidRequestError(_MIXED_MARKET_MESSAGE)


def _require_single_currency(rows: tuple[DAMPriceLag24h168hFeatureRow, ...]) -> None:
    currencies = {row.currency for row in rows}
    if len(currencies) > 1:
        raise InvalidRequestError(_MIXED_CURRENCY_MESSAGE)


def _require_strict_chronology(rows: tuple[DAMPriceLag24h168hFeatureRow, ...]) -> None:
    previous = rows[0]
    for current in rows[1:]:
        if previous.target_timestamp == current.target_timestamp:
            raise InvalidRequestError(_DUPLICATE_TIMESTAMP_MESSAGE)
        if previous.target_timestamp > current.target_timestamp:
            raise InvalidRequestError(_OUT_OF_ORDER_MESSAGE)
        previous = current
