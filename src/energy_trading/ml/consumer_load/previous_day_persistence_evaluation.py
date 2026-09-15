"""Exact previous-day persistence Consumer Load MAE evaluation.

This outer ML transformation scores already-built
``PreviousDayPersistenceBacktestCase`` values. It calculates MAE only.

Ownership:

* Application: owns live inference via ``ConsumerLoadForecastModelPort``.
* ML: owns this offline MAE evaluator. Returned values are ML evaluation
  results, not workflow state and not ``LoadForecastPoint``.
* Chunk 133 owns which historical pairs are evaluable. This module scores
  exactly the supplied cases and does not rebuild history or backtest
  cases.

MAE remains in MW:

``MAE = mean(|predicted_value_mw - actual_value_mw|)``

An empty case tuple is undefined and fails closed with existing
``InvalidRequestError``. There is no zero, NaN, infinity, or optional
sentinel result. Weighting, rounding, and MW↔MWh conversion are not
implemented.

The evaluator remains unwired from agents, API composition, FastAPI,
LangGraph, and ``ForecastingExecutionPort``.
"""

from dataclasses import dataclass

from energy_trading.application.errors import InvalidRequestError
from energy_trading.domain.value_objects.quantities import NonNegativeMW
from energy_trading.ml.consumer_load.previous_day_persistence_backtest import (
    PreviousDayPersistenceBacktestCase,
)

_EMPTY_CASES_MESSAGE = (
    "Previous-day persistence MAE evaluation requires at least one backtest case."
)


@dataclass(frozen=True, slots=True)
class PreviousDayPersistenceMAEResult:
    """MAE over supplied previous-day persistence backtest cases."""

    case_count: int
    mae_mw: NonNegativeMW


def evaluate_previous_day_persistence_mae(
    *,
    cases: tuple[PreviousDayPersistenceBacktestCase, ...],
) -> PreviousDayPersistenceMAEResult:
    """Return MAE in MW over the supplied evaluation cases."""

    if not cases:
        raise InvalidRequestError(_EMPTY_CASES_MESSAGE)
    total_abs_error = sum(abs(case.predicted_value_mw - case.actual_value_mw) for case in cases)
    return PreviousDayPersistenceMAEResult(
        case_count=len(cases),
        mae_mw=total_abs_error / len(cases),
    )
