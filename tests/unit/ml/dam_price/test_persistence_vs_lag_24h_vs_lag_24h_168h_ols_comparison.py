"""Aligned three-way persistence-versus-one-feature-versus-two-feature DAM Price MAE comparison."""

from __future__ import annotations

import inspect
from dataclasses import MISSING, FrozenInstanceError, fields
from datetime import UTC, datetime
from decimal import Decimal

import pytest

# ``energy_trading.domain.models`` must initialize before
# ``energy_trading.domain.value_objects`` because value-object modules import
# canonical models during their own initialization. Importing the models
# package explicitly keeps that pre-existing order.
import energy_trading.domain.models  # noqa: F401
from energy_trading.application.errors import InvalidRequestError
from energy_trading.domain.value_objects.money import EnergyPrice
from energy_trading.ml.dam_price import persistence_vs_lag_24h_vs_lag_24h_168h_ols_comparison
from energy_trading.ml.dam_price.lag_24h_168h_linear_regression_prediction import (
    DAMPriceLag24h168hLinearRegressionPrediction,
)
from energy_trading.ml.dam_price.lag_24h_linear_regression_prediction import (
    DAMPriceLag24hLinearRegressionPrediction,
)
from energy_trading.ml.dam_price.persistence_vs_lag_24h_vs_lag_24h_168h_ols_comparison import (
    DAMPricePersistenceVsLag24hVsLag24h168hOLSMAEComparison,
    compare_dam_price_persistence_vs_lag_24h_vs_lag_24h_168h_ols_mae,
)
from energy_trading.ml.dam_price.previous_day_persistence_backtest import (
    PreviousDayPersistenceBacktestCase,
)

_PREFIX = "DAM Price persistence-versus-one-feature-versus-two-feature OLS MAE comparison requires "
_EMPTY_ALL_MESSAGE = _PREFIX + "a non-empty aligned cohort."
_EMPTY_PERSISTENCE_MESSAGE = _PREFIX + "a non-empty persistence cohort."
_EMPTY_LAG_24H_MESSAGE = _PREFIX + "a non-empty one-feature cohort."
_EMPTY_LAG_24H_168H_MESSAGE = _PREFIX + "a non-empty two-feature cohort."
_UNEQUAL_LENGTH_MESSAGE = _PREFIX + "equal persistence, one-feature, and two-feature case counts."
_MIXED_PERSISTENCE_MARKET_MESSAGE = _PREFIX + "persistence cases from exactly one market."
_MIXED_LAG_24H_MARKET_MESSAGE = _PREFIX + "one-feature predictions from exactly one market."
_MIXED_LAG_24H_168H_MARKET_MESSAGE = _PREFIX + "two-feature predictions from exactly one market."
_MARKET_MISMATCH_MESSAGE = (
    _PREFIX + "persistence cases, one-feature predictions, and two-feature predictions from "
    "the same market."
)
_PERSISTENCE_CURRENCY_COHERENCE_MESSAGE = (
    _PREFIX + "matching predicted and actual persistence currency."
)
_MIXED_PERSISTENCE_CURRENCY_MESSAGE = _PREFIX + "persistence cases in exactly one currency."
_MIXED_LAG_24H_CURRENCY_MESSAGE = _PREFIX + "one-feature predictions in exactly one currency."
_MIXED_LAG_24H_168H_CURRENCY_MESSAGE = _PREFIX + "two-feature predictions in exactly one currency."
_CURRENCY_MISMATCH_MESSAGE = (
    _PREFIX + "persistence cases, one-feature predictions, and two-feature predictions in the "
    "same currency."
)
_DUPLICATE_PERSISTENCE_TIMESTAMP_MESSAGE = _PREFIX + "unique persistence target timestamps."
_DUPLICATE_LAG_24H_TIMESTAMP_MESSAGE = _PREFIX + "unique one-feature target timestamps."
_DUPLICATE_LAG_24H_168H_TIMESTAMP_MESSAGE = _PREFIX + "unique two-feature target timestamps."
_OUT_OF_ORDER_PERSISTENCE_MESSAGE = _PREFIX + "strictly increasing persistence target timestamps."
_OUT_OF_ORDER_LAG_24H_MESSAGE = _PREFIX + "strictly increasing one-feature target timestamps."
_OUT_OF_ORDER_LAG_24H_168H_MESSAGE = _PREFIX + "strictly increasing two-feature target timestamps."
_TIMESTAMP_MISMATCH_MESSAGE = _PREFIX + "matching target timestamps at each aligned index."
_ACTUAL_MISMATCH_MESSAGE = _PREFIX + "matching actual price amounts at each aligned index."

# Published evaluator messages, used to prove evaluator failures propagate unchanged.
_LAG_24H_EVALUATOR_NON_FINITE_MESSAGE = (
    "DAM Price lag-24h linear regression MAE evaluation requires finite predicted and actual "
    "values."
)
_LAG_24H_168H_EVALUATOR_NON_FINITE_MESSAGE = (
    "DAM Price 24h+168h linear regression MAE evaluation requires finite predicted and "
    "actual values."
)

FIVE_FIELDS = (
    "case_count",
    "currency",
    "persistence_mae_amount_per_mwh",
    "lag_24h_mae_amount_per_mwh",
    "lag_24h_168h_mae_amount_per_mwh",
)

_EVALUATOR_NAMES = (
    "evaluate_previous_day_persistence_mae",
    "evaluate_dam_price_lag_24h_linear_regression_mae",
    "evaluate_dam_price_lag_24h_168h_linear_regression_mae",
)


def _ts(day: int, hour: int = 16) -> datetime:
    return datetime(2026, 10, day, hour, 0, 0, tzinfo=UTC)


def _price(amount: str, *, currency: str = "AMD") -> EnergyPrice:
    return EnergyPrice(amount_per_mwh=Decimal(amount), currency=currency)


def _case(
    *,
    day: int,
    predicted: str,
    actual: str,
    market_id: str = "market-1",
    predicted_currency: str = "AMD",
    actual_currency: str = "AMD",
) -> PreviousDayPersistenceBacktestCase:
    return PreviousDayPersistenceBacktestCase(
        market_id=market_id,
        target_timestamp=_ts(day),
        predicted_price=_price(predicted, currency=predicted_currency),
        actual_price=_price(actual, currency=actual_currency),
    )


def _lag_24h(
    *,
    day: int,
    predicted: str,
    actual: str,
    market_id: str = "market-1",
    currency: str = "AMD",
) -> DAMPriceLag24hLinearRegressionPrediction:
    return DAMPriceLag24hLinearRegressionPrediction(
        market_id=market_id,
        currency=currency,
        target_timestamp=_ts(day),
        predicted_amount_per_mwh=Decimal(predicted),
        actual_amount_per_mwh=Decimal(actual),
    )


def _lag_24h_168h(
    *,
    day: int,
    predicted: str,
    actual: str,
    market_id: str = "market-1",
    currency: str = "AMD",
) -> DAMPriceLag24h168hLinearRegressionPrediction:
    return DAMPriceLag24h168hLinearRegressionPrediction(
        market_id=market_id,
        currency=currency,
        target_timestamp=_ts(day),
        predicted_amount_per_mwh=Decimal(predicted),
        actual_amount_per_mwh=Decimal(actual),
    )


def _compare(
    persistence_cases: tuple[PreviousDayPersistenceBacktestCase, ...],
    lag_24h_predictions: tuple[DAMPriceLag24hLinearRegressionPrediction, ...],
    lag_24h_168h_predictions: tuple[DAMPriceLag24h168hLinearRegressionPrediction, ...],
) -> DAMPricePersistenceVsLag24hVsLag24h168hOLSMAEComparison:
    return compare_dam_price_persistence_vs_lag_24h_vs_lag_24h_168h_ols_mae(
        persistence_cases=persistence_cases,
        lag_24h_predictions=lag_24h_predictions,
        lag_24h_168h_predictions=lag_24h_168h_predictions,
    )


def _assert_fails(
    persistence_cases: tuple[PreviousDayPersistenceBacktestCase, ...],
    lag_24h_predictions: tuple[DAMPriceLag24hLinearRegressionPrediction, ...],
    lag_24h_168h_predictions: tuple[DAMPriceLag24h168hLinearRegressionPrediction, ...],
    message: str,
) -> InvalidRequestError:
    with pytest.raises(InvalidRequestError) as captured:
        _compare(persistence_cases, lag_24h_predictions, lag_24h_168h_predictions)
    assert captured.value.message == message
    return captured.value


def _aligned(
    days: tuple[int, ...] = (1, 2),
) -> tuple[
    tuple[PreviousDayPersistenceBacktestCase, ...],
    tuple[DAMPriceLag24hLinearRegressionPrediction, ...],
    tuple[DAMPriceLag24h168hLinearRegressionPrediction, ...],
]:
    return (
        tuple(_case(day=day, predicted="1.00", actual=f"{day}.00") for day in days),
        tuple(_lag_24h(day=day, predicted="2.00", actual=f"{day}.00") for day in days),
        tuple(_lag_24h_168h(day=day, predicted="3.00", actual=f"{day}.00") for day in days),
    )


# --- valid alignment ---------------------------------------------------------


def test_valid_aligned_single_case() -> None:
    result = _compare(
        (_case(day=1, predicted="10.00", actual="12.00"),),
        (_lag_24h(day=1, predicted="11.50", actual="12.00"),),
        (_lag_24h_168h(day=1, predicted="11.00", actual="12.00"),),
    )
    assert result.case_count == 1
    assert result.currency == "AMD"
    assert result.persistence_mae_amount_per_mwh == Decimal("2.00")
    assert result.lag_24h_mae_amount_per_mwh == Decimal("0.50")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("1.00")


def test_valid_aligned_multiple_cases() -> None:
    persistence_cases = (
        _case(day=1, predicted="10.00", actual="12.00"),
        _case(day=2, predicted="17.00", actual="20.00"),
        _case(day=3, predicted="30.00", actual="30.00"),
    )
    lag_24h_predictions = (
        _lag_24h(day=1, predicted="14.00", actual="12.00"),
        _lag_24h(day=2, predicted="18.00", actual="20.00"),
        _lag_24h(day=3, predicted="32.00", actual="30.00"),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h(day=1, predicted="11.00", actual="12.00"),
        _lag_24h_168h(day=2, predicted="19.00", actual="20.00"),
        _lag_24h_168h(day=3, predicted="31.00", actual="30.00"),
    )
    result = _compare(persistence_cases, lag_24h_predictions, lag_24h_168h_predictions)
    assert result.case_count == 3
    assert result.persistence_mae_amount_per_mwh == (Decimal("2") + Decimal("3") + Decimal("0")) / 3
    assert result.lag_24h_mae_amount_per_mwh == (Decimal("2") + Decimal("2") + Decimal("2")) / 3
    assert result.lag_24h_168h_mae_amount_per_mwh == (
        (Decimal("1") + Decimal("1") + Decimal("1")) / 3
    )


def test_exact_case_count_matches_supplied_cohort() -> None:
    assert _compare(*_aligned((1, 2, 3, 4))).case_count == 4


def test_canonical_shared_currency_is_returned() -> None:
    assert _compare(*_aligned((1,))).currency == "AMD"


def test_non_default_shared_currency_is_returned_exactly() -> None:
    result = _compare(
        (
            _case(
                day=1,
                predicted="11.00",
                actual="13.00",
                market_id="market-7",
                predicted_currency="EUR",
                actual_currency="EUR",
            ),
        ),
        (_lag_24h(day=1, predicted="16.00", actual="13.00", market_id="market-7", currency="EUR"),),
        (
            _lag_24h_168h(
                day=1, predicted="12.00", actual="13.00", market_id="market-7", currency="EUR"
            ),
        ),
    )
    assert result.currency == "EUR"
    assert result.persistence_mae_amount_per_mwh == Decimal("2")
    assert result.lag_24h_mae_amount_per_mwh == Decimal("3")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("1")


def test_published_persistence_evaluator_mae_is_exposed() -> None:
    result = _compare(
        (_case(day=1, predicted="10.25", actual="13.75"),),
        (_lag_24h(day=1, predicted="13.75", actual="13.75"),),
        (_lag_24h_168h(day=1, predicted="13.75", actual="13.75"),),
    )
    assert result.persistence_mae_amount_per_mwh == Decimal("3.50")
    assert result.lag_24h_mae_amount_per_mwh == Decimal("0")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("0")


def test_published_one_feature_evaluator_mae_is_exposed() -> None:
    result = _compare(
        (_case(day=1, predicted="13.75", actual="13.75"),),
        (_lag_24h(day=1, predicted="10.25", actual="13.75"),),
        (_lag_24h_168h(day=1, predicted="13.75", actual="13.75"),),
    )
    assert result.persistence_mae_amount_per_mwh == Decimal("0")
    assert result.lag_24h_mae_amount_per_mwh == Decimal("3.50")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("0")


def test_published_two_feature_evaluator_mae_is_exposed() -> None:
    result = _compare(
        (_case(day=1, predicted="13.75", actual="13.75"),),
        (_lag_24h(day=1, predicted="13.75", actual="13.75"),),
        (_lag_24h_168h(day=1, predicted="10.25", actual="13.75"),),
    )
    assert result.persistence_mae_amount_per_mwh == Decimal("0")
    assert result.lag_24h_mae_amount_per_mwh == Decimal("0")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("3.50")


def test_all_three_mae_values_differ() -> None:
    result = _compare(
        (_case(day=1, predicted="10.00", actual="20.00"),),
        (_lag_24h(day=1, predicted="15.00", actual="20.00"),),
        (_lag_24h_168h(day=1, predicted="22.00", actual="20.00"),),
    )
    values = {
        result.persistence_mae_amount_per_mwh,
        result.lag_24h_mae_amount_per_mwh,
        result.lag_24h_168h_mae_amount_per_mwh,
    }
    assert values == {Decimal("10"), Decimal("5"), Decimal("2")}


@pytest.mark.parametrize(
    ("persistence_predicted", "lag_24h_predicted", "lag_24h_168h_predicted"),
    [
        ("19.00", "15.00", "10.00"),
        ("10.00", "19.00", "15.00"),
        ("15.00", "10.00", "19.00"),
    ],
)
def test_any_smallest_metric_changes_only_numeric_fields(
    persistence_predicted: str,
    lag_24h_predicted: str,
    lag_24h_168h_predicted: str,
) -> None:
    result = _compare(
        (_case(day=1, predicted=persistence_predicted, actual="20.00"),),
        (_lag_24h(day=1, predicted=lag_24h_predicted, actual="20.00"),),
        (_lag_24h_168h(day=1, predicted=lag_24h_168h_predicted, actual="20.00"),),
    )
    assert result.persistence_mae_amount_per_mwh == Decimal("20.00") - Decimal(
        persistence_predicted
    )
    assert result.lag_24h_mae_amount_per_mwh == Decimal("20.00") - Decimal(lag_24h_predicted)
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("20.00") - Decimal(
        lag_24h_168h_predicted
    )
    assert tuple(item.name for item in fields(result)) == FIVE_FIELDS
    for absent in ("winner", "champion", "preferred_model", "best_model", "rank"):
        assert not hasattr(result, absent)


def test_equal_mae_values_produce_no_tie_policy() -> None:
    result = _compare(
        (_case(day=1, predicted="10.00", actual="14.00"),),
        (_lag_24h(day=1, predicted="18.00", actual="14.00"),),
        (_lag_24h_168h(day=1, predicted="10.00", actual="14.00"),),
    )
    assert result.persistence_mae_amount_per_mwh == Decimal("4")
    assert result.lag_24h_mae_amount_per_mwh == Decimal("4")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("4")
    assert not hasattr(result, "tie")
    assert tuple(item.name for item in fields(result)) == FIVE_FIELDS


def test_negative_persistence_prediction_is_valid() -> None:
    result = _compare(
        (_case(day=1, predicted="-15.00", actual="5.00"),),
        (_lag_24h(day=1, predicted="5.00", actual="5.00"),),
        (_lag_24h_168h(day=1, predicted="5.00", actual="5.00"),),
    )
    assert result.persistence_mae_amount_per_mwh == Decimal("20")


def test_negative_one_feature_prediction_is_valid() -> None:
    result = _compare(
        (_case(day=1, predicted="5.00", actual="5.00"),),
        (_lag_24h(day=1, predicted="-15.00", actual="5.00"),),
        (_lag_24h_168h(day=1, predicted="5.00", actual="5.00"),),
    )
    assert result.lag_24h_mae_amount_per_mwh == Decimal("20")


def test_negative_two_feature_prediction_is_valid() -> None:
    result = _compare(
        (_case(day=1, predicted="5.00", actual="5.00"),),
        (_lag_24h(day=1, predicted="5.00", actual="5.00"),),
        (_lag_24h_168h(day=1, predicted="-15.00", actual="5.00"),),
    )
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("20")


def test_negative_actual_values_are_valid() -> None:
    result = _compare(
        (_case(day=1, predicted="10.00", actual="-12.00"),),
        (_lag_24h(day=1, predicted="0.00", actual="-12.00"),),
        (_lag_24h_168h(day=1, predicted="11.00", actual="-12.00"),),
    )
    assert result.persistence_mae_amount_per_mwh == Decimal("22")
    assert result.lag_24h_mae_amount_per_mwh == Decimal("12")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("23")


def test_both_negative_predictions_and_actuals_are_valid() -> None:
    result = _compare(
        (_case(day=1, predicted="-20.00", actual="-15.00"),),
        (_lag_24h(day=1, predicted="-16.00", actual="-15.00"),),
        (_lag_24h_168h(day=1, predicted="-18.00", actual="-15.00"),),
    )
    assert result.persistence_mae_amount_per_mwh == Decimal("5")
    assert result.lag_24h_mae_amount_per_mwh == Decimal("1")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("3")


def test_zero_actual_prices_are_valid() -> None:
    result = _compare(
        (_case(day=1, predicted="0.00", actual="0.00"),),
        (_lag_24h(day=1, predicted="-1.00", actual="0.00"),),
        (_lag_24h_168h(day=1, predicted="2.00", actual="0.00"),),
    )
    assert result.persistence_mae_amount_per_mwh == Decimal("0")
    assert result.lag_24h_mae_amount_per_mwh == Decimal("1")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("2")


def test_all_predicted_values_are_explicitly_allowed_to_differ() -> None:
    persistence_cases = (_case(day=1, predicted="1.00", actual="10.00"),)
    lag_24h_predictions = (_lag_24h(day=1, predicted="7.00", actual="10.00"),)
    lag_24h_168h_predictions = (_lag_24h_168h(day=1, predicted="9.00", actual="10.00"),)
    predicted = {
        persistence_cases[0].predicted_price.amount_per_mwh,
        lag_24h_predictions[0].predicted_amount_per_mwh,
        lag_24h_168h_predictions[0].predicted_amount_per_mwh,
    }
    assert len(predicted) == 3
    result = _compare(persistence_cases, lag_24h_predictions, lag_24h_168h_predictions)
    assert result.persistence_mae_amount_per_mwh == Decimal("9")
    assert result.lag_24h_mae_amount_per_mwh == Decimal("3")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("1")


# --- cardinality -------------------------------------------------------------


def test_all_three_empty_cohorts_fail_closed() -> None:
    _assert_fails((), (), (), _EMPTY_ALL_MESSAGE)


def test_empty_persistence_cohort_fails_closed() -> None:
    _, lag_24h, lag_24h_168h = _aligned((1,))
    _assert_fails((), lag_24h, lag_24h_168h, _EMPTY_PERSISTENCE_MESSAGE)


def test_empty_one_feature_cohort_fails_closed() -> None:
    persistence, _, lag_24h_168h = _aligned((1,))
    _assert_fails(persistence, (), lag_24h_168h, _EMPTY_LAG_24H_MESSAGE)


def test_empty_two_feature_cohort_fails_closed() -> None:
    persistence, lag_24h, _ = _aligned((1,))
    _assert_fails(persistence, lag_24h, (), _EMPTY_LAG_24H_168H_MESSAGE)


def test_only_persistence_populated_fails_on_first_empty_cohort() -> None:
    persistence, _, _ = _aligned((1,))
    _assert_fails(persistence, (), (), _EMPTY_LAG_24H_MESSAGE)


def test_only_one_feature_populated_fails_on_first_empty_cohort() -> None:
    _, lag_24h, _ = _aligned((1,))
    _assert_fails((), lag_24h, (), _EMPTY_PERSISTENCE_MESSAGE)


def test_only_two_feature_populated_fails_on_first_empty_cohort() -> None:
    _, _, lag_24h_168h = _aligned((1,))
    _assert_fails((), (), lag_24h_168h, _EMPTY_PERSISTENCE_MESSAGE)


@pytest.mark.parametrize(
    ("persistence_days", "lag_24h_days", "lag_24h_168h_days"),
    [
        ((1, 2), (1,), (1,)),
        ((1,), (1, 2), (1,)),
        ((1,), (1,), (1, 2)),
        ((1, 2), (1, 2), (1,)),
        ((1, 2, 3), (1, 2), (1,)),
    ],
)
def test_unequal_cohort_lengths_fail_closed_without_truncation(
    persistence_days: tuple[int, ...],
    lag_24h_days: tuple[int, ...],
    lag_24h_168h_days: tuple[int, ...],
) -> None:
    _assert_fails(
        _aligned(persistence_days)[0],
        _aligned(lag_24h_days)[1],
        _aligned(lag_24h_168h_days)[2],
        _UNEQUAL_LENGTH_MESSAGE,
    )


# --- market identity ---------------------------------------------------------


def test_mixed_persistence_markets_fail_closed_without_leaking_ids() -> None:
    _, lag_24h, lag_24h_168h = _aligned((1, 2))
    error = _assert_fails(
        (
            _case(day=1, predicted="1.00", actual="1.00", market_id="market-alpha"),
            _case(day=2, predicted="1.00", actual="2.00", market_id="market-beta"),
        ),
        lag_24h,
        lag_24h_168h,
        _MIXED_PERSISTENCE_MARKET_MESSAGE,
    )
    assert "market-alpha" not in error.message
    assert "market-beta" not in error.message


def test_mixed_one_feature_markets_fail_closed() -> None:
    persistence, _, lag_24h_168h = _aligned((1, 2))
    _assert_fails(
        persistence,
        (
            _lag_24h(day=1, predicted="2.00", actual="1.00", market_id="market-alpha"),
            _lag_24h(day=2, predicted="2.00", actual="2.00", market_id="market-beta"),
        ),
        lag_24h_168h,
        _MIXED_LAG_24H_MARKET_MESSAGE,
    )


def test_mixed_two_feature_markets_fail_closed() -> None:
    persistence, lag_24h, _ = _aligned((1, 2))
    _assert_fails(
        persistence,
        lag_24h,
        (
            _lag_24h_168h(day=1, predicted="3.00", actual="1.00", market_id="market-alpha"),
            _lag_24h_168h(day=2, predicted="3.00", actual="2.00", market_id="market-beta"),
        ),
        _MIXED_LAG_24H_168H_MARKET_MESSAGE,
    )


@pytest.mark.parametrize(
    ("persistence_market", "lag_24h_market", "lag_24h_168h_market"),
    [
        ("market-alpha", "market-beta", "market-beta"),
        ("market-alpha", "market-alpha", "market-beta"),
        ("market-beta", "market-alpha", "market-beta"),
    ],
)
def test_cross_cohort_market_mismatch_fails_closed_without_leaking_ids(
    persistence_market: str,
    lag_24h_market: str,
    lag_24h_168h_market: str,
) -> None:
    error = _assert_fails(
        (_case(day=1, predicted="1.00", actual="1.00", market_id=persistence_market),),
        (_lag_24h(day=1, predicted="1.00", actual="1.00", market_id=lag_24h_market),),
        (_lag_24h_168h(day=1, predicted="1.00", actual="1.00", market_id=lag_24h_168h_market),),
        _MARKET_MISMATCH_MESSAGE,
    )
    assert "market-alpha" not in error.message
    assert "market-beta" not in error.message


# --- currency ----------------------------------------------------------------


def test_persistence_predicted_actual_currency_incoherence_fails_closed() -> None:
    _, lag_24h, lag_24h_168h = _aligned((1,))
    error = _assert_fails(
        (_case(day=1, predicted="1.00", actual="1.00", actual_currency="EUR"),),
        lag_24h,
        lag_24h_168h,
        _PERSISTENCE_CURRENCY_COHERENCE_MESSAGE,
    )
    assert "AMD" not in error.message
    assert "EUR" not in error.message


def test_mixed_persistence_currencies_fail_closed() -> None:
    _, lag_24h, lag_24h_168h = _aligned((1, 2))
    error = _assert_fails(
        (
            _case(day=1, predicted="1.00", actual="1.00"),
            _case(
                day=2,
                predicted="1.00",
                actual="2.00",
                predicted_currency="EUR",
                actual_currency="EUR",
            ),
        ),
        lag_24h,
        lag_24h_168h,
        _MIXED_PERSISTENCE_CURRENCY_MESSAGE,
    )
    assert "AMD" not in error.message
    assert "EUR" not in error.message


def test_mixed_one_feature_currencies_fail_closed() -> None:
    persistence, _, lag_24h_168h = _aligned((1, 2))
    error = _assert_fails(
        persistence,
        (
            _lag_24h(day=1, predicted="2.00", actual="1.00"),
            _lag_24h(day=2, predicted="2.00", actual="2.00", currency="EUR"),
        ),
        lag_24h_168h,
        _MIXED_LAG_24H_CURRENCY_MESSAGE,
    )
    assert "AMD" not in error.message
    assert "EUR" not in error.message


def test_mixed_two_feature_currencies_fail_closed() -> None:
    persistence, lag_24h, _ = _aligned((1, 2))
    error = _assert_fails(
        persistence,
        lag_24h,
        (
            _lag_24h_168h(day=1, predicted="3.00", actual="1.00"),
            _lag_24h_168h(day=2, predicted="3.00", actual="2.00", currency="EUR"),
        ),
        _MIXED_LAG_24H_168H_CURRENCY_MESSAGE,
    )
    assert "AMD" not in error.message
    assert "EUR" not in error.message


@pytest.mark.parametrize(
    ("persistence_currency", "lag_24h_currency", "lag_24h_168h_currency"),
    [
        ("AMD", "EUR", "EUR"),
        ("AMD", "AMD", "EUR"),
        ("EUR", "AMD", "EUR"),
    ],
)
def test_cross_cohort_currency_mismatch_fails_closed_without_fx(
    persistence_currency: str,
    lag_24h_currency: str,
    lag_24h_168h_currency: str,
) -> None:
    error = _assert_fails(
        (
            _case(
                day=1,
                predicted="1.00",
                actual="1.00",
                predicted_currency=persistence_currency,
                actual_currency=persistence_currency,
            ),
        ),
        (_lag_24h(day=1, predicted="1.00", actual="1.00", currency=lag_24h_currency),),
        (_lag_24h_168h(day=1, predicted="1.00", actual="1.00", currency=lag_24h_168h_currency),),
        _CURRENCY_MISMATCH_MESSAGE,
    )
    assert "AMD" not in error.message
    assert "EUR" not in error.message


# --- chronology --------------------------------------------------------------


def test_duplicate_persistence_timestamps_fail_closed() -> None:
    _, lag_24h, lag_24h_168h = _aligned((1, 2))
    _assert_fails(
        (
            _case(day=1, predicted="1.00", actual="1.00"),
            _case(day=1, predicted="1.00", actual="2.00"),
        ),
        lag_24h,
        lag_24h_168h,
        _DUPLICATE_PERSISTENCE_TIMESTAMP_MESSAGE,
    )


def test_out_of_order_persistence_timestamps_fail_closed() -> None:
    _, lag_24h, lag_24h_168h = _aligned((1, 3))
    _assert_fails(
        (
            _case(day=3, predicted="1.00", actual="3.00"),
            _case(day=1, predicted="1.00", actual="1.00"),
        ),
        lag_24h,
        lag_24h_168h,
        _OUT_OF_ORDER_PERSISTENCE_MESSAGE,
    )


def test_duplicate_one_feature_timestamps_fail_closed() -> None:
    persistence, _, lag_24h_168h = _aligned((1, 2))
    _assert_fails(
        persistence,
        (
            _lag_24h(day=1, predicted="2.00", actual="1.00"),
            _lag_24h(day=1, predicted="2.00", actual="2.00"),
        ),
        lag_24h_168h,
        _DUPLICATE_LAG_24H_TIMESTAMP_MESSAGE,
    )


def test_out_of_order_one_feature_timestamps_fail_closed() -> None:
    persistence, _, lag_24h_168h = _aligned((1, 3))
    _assert_fails(
        persistence,
        (
            _lag_24h(day=3, predicted="2.00", actual="3.00"),
            _lag_24h(day=1, predicted="2.00", actual="1.00"),
        ),
        lag_24h_168h,
        _OUT_OF_ORDER_LAG_24H_MESSAGE,
    )


def test_duplicate_two_feature_timestamps_fail_closed() -> None:
    persistence, lag_24h, _ = _aligned((1, 2))
    _assert_fails(
        persistence,
        lag_24h,
        (
            _lag_24h_168h(day=1, predicted="3.00", actual="1.00"),
            _lag_24h_168h(day=1, predicted="3.00", actual="2.00"),
        ),
        _DUPLICATE_LAG_24H_168H_TIMESTAMP_MESSAGE,
    )


def test_out_of_order_two_feature_timestamps_fail_closed() -> None:
    persistence, lag_24h, _ = _aligned((1, 3))
    _assert_fails(
        persistence,
        lag_24h,
        (
            _lag_24h_168h(day=3, predicted="3.00", actual="3.00"),
            _lag_24h_168h(day=1, predicted="3.00", actual="1.00"),
        ),
        _OUT_OF_ORDER_LAG_24H_168H_MESSAGE,
    )


def test_same_timestamps_in_different_order_fail_rather_than_realign() -> None:
    # The same timestamp set in reversed order in one cohort must fail rather
    # than being sorted into alignment.
    persistence, lag_24h, lag_24h_168h = _aligned((1, 2))
    _assert_fails(
        persistence,
        (lag_24h[1], lag_24h[0]),
        lag_24h_168h,
        _OUT_OF_ORDER_LAG_24H_MESSAGE,
    )


# --- positional alignment ----------------------------------------------------


def test_persistence_vs_one_feature_timestamp_mismatch_fails_closed() -> None:
    _assert_fails(
        (_case(day=1, predicted="1.00", actual="1.00"),),
        (_lag_24h(day=5, predicted="1.00", actual="1.00"),),
        (_lag_24h_168h(day=1, predicted="1.00", actual="1.00"),),
        _TIMESTAMP_MISMATCH_MESSAGE,
    )


def test_persistence_vs_two_feature_timestamp_mismatch_fails_closed() -> None:
    _assert_fails(
        (_case(day=1, predicted="1.00", actual="1.00"),),
        (_lag_24h(day=1, predicted="1.00", actual="1.00"),),
        (_lag_24h_168h(day=5, predicted="1.00", actual="1.00"),),
        _TIMESTAMP_MISMATCH_MESSAGE,
    )


def test_one_feature_vs_two_feature_timestamp_mismatch_fails_closed() -> None:
    _assert_fails(
        (_case(day=1, predicted="1.00", actual="1.00"),),
        (_lag_24h(day=4, predicted="1.00", actual="1.00"),),
        (_lag_24h_168h(day=5, predicted="1.00", actual="1.00"),),
        _TIMESTAMP_MISMATCH_MESSAGE,
    )


def test_shifted_timestamps_fail_rather_than_intersect() -> None:
    # Each cohort is individually strictly chronological, so only positional
    # identity can fail. Overlapping timestamps must not be intersected.
    persistence = _aligned((2, 3))[0]
    lag_24h = _aligned((2, 3))[1]
    lag_24h_168h = _aligned((1, 2))[2]
    _assert_fails(persistence, lag_24h, lag_24h_168h, _TIMESTAMP_MISMATCH_MESSAGE)


def test_persistence_vs_one_feature_actual_mismatch_fails_closed() -> None:
    _assert_fails(
        (_case(day=1, predicted="1.00", actual="5.00"),),
        (_lag_24h(day=1, predicted="1.00", actual="6.00"),),
        (_lag_24h_168h(day=1, predicted="1.00", actual="5.00"),),
        _ACTUAL_MISMATCH_MESSAGE,
    )


def test_persistence_vs_two_feature_actual_mismatch_fails_closed() -> None:
    _assert_fails(
        (_case(day=1, predicted="1.00", actual="5.00"),),
        (_lag_24h(day=1, predicted="1.00", actual="5.00"),),
        (_lag_24h_168h(day=1, predicted="1.00", actual="6.00"),),
        _ACTUAL_MISMATCH_MESSAGE,
    )


def test_one_feature_vs_two_feature_actual_mismatch_fails_closed() -> None:
    _assert_fails(
        (_case(day=1, predicted="1.00", actual="5.00"),),
        (_lag_24h(day=1, predicted="1.00", actual="6.00"),),
        (_lag_24h_168h(day=1, predicted="1.00", actual="7.00"),),
        _ACTUAL_MISMATCH_MESSAGE,
    )


def test_actual_mismatch_at_later_index_fails_closed() -> None:
    persistence, lag_24h, _ = _aligned((1, 2))
    _assert_fails(
        persistence,
        lag_24h,
        (
            _lag_24h_168h(day=1, predicted="3.00", actual="1.00"),
            _lag_24h_168h(day=2, predicted="3.00", actual="2.01"),
        ),
        _ACTUAL_MISMATCH_MESSAGE,
    )


def test_actual_price_mismatch_message_contains_no_amount() -> None:
    error = _assert_fails(
        (_case(day=1, predicted="1.00", actual="111.11"),),
        (_lag_24h(day=1, predicted="1.00", actual="111.11"),),
        (_lag_24h_168h(day=1, predicted="1.00", actual="222.22"),),
        _ACTUAL_MISMATCH_MESSAGE,
    )
    assert "111.11" not in error.message
    assert "222.22" not in error.message


def test_timestamp_mismatch_message_contains_no_timestamp_or_index() -> None:
    error = _assert_fails(
        (_case(day=1, predicted="1.00", actual="1.00"),),
        (_lag_24h(day=1, predicted="1.00", actual="1.00"),),
        (_lag_24h_168h(day=9, predicted="1.00", actual="1.00"),),
        _TIMESTAMP_MISMATCH_MESSAGE,
    )
    assert "2026" not in error.message
    assert "[0]" not in error.message


def test_exact_decimal_actual_equality_succeeds_without_conversion() -> None:
    result = _compare(
        (_case(day=1, predicted="1.00", actual="0.10"),),
        (_lag_24h(day=1, predicted="1.00", actual="0.100"),),
        (_lag_24h_168h(day=1, predicted="1.00", actual="0.1"),),
    )
    assert result.case_count == 1


def test_near_equal_actual_amounts_are_not_tolerated() -> None:
    _assert_fails(
        (_case(day=1, predicted="1.00", actual="0.1"),),
        (_lag_24h(day=1, predicted="1.00", actual="0.1000000000000000000001"),),
        (_lag_24h_168h(day=1, predicted="1.00", actual="0.1"),),
        _ACTUAL_MISMATCH_MESSAGE,
    )


# --- delegated scoring -------------------------------------------------------


def _install_failing_evaluator(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    sentinel: InvalidRequestError,
) -> None:
    def _failing_evaluator(**_: object) -> object:
        raise sentinel

    monkeypatch.setattr(
        persistence_vs_lag_24h_vs_lag_24h_168h_ols_comparison, name, _failing_evaluator
    )


def test_persistence_evaluator_failure_propagates_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Every published persistence-evaluator guard is already proven by
    # alignment, so a sentinel failure proves the comparison neither wraps nor
    # swallows evaluator exceptions.
    sentinel = InvalidRequestError("persistence evaluator sentinel failure")
    _install_failing_evaluator(monkeypatch, "evaluate_previous_day_persistence_mae", sentinel)
    with pytest.raises(InvalidRequestError) as captured:
        _compare(*_aligned((1,)))
    assert captured.value is sentinel


def test_one_feature_evaluator_failure_propagates_unchanged() -> None:
    # Alignment passes (actuals agree), so the published one-feature
    # evaluator's own non-finite guard is what fails closed.
    _assert_fails(
        (_case(day=1, predicted="1.00", actual="1.00"),),
        (_lag_24h(day=1, predicted="Infinity", actual="1.00"),),
        (_lag_24h_168h(day=1, predicted="1.00", actual="1.00"),),
        _LAG_24H_EVALUATOR_NON_FINITE_MESSAGE,
    )


def test_two_feature_evaluator_failure_propagates_unchanged() -> None:
    _assert_fails(
        (_case(day=1, predicted="1.00", actual="1.00"),),
        (_lag_24h(day=1, predicted="1.00", actual="1.00"),),
        (_lag_24h_168h(day=1, predicted="Infinity", actual="1.00"),),
        _LAG_24H_168H_EVALUATOR_NON_FINITE_MESSAGE,
    )


@pytest.mark.parametrize("name", _EVALUATOR_NAMES)
def test_monkeypatched_evaluator_failure_propagates_by_identity(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
) -> None:
    sentinel = InvalidRequestError("evaluator sentinel failure")
    _install_failing_evaluator(monkeypatch, name, sentinel)
    with pytest.raises(InvalidRequestError) as captured:
        _compare(*_aligned((1, 2)))
    assert captured.value is sentinel


def test_each_evaluator_is_called_exactly_once_with_its_own_cohort(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    module = persistence_vs_lag_24h_vs_lag_24h_168h_ols_comparison
    for name in _EVALUATOR_NAMES:
        original = getattr(module, name)

        def _recording(
            *, _name: str = name, _original: object = original, **kwargs: object
        ) -> object:
            calls.append((_name, kwargs))
            return _original(**kwargs)  # type: ignore[operator]

        monkeypatch.setattr(module, name, _recording)
    persistence, lag_24h, lag_24h_168h = _aligned((1, 2))
    _compare(persistence, lag_24h, lag_24h_168h)
    assert [name for name, _ in calls] == list(_EVALUATOR_NAMES)
    assert calls[0][1] == {"cases": persistence}
    assert calls[0][1]["cases"] is persistence
    assert calls[1][1] == {"predictions": lag_24h}
    assert calls[1][1]["predictions"] is lag_24h
    assert calls[2][1] == {"predictions": lag_24h_168h}
    assert calls[2][1]["predictions"] is lag_24h_168h


def test_no_evaluator_runs_when_alignment_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[str] = []
    module = persistence_vs_lag_24h_vs_lag_24h_168h_ols_comparison
    for name in _EVALUATOR_NAMES:

        def _recording(*, _name: str = name, **_: object) -> object:
            called.append(_name)
            raise AssertionError("evaluator must not run")

        monkeypatch.setattr(module, name, _recording)
    _assert_fails(
        (_case(day=1, predicted="1.00", actual="5.00"),),
        (_lag_24h(day=1, predicted="1.00", actual="5.00"),),
        (_lag_24h_168h(day=1, predicted="1.00", actual="6.00"),),
        _ACTUAL_MISMATCH_MESSAGE,
    )
    _assert_fails((), (), (), _EMPTY_ALL_MESSAGE)
    assert called == []


def test_metric_values_are_decimal_not_float() -> None:
    result = _compare(
        (_case(day=1, predicted="100.10", actual="200.33"),),
        (_lag_24h(day=1, predicted="200.00", actual="200.33"),),
        (_lag_24h_168h(day=1, predicted="200.33", actual="200.33"),),
    )
    for value in (
        result.persistence_mae_amount_per_mwh,
        result.lag_24h_mae_amount_per_mwh,
        result.lag_24h_168h_mae_amount_per_mwh,
    ):
        assert isinstance(value, Decimal)
        assert not isinstance(value, float)
    assert result.persistence_mae_amount_per_mwh == Decimal("100.23")
    assert result.lag_24h_mae_amount_per_mwh == Decimal("0.33")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("0")


# --- purity and contract -----------------------------------------------------


def test_input_cohorts_and_objects_are_not_modified() -> None:
    case = _case(day=1, predicted="10.00", actual="12.00")
    lag_24h_prediction = _lag_24h(day=1, predicted="13.00", actual="12.00")
    lag_24h_168h_prediction = _lag_24h_168h(day=1, predicted="11.00", actual="12.00")
    persistence_cases = (case,)
    lag_24h_predictions = (lag_24h_prediction,)
    lag_24h_168h_predictions = (lag_24h_168h_prediction,)
    _compare(persistence_cases, lag_24h_predictions, lag_24h_168h_predictions)
    assert persistence_cases[0] is case
    assert lag_24h_predictions[0] is lag_24h_prediction
    assert lag_24h_168h_predictions[0] is lag_24h_168h_prediction
    assert case.predicted_price.amount_per_mwh == Decimal("10.00")
    assert case.actual_price.amount_per_mwh == Decimal("12.00")
    assert lag_24h_prediction.predicted_amount_per_mwh == Decimal("13.00")
    assert lag_24h_prediction.actual_amount_per_mwh == Decimal("12.00")
    assert lag_24h_168h_prediction.predicted_amount_per_mwh == Decimal("11.00")
    assert lag_24h_168h_prediction.actual_amount_per_mwh == Decimal("12.00")
    assert lag_24h_prediction.currency == "AMD"
    assert lag_24h_168h_prediction.market_id == "market-1"


def test_repeated_equivalent_calls_are_value_equivalent() -> None:
    cohorts = _aligned((1, 2, 3))
    assert _compare(*cohorts) == _compare(*cohorts)


def test_result_contract_is_frozen_slotted_and_exactly_five_fields_without_defaults() -> None:
    contract_fields = fields(DAMPricePersistenceVsLag24hVsLag24h168hOLSMAEComparison)
    names = tuple(item.name for item in contract_fields)
    assert names == FIVE_FIELDS
    assert DAMPricePersistenceVsLag24hVsLag24h168hOLSMAEComparison.__slots__ == names
    for item in contract_fields:
        assert item.default is MISSING
        assert item.default_factory is MISSING
    with pytest.raises(TypeError):
        DAMPricePersistenceVsLag24hVsLag24h168hOLSMAEComparison()  # type: ignore[call-arg]
    result = _compare(*_aligned((1,)))
    with pytest.raises(FrozenInstanceError):
        result.case_count = 99  # type: ignore[misc]


def test_result_exposes_no_winner_champion_or_improvement_fields() -> None:
    names = {item.name for item in fields(DAMPricePersistenceVsLag24hVsLag24h168hOLSMAEComparison)}
    assert names == set(FIVE_FIELDS)
    forbidden = {
        "market_id",
        "winner",
        "champion",
        "selected_model",
        "preferred_model",
        "best_model",
        "tie",
        "rank",
        "delta",
        "improvement",
        "percentage_improvement",
        "ratio",
        "threshold",
        "score",
        "confidence",
        "significance",
        "mse",
        "rmse",
        "mape",
        "metadata",
    }
    assert forbidden.isdisjoint(names)


def test_comparison_is_synchronous_and_keyword_only() -> None:
    function = compare_dam_price_persistence_vs_lag_24h_vs_lag_24h_168h_ols_mae
    assert not inspect.iscoroutinefunction(function)
    parameters = inspect.signature(function).parameters
    assert tuple(parameters) == (
        "persistence_cases",
        "lag_24h_predictions",
        "lag_24h_168h_predictions",
    )
    for parameter in parameters.values():
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty
    with pytest.raises(TypeError):
        function(*_aligned((1,)))  # type: ignore[misc]
