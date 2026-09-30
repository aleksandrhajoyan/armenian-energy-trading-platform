"""Lag-24h ordinary least-squares DAM Price parameter fit.

This outer ML transformation fits one slope and one intercept from
already-built Chunk 173 ``DAMPriceLag24hFeatureRow`` training values. It does
not emit forecasts and does not calculate metrics.

Ownership:

* Application: owns live inference via ``DAMPriceForecastModelPort``.
* ML: owns this offline one-feature OLS fit. Returned values are ML fitted
  parameters, not workflow state and not a live forecast price.
* Already-built feature rows are the only input. This module does not rebuild
  history, does not own chronological splitting, does not consume the Chunk
  174 split object, and does not belong to application orchestration.

Ordinary least squares:

* ``x_i = lag_24h_amount_per_mwh``
* ``y_i = target_amount_per_mwh``
* ``slope = numerator / denominator``
* ``intercept_amount_per_mwh = y_mean - slope * x_mean``

All arithmetic stays in canonical ``Decimal``: no float conversion, rounding,
quantization, scaling, standardization, normalization, or regularization is
performed. The intercept is an ML parameter derived from a currency-qualified
price scale, not a canonical market-price observation, so it is not wrapped as
``EnergyPrice``. A negative slope or intercept is mathematically valid and is
not clamped.

Fewer than two rows, zero feature variance, mixed markets, mixed currencies,
malformed chronology, and non-finite inputs or fitted parameters all fail
closed. External ML libraries are not used.

The fitter remains unwired from agents, API composition, FastAPI, LangGraph,
and ``ForecastingExecutionPort``.
"""

from dataclasses import dataclass
from decimal import Decimal, DecimalException

from energy_trading.application.errors import InvalidRequestError
from energy_trading.domain.value_objects.quantities import FiniteDecimal
from energy_trading.ml.dam_price.lag_24h_features import DAMPriceLag24hFeatureRow

_TOO_FEW_ROWS_MESSAGE = "DAM Price lag-24h linear regression requires at least two training rows."
_MIXED_MARKET_MESSAGE = "DAM Price lag-24h linear regression requires rows from exactly one market."
_MIXED_CURRENCY_MESSAGE = (
    "DAM Price lag-24h linear regression requires rows in exactly one currency."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "DAM Price lag-24h linear regression requires unique target timestamps."
)
_OUT_OF_ORDER_MESSAGE = (
    "DAM Price lag-24h linear regression requires strictly increasing target timestamps."
)
_ZERO_VARIANCE_MESSAGE = (
    "DAM Price lag-24h linear regression requires non-zero variance in lag_24h_amount_per_mwh."
)
_NON_FINITE_INPUT_MESSAGE = (
    "DAM Price lag-24h linear regression requires finite feature and target values."
)
_NON_FINITE_FIT_MESSAGE = (
    "DAM Price lag-24h linear regression requires finite fitted slope and intercept."
)


@dataclass(frozen=True, slots=True)
class DAMPriceLag24hLinearRegressionFit:
    """Fitted one-feature OLS slope and intercept for DAM Price."""

    slope: FiniteDecimal
    intercept_amount_per_mwh: FiniteDecimal


def fit_dam_price_lag_24h_linear_regression(
    *,
    training_rows: tuple[DAMPriceLag24hFeatureRow, ...],
) -> DAMPriceLag24hLinearRegressionFit:
    """Fit OLS slope and intercept from chronological lag-24h training rows."""

    if len(training_rows) < 2:
        raise InvalidRequestError(_TOO_FEW_ROWS_MESSAGE)
    _require_single_market(training_rows)
    _require_single_currency(training_rows)
    _require_strict_chronology(training_rows)
    features = tuple(row.lag_24h_amount_per_mwh for row in training_rows)
    targets = tuple(row.target_amount_per_mwh for row in training_rows)
    _require_finite_values(features, targets)
    slope, intercept = _fit_parameters(features, targets)
    return DAMPriceLag24hLinearRegressionFit(
        slope=slope,
        intercept_amount_per_mwh=intercept,
    )


def _fit_parameters(
    features: tuple[Decimal, ...],
    targets: tuple[Decimal, ...],
) -> tuple[Decimal, Decimal]:
    """Return Decimal OLS parameters, translating arithmetic failure closed.

    Decimal arithmetic can raise a signal for a valid-looking cohort whose
    intermediate products or quotients leave the representable range. Every
    arithmetic step is therefore performed under a narrowed Decimal-exception
    guard so that such a cohort becomes the same sanitized failure family
    rather than leaking raw numeric inputs. Only ``DecimalException`` is
    translated, so no broad exception handling is introduced.
    """

    slope, intercept = _compute_ols(features, targets)
    if not slope.is_finite() or not intercept.is_finite():
        raise InvalidRequestError(_NON_FINITE_FIT_MESSAGE)
    return slope, intercept


def _compute_ols(
    features: tuple[Decimal, ...],
    targets: tuple[Decimal, ...],
) -> tuple[Decimal, Decimal]:
    """Compute OLS parameters, failing closed on any Decimal arithmetic signal."""

    try:
        count = Decimal(len(features))
        x_mean = _mean(features, count)
        y_mean = _mean(targets, count)
        numerator = _zero()
        denominator = _zero()
        for index in range(len(features)):
            x_deviation = features[index] - x_mean
            numerator += x_deviation * (targets[index] - y_mean)
            denominator += x_deviation * x_deviation
    except DecimalException as error:
        msg = _NON_FINITE_FIT_MESSAGE
        raise InvalidRequestError(msg) from error
    if denominator == 0:
        raise InvalidRequestError(_ZERO_VARIANCE_MESSAGE)
    try:
        slope = numerator / denominator
        intercept = y_mean - slope * x_mean
    except DecimalException as error:
        msg = _NON_FINITE_FIT_MESSAGE
        raise InvalidRequestError(msg) from error
    return slope, intercept


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
    features: tuple[Decimal, ...],
    targets: tuple[Decimal, ...],
) -> None:
    for value in features:
        if not value.is_finite():
            raise InvalidRequestError(_NON_FINITE_INPUT_MESSAGE)
    for value in targets:
        if not value.is_finite():
            raise InvalidRequestError(_NON_FINITE_INPUT_MESSAGE)


def _require_single_market(rows: tuple[DAMPriceLag24hFeatureRow, ...]) -> None:
    market_ids = {row.market_id for row in rows}
    if len(market_ids) > 1:
        raise InvalidRequestError(_MIXED_MARKET_MESSAGE)


def _require_single_currency(rows: tuple[DAMPriceLag24hFeatureRow, ...]) -> None:
    currencies = {row.currency for row in rows}
    if len(currencies) > 1:
        raise InvalidRequestError(_MIXED_CURRENCY_MESSAGE)


def _require_strict_chronology(rows: tuple[DAMPriceLag24hFeatureRow, ...]) -> None:
    previous = rows[0]
    for current in rows[1:]:
        if previous.target_timestamp == current.target_timestamp:
            raise InvalidRequestError(_DUPLICATE_TIMESTAMP_MESSAGE)
        if previous.target_timestamp > current.target_timestamp:
            raise InvalidRequestError(_OUT_OF_ORDER_MESSAGE)
        previous = current
