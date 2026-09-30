"""Exact previous-day persistence DAM Price MAE evaluation.

This outer ML transformation scores already-built
``PreviousDayPersistenceBacktestCase`` values. It calculates MAE only.

Ownership:

* Application: owns live inference via ``DAMPriceForecastModelPort``.
* ML: owns this offline MAE evaluator. Returned values are ML evaluation
  results, not workflow state and not ``PriceForecastPoint``.
* Chunk 171 owns which historical pairs are evaluable, and the chronology
  of the cohort. This module scores exactly the supplied cases and does not
  rebuild history, rebuild backtest cases, or call live inference.

MAE remains a currency amount per MWh:

``MAE = mean(|predicted_price.amount_per_mwh - actual_price.amount_per_mwh|)``

Arithmetic stays in canonical ``Decimal``. The cohort must belong to exactly
one market and use exactly one currency, and each case's predicted and actual
price must share that currency. Target timestamps must be strictly increasing
and unique in supplied order; malformed cohorts fail closed rather than being
sorted, deduplicated, or repaired. An empty case tuple is undefined and fails
closed with existing ``InvalidRequestError``. There is no zero, NaN, infinity,
or optional sentinel result.

Canonical prices may be negative. ``abs`` is used only for the error
difference required by MAE; it never mutates a price input. Weighting,
rounding, quantizing, clamping, currency conversion, and MW/MWh conversion are
not implemented. No other metric is calculated.

The evaluator remains unwired from agents, API composition, FastAPI,
LangGraph, and ``ForecastingExecutionPort``.
"""

from dataclasses import dataclass

from energy_trading.application.errors import InvalidRequestError
from energy_trading.domain.value_objects.quantities import CurrencyCode, FiniteDecimal
from energy_trading.ml.dam_price.previous_day_persistence_backtest import (
    PreviousDayPersistenceBacktestCase,
)

_EMPTY_CASES_MESSAGE = (
    "Previous-day persistence MAE evaluation requires at least one backtest case."
)
_MIXED_MARKET_MESSAGE = (
    "Previous-day persistence MAE evaluation requires cases from exactly one market."
)
_MIXED_CURRENCY_MESSAGE = (
    "Previous-day persistence MAE evaluation requires cases in exactly one currency."
)
_CASE_CURRENCY_MISMATCH_MESSAGE = (
    "Previous-day persistence MAE evaluation requires matching predicted and actual case currency."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "Previous-day persistence MAE evaluation requires unique target timestamps."
)
_OUT_OF_ORDER_MESSAGE = (
    "Previous-day persistence MAE evaluation requires strictly increasing target timestamps."
)


@dataclass(frozen=True, slots=True)
class PreviousDayPersistenceMAEResult:
    """MAE over supplied previous-day persistence backtest cases."""

    case_count: int
    currency: CurrencyCode
    mae_amount_per_mwh: FiniteDecimal


def evaluate_previous_day_persistence_mae(
    *,
    cases: tuple[PreviousDayPersistenceBacktestCase, ...],
) -> PreviousDayPersistenceMAEResult:
    """Return MAE as a currency amount per MWh over the supplied cases."""

    if not cases:
        raise InvalidRequestError(_EMPTY_CASES_MESSAGE)
    _require_single_market(cases)
    currency = _require_single_currency(cases)
    _require_strict_chronology(cases)
    total_abs_error = abs(
        cases[0].predicted_price.amount_per_mwh - cases[0].actual_price.amount_per_mwh
    )
    for case in cases[1:]:
        total_abs_error += abs(
            case.predicted_price.amount_per_mwh - case.actual_price.amount_per_mwh
        )
    return PreviousDayPersistenceMAEResult(
        case_count=len(cases),
        currency=currency,
        mae_amount_per_mwh=total_abs_error / len(cases),
    )


def _require_single_market(
    cases: tuple[PreviousDayPersistenceBacktestCase, ...],
) -> None:
    market_ids = {case.market_id for case in cases}
    if len(market_ids) > 1:
        raise InvalidRequestError(_MIXED_MARKET_MESSAGE)


def _require_single_currency(
    cases: tuple[PreviousDayPersistenceBacktestCase, ...],
) -> str:
    for case in cases:
        if case.predicted_price.currency != case.actual_price.currency:
            raise InvalidRequestError(_CASE_CURRENCY_MISMATCH_MESSAGE)
    currencies = {case.actual_price.currency for case in cases}
    if len(currencies) > 1:
        raise InvalidRequestError(_MIXED_CURRENCY_MESSAGE)
    return next(iter(currencies))


def _require_strict_chronology(
    cases: tuple[PreviousDayPersistenceBacktestCase, ...],
) -> None:
    previous = cases[0]
    for current in cases[1:]:
        if previous.target_timestamp == current.target_timestamp:
            raise InvalidRequestError(_DUPLICATE_TIMESTAMP_MESSAGE)
        if previous.target_timestamp > current.target_timestamp:
            raise InvalidRequestError(_OUT_OF_ORDER_MESSAGE)
        previous = current
