"""Aligned one-feature versus two-feature OLS DAM Price MAE comparison."""

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
from energy_trading.ml.dam_price.lag_24h_168h_linear_regression_prediction import (
    DAMPriceLag24h168hLinearRegressionPrediction,
)
from energy_trading.ml.dam_price.lag_24h_linear_regression_prediction import (
    DAMPriceLag24hLinearRegressionPrediction,
)
from energy_trading.ml.dam_price.lag_24h_vs_lag_24h_168h_ols_comparison import (
    DAMPriceLag24hVsLag24h168hOLSMAEComparison,
    compare_dam_price_lag_24h_vs_lag_24h_168h_ols_mae,
)

_EMPTY_BOTH_MESSAGE = (
    "DAM Price one-feature versus two-feature OLS MAE comparison requires a non-empty aligned "
    "cohort."
)
_EMPTY_LAG_24H_MESSAGE = (
    "DAM Price one-feature versus two-feature OLS MAE comparison requires a non-empty "
    "one-feature cohort."
)
_EMPTY_LAG_24H_168H_MESSAGE = (
    "DAM Price one-feature versus two-feature OLS MAE comparison requires a non-empty "
    "two-feature cohort."
)
_UNEQUAL_LENGTH_MESSAGE = (
    "DAM Price one-feature versus two-feature OLS MAE comparison requires equal one-feature and "
    "two-feature case counts."
)
_MIXED_LAG_24H_MARKET_MESSAGE = (
    "DAM Price one-feature versus two-feature OLS MAE comparison requires one-feature "
    "predictions from exactly one market."
)
_MIXED_LAG_24H_168H_MARKET_MESSAGE = (
    "DAM Price one-feature versus two-feature OLS MAE comparison requires two-feature "
    "predictions from exactly one market."
)
_MARKET_MISMATCH_MESSAGE = (
    "DAM Price one-feature versus two-feature OLS MAE comparison requires one-feature and "
    "two-feature predictions from the same market."
)
_MIXED_LAG_24H_CURRENCY_MESSAGE = (
    "DAM Price one-feature versus two-feature OLS MAE comparison requires one-feature "
    "predictions in exactly one currency."
)
_MIXED_LAG_24H_168H_CURRENCY_MESSAGE = (
    "DAM Price one-feature versus two-feature OLS MAE comparison requires two-feature "
    "predictions in exactly one currency."
)
_CURRENCY_MISMATCH_MESSAGE = (
    "DAM Price one-feature versus two-feature OLS MAE comparison requires one-feature and "
    "two-feature predictions in the same currency."
)
_DUPLICATE_LAG_24H_TIMESTAMP_MESSAGE = (
    "DAM Price one-feature versus two-feature OLS MAE comparison requires unique one-feature "
    "target timestamps."
)
_DUPLICATE_LAG_24H_168H_TIMESTAMP_MESSAGE = (
    "DAM Price one-feature versus two-feature OLS MAE comparison requires unique two-feature "
    "target timestamps."
)
_OUT_OF_ORDER_LAG_24H_MESSAGE = (
    "DAM Price one-feature versus two-feature OLS MAE comparison requires strictly increasing "
    "one-feature target timestamps."
)
_OUT_OF_ORDER_LAG_24H_168H_MESSAGE = (
    "DAM Price one-feature versus two-feature OLS MAE comparison requires strictly increasing "
    "two-feature target timestamps."
)
_TIMESTAMP_MISMATCH_MESSAGE = (
    "DAM Price one-feature versus two-feature OLS MAE comparison requires matching target "
    "timestamps at each aligned index."
)
_ACTUAL_MISMATCH_MESSAGE = (
    "DAM Price one-feature versus two-feature OLS MAE comparison requires matching actual price "
    "amounts at each aligned index."
)

# Published evaluator messages, used to prove evaluator failures propagate unchanged.
_LAG_24H_EVALUATOR_NON_FINITE_MESSAGE = (
    "DAM Price lag-24h linear regression MAE evaluation requires finite predicted and actual "
    "values."
)
_LAG_24H_168H_EVALUATOR_NON_FINITE_MESSAGE = (
    "DAM Price 24h+168h linear regression MAE evaluation requires finite predicted and "
    "actual values."
)

FOUR_FIELDS = (
    "case_count",
    "currency",
    "lag_24h_mae_amount_per_mwh",
    "lag_24h_168h_mae_amount_per_mwh",
)


def _ts(day: int, hour: int = 16) -> datetime:
    return datetime(2026, 10, day, hour, 0, 0, tzinfo=UTC)


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
    lag_24h_predictions: tuple[DAMPriceLag24hLinearRegressionPrediction, ...],
    lag_24h_168h_predictions: tuple[DAMPriceLag24h168hLinearRegressionPrediction, ...],
) -> DAMPriceLag24hVsLag24h168hOLSMAEComparison:
    return compare_dam_price_lag_24h_vs_lag_24h_168h_ols_mae(
        lag_24h_predictions=lag_24h_predictions,
        lag_24h_168h_predictions=lag_24h_168h_predictions,
    )


def _assert_fails(
    lag_24h_predictions: tuple[DAMPriceLag24hLinearRegressionPrediction, ...],
    lag_24h_168h_predictions: tuple[DAMPriceLag24h168hLinearRegressionPrediction, ...],
    message: str,
) -> InvalidRequestError:
    with pytest.raises(InvalidRequestError) as captured:
        _compare(lag_24h_predictions, lag_24h_168h_predictions)
    assert captured.value.message == message
    return captured.value


def test_valid_aligned_single_case() -> None:
    result = _compare(
        (_lag_24h(day=1, predicted="10.00", actual="12.00"),),
        (_lag_24h_168h(day=1, predicted="11.00", actual="12.00"),),
    )
    assert result.case_count == 1
    assert result.currency == "AMD"
    assert result.lag_24h_mae_amount_per_mwh == Decimal("2.00")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("1.00")


def test_valid_aligned_multiple_cases() -> None:
    lag_24h_predictions = (
        _lag_24h(day=1, predicted="10.00", actual="12.00"),
        _lag_24h(day=2, predicted="17.00", actual="20.00"),
        _lag_24h(day=3, predicted="30.00", actual="30.00"),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h(day=1, predicted="11.00", actual="12.00"),
        _lag_24h_168h(day=2, predicted="19.00", actual="20.00"),
        _lag_24h_168h(day=3, predicted="31.00", actual="30.00"),
    )
    result = _compare(lag_24h_predictions, lag_24h_168h_predictions)
    assert result.case_count == 3
    assert result.lag_24h_mae_amount_per_mwh == (Decimal("2") + Decimal("3") + Decimal("0")) / 3
    assert (
        result.lag_24h_168h_mae_amount_per_mwh == (Decimal("1") + Decimal("1") + Decimal("1")) / 3
    )


def test_exact_case_count_matches_supplied_cohort() -> None:
    lag_24h_predictions = (
        _lag_24h(day=1, predicted="1.00", actual="2.00"),
        _lag_24h(day=2, predicted="3.00", actual="4.00"),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h(day=1, predicted="1.50", actual="2.00"),
        _lag_24h_168h(day=2, predicted="3.50", actual="4.00"),
    )
    assert _compare(lag_24h_predictions, lag_24h_168h_predictions).case_count == 2


def test_shared_currency_is_preserved_exactly() -> None:
    result = _compare(
        (_lag_24h(day=1, predicted="1.00", actual="2.00"),),
        (_lag_24h_168h(day=1, predicted="1.00", actual="2.00"),),
    )
    assert result.currency == "AMD"


def test_non_default_currency_is_preserved_without_conversion() -> None:
    lag_24h_predictions = (
        _lag_24h(day=1, predicted="11.00", actual="13.00", market_id="market-7", currency="EUR"),
        _lag_24h(day=2, predicted="21.00", actual="19.00", market_id="market-7", currency="EUR"),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h(
            day=1, predicted="12.00", actual="13.00", market_id="market-7", currency="EUR"
        ),
        _lag_24h_168h(
            day=2, predicted="18.00", actual="19.00", market_id="market-7", currency="EUR"
        ),
    )
    result = _compare(lag_24h_predictions, lag_24h_168h_predictions)
    assert result.currency == "EUR"
    assert result.lag_24h_mae_amount_per_mwh == Decimal("2")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("1")


def test_published_one_feature_evaluator_mae_is_exposed() -> None:
    result = _compare(
        (_lag_24h(day=1, predicted="10.25", actual="13.75"),),
        (_lag_24h_168h(day=1, predicted="13.75", actual="13.75"),),
    )
    assert result.lag_24h_mae_amount_per_mwh == Decimal("3.50")


def test_published_two_feature_evaluator_mae_is_exposed() -> None:
    result = _compare(
        (_lag_24h(day=1, predicted="13.75", actual="13.75"),),
        (_lag_24h_168h(day=1, predicted="10.25", actual="13.75"),),
    )
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("3.50")


def test_lower_one_feature_mae_produces_no_winner_field() -> None:
    result = _compare(
        (_lag_24h(day=1, predicted="13.00", actual="14.00"),),
        (_lag_24h_168h(day=1, predicted="10.00", actual="14.00"),),
    )
    assert result.lag_24h_mae_amount_per_mwh == Decimal("1")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("4")
    assert not hasattr(result, "winner")
    assert {item.name for item in fields(result)} == set(FOUR_FIELDS)


def test_lower_two_feature_mae_produces_no_winner_field() -> None:
    result = _compare(
        (_lag_24h(day=1, predicted="10.00", actual="14.00"),),
        (_lag_24h_168h(day=1, predicted="13.00", actual="14.00"),),
    )
    assert result.lag_24h_mae_amount_per_mwh == Decimal("4")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("1")
    assert not hasattr(result, "winner")
    assert not hasattr(result, "preferred_model")


def test_equal_mae_values_produce_no_tie_policy() -> None:
    result = _compare(
        (_lag_24h(day=1, predicted="10.00", actual="14.00"),),
        (_lag_24h_168h(day=1, predicted="18.00", actual="14.00"),),
    )
    assert result.lag_24h_mae_amount_per_mwh == result.lag_24h_168h_mae_amount_per_mwh
    assert not hasattr(result, "tie")
    assert {item.name for item in fields(result)} == set(FOUR_FIELDS)


def test_negative_one_feature_prediction_is_valid() -> None:
    result = _compare(
        (_lag_24h(day=1, predicted="-15.00", actual="5.00"),),
        (_lag_24h_168h(day=1, predicted="5.00", actual="5.00"),),
    )
    assert result.lag_24h_mae_amount_per_mwh == Decimal("20")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("0")


def test_negative_two_feature_prediction_is_valid() -> None:
    result = _compare(
        (_lag_24h(day=1, predicted="5.00", actual="5.00"),),
        (_lag_24h_168h(day=1, predicted="-15.00", actual="5.00"),),
    )
    assert result.lag_24h_mae_amount_per_mwh == Decimal("0")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("20")


def test_negative_actual_values_are_valid() -> None:
    result = _compare(
        (_lag_24h(day=1, predicted="10.00", actual="-12.00"),),
        (_lag_24h_168h(day=1, predicted="-11.00", actual="-12.00"),),
    )
    assert result.lag_24h_mae_amount_per_mwh == Decimal("22")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("1")


def test_both_negative_predictions_and_actuals_are_valid() -> None:
    result = _compare(
        (_lag_24h(day=1, predicted="-20.00", actual="-15.00"),),
        (_lag_24h_168h(day=1, predicted="-18.00", actual="-15.00"),),
    )
    assert result.lag_24h_mae_amount_per_mwh == Decimal("5")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("3")


def test_zero_actual_values_are_valid() -> None:
    result = _compare(
        (_lag_24h(day=1, predicted="4.00", actual="0.00"),),
        (_lag_24h_168h(day=1, predicted="2.00", actual="0.00"),),
    )
    assert result.lag_24h_mae_amount_per_mwh == Decimal("4")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("2")


def test_different_predicted_values_are_explicitly_allowed() -> None:
    result = _compare(
        (_lag_24h(day=1, predicted="1.00", actual="10.00"),),
        (_lag_24h_168h(day=1, predicted="9.00", actual="10.00"),),
    )
    assert result.lag_24h_mae_amount_per_mwh == Decimal("9")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("1")


def test_empty_both_cohorts_fail_closed() -> None:
    _assert_fails((), (), _EMPTY_BOTH_MESSAGE)


def test_empty_one_feature_cohort_fails_closed() -> None:
    _assert_fails(
        (),
        (_lag_24h_168h(day=1, predicted="1.00", actual="1.00"),),
        _EMPTY_LAG_24H_MESSAGE,
    )


def test_empty_two_feature_cohort_fails_closed() -> None:
    _assert_fails(
        (_lag_24h(day=1, predicted="1.00", actual="1.00"),),
        (),
        _EMPTY_LAG_24H_168H_MESSAGE,
    )


def test_unequal_cohort_lengths_fail_closed() -> None:
    _assert_fails(
        (
            _lag_24h(day=1, predicted="1.00", actual="1.00"),
            _lag_24h(day=2, predicted="2.00", actual="2.00"),
        ),
        (_lag_24h_168h(day=1, predicted="1.00", actual="1.00"),),
        _UNEQUAL_LENGTH_MESSAGE,
    )


def test_mixed_one_feature_markets_fail_closed_without_leaking_ids() -> None:
    error = _assert_fails(
        (
            _lag_24h(day=1, predicted="1.00", actual="1.00", market_id="market-alpha"),
            _lag_24h(day=2, predicted="2.00", actual="2.00", market_id="market-beta"),
        ),
        (
            _lag_24h_168h(day=1, predicted="1.00", actual="1.00", market_id="market-alpha"),
            _lag_24h_168h(day=2, predicted="2.00", actual="2.00", market_id="market-alpha"),
        ),
        _MIXED_LAG_24H_MARKET_MESSAGE,
    )
    assert "market-alpha" not in error.message
    assert "market-beta" not in error.message


def test_mixed_two_feature_markets_fail_closed() -> None:
    _assert_fails(
        (
            _lag_24h(day=1, predicted="1.00", actual="1.00"),
            _lag_24h(day=2, predicted="2.00", actual="2.00"),
        ),
        (
            _lag_24h_168h(day=1, predicted="1.00", actual="1.00", market_id="market-alpha"),
            _lag_24h_168h(day=2, predicted="2.00", actual="2.00", market_id="market-beta"),
        ),
        _MIXED_LAG_24H_168H_MARKET_MESSAGE,
    )


def test_cross_cohort_market_mismatch_fails_closed_without_leaking_ids() -> None:
    error = _assert_fails(
        (_lag_24h(day=1, predicted="1.00", actual="1.00", market_id="market-alpha"),),
        (_lag_24h_168h(day=1, predicted="1.00", actual="1.00", market_id="market-beta"),),
        _MARKET_MISMATCH_MESSAGE,
    )
    assert "market-alpha" not in error.message
    assert "market-beta" not in error.message


def test_mixed_one_feature_currencies_fail_closed() -> None:
    error = _assert_fails(
        (
            _lag_24h(day=1, predicted="1.00", actual="1.00", currency="AMD"),
            _lag_24h(day=2, predicted="2.00", actual="2.00", currency="EUR"),
        ),
        (
            _lag_24h_168h(day=1, predicted="1.00", actual="1.00"),
            _lag_24h_168h(day=2, predicted="2.00", actual="2.00"),
        ),
        _MIXED_LAG_24H_CURRENCY_MESSAGE,
    )
    assert "AMD" not in error.message
    assert "EUR" not in error.message


def test_mixed_two_feature_currencies_fail_closed() -> None:
    error = _assert_fails(
        (
            _lag_24h(day=1, predicted="1.00", actual="1.00"),
            _lag_24h(day=2, predicted="2.00", actual="2.00"),
        ),
        (
            _lag_24h_168h(day=1, predicted="1.00", actual="1.00", currency="AMD"),
            _lag_24h_168h(day=2, predicted="2.00", actual="2.00", currency="EUR"),
        ),
        _MIXED_LAG_24H_168H_CURRENCY_MESSAGE,
    )
    assert "AMD" not in error.message
    assert "EUR" not in error.message


def test_cross_cohort_currency_mismatch_fails_closed() -> None:
    error = _assert_fails(
        (_lag_24h(day=1, predicted="1.00", actual="1.00", currency="AMD"),),
        (_lag_24h_168h(day=1, predicted="1.00", actual="1.00", currency="EUR"),),
        _CURRENCY_MISMATCH_MESSAGE,
    )
    assert "AMD" not in error.message
    assert "EUR" not in error.message


def test_duplicate_one_feature_timestamps_fail_closed() -> None:
    _assert_fails(
        (
            _lag_24h(day=1, predicted="1.00", actual="1.00"),
            _lag_24h(day=1, predicted="2.00", actual="2.00"),
        ),
        (
            _lag_24h_168h(day=1, predicted="1.00", actual="1.00"),
            _lag_24h_168h(day=2, predicted="2.00", actual="2.00"),
        ),
        _DUPLICATE_LAG_24H_TIMESTAMP_MESSAGE,
    )


def test_out_of_order_one_feature_timestamps_fail_closed() -> None:
    _assert_fails(
        (
            _lag_24h(day=3, predicted="1.00", actual="1.00"),
            _lag_24h(day=1, predicted="2.00", actual="2.00"),
        ),
        (
            _lag_24h_168h(day=1, predicted="1.00", actual="1.00"),
            _lag_24h_168h(day=3, predicted="2.00", actual="2.00"),
        ),
        _OUT_OF_ORDER_LAG_24H_MESSAGE,
    )


def test_duplicate_two_feature_timestamps_fail_closed() -> None:
    _assert_fails(
        (
            _lag_24h(day=1, predicted="1.00", actual="1.00"),
            _lag_24h(day=2, predicted="2.00", actual="2.00"),
        ),
        (
            _lag_24h_168h(day=1, predicted="1.00", actual="1.00"),
            _lag_24h_168h(day=1, predicted="2.00", actual="2.00"),
        ),
        _DUPLICATE_LAG_24H_168H_TIMESTAMP_MESSAGE,
    )


def test_out_of_order_two_feature_timestamps_fail_closed() -> None:
    _assert_fails(
        (
            _lag_24h(day=1, predicted="1.00", actual="1.00"),
            _lag_24h(day=3, predicted="2.00", actual="2.00"),
        ),
        (
            _lag_24h_168h(day=3, predicted="1.00", actual="1.00"),
            _lag_24h_168h(day=1, predicted="2.00", actual="2.00"),
        ),
        _OUT_OF_ORDER_LAG_24H_168H_MESSAGE,
    )


def test_same_timestamps_in_different_order_fail_rather_than_sort() -> None:
    # The two-feature cohort carries the same timestamp set in reversed order;
    # it must fail closed rather than be sorted into alignment.
    _assert_fails(
        (
            _lag_24h(day=1, predicted="1.00", actual="1.00"),
            _lag_24h(day=2, predicted="2.00", actual="2.00"),
        ),
        (
            _lag_24h_168h(day=2, predicted="2.00", actual="2.00"),
            _lag_24h_168h(day=1, predicted="1.00", actual="1.00"),
        ),
        _OUT_OF_ORDER_LAG_24H_168H_MESSAGE,
    )


def test_shifted_timestamps_fail_rather_than_realign() -> None:
    # Both cohorts are individually strictly chronological, so only positional
    # identity can fail. Overlapping timestamps must not be realigned.
    _assert_fails(
        (
            _lag_24h(day=2, predicted="1.00", actual="1.00"),
            _lag_24h(day=3, predicted="2.00", actual="2.00"),
        ),
        (
            _lag_24h_168h(day=1, predicted="1.00", actual="1.00"),
            _lag_24h_168h(day=2, predicted="2.00", actual="2.00"),
        ),
        _TIMESTAMP_MISMATCH_MESSAGE,
    )


def test_pairwise_timestamp_mismatch_fails_closed() -> None:
    _assert_fails(
        (_lag_24h(day=1, predicted="1.00", actual="1.00"),),
        (_lag_24h_168h(day=5, predicted="1.00", actual="1.00"),),
        _TIMESTAMP_MISMATCH_MESSAGE,
    )


def test_pairwise_actual_amount_mismatch_fails_closed() -> None:
    _assert_fails(
        (_lag_24h(day=1, predicted="1.00", actual="5.00"),),
        (_lag_24h_168h(day=1, predicted="1.00", actual="6.00"),),
        _ACTUAL_MISMATCH_MESSAGE,
    )


def test_actual_mismatch_message_contains_no_numeric_actual() -> None:
    error = _assert_fails(
        (_lag_24h(day=1, predicted="1.00", actual="111.11"),),
        (_lag_24h_168h(day=1, predicted="1.00", actual="222.22"),),
        _ACTUAL_MISMATCH_MESSAGE,
    )
    assert "111.11" not in error.message
    assert "222.22" not in error.message


def test_exact_decimal_actual_equality_succeeds_without_conversion() -> None:
    result = _compare(
        (_lag_24h(day=1, predicted="1.00", actual="0.10"),),
        (_lag_24h_168h(day=1, predicted="1.00", actual="0.1"),),
    )
    assert result.case_count == 1
    assert isinstance(result.lag_24h_mae_amount_per_mwh, Decimal)


def test_one_feature_evaluator_failure_propagates_unchanged() -> None:
    # Alignment passes (actuals agree), so the published evaluator's own
    # non-finite guard is what fails closed.
    _assert_fails(
        (_lag_24h(day=1, predicted="NaN", actual="1.00"),),
        (_lag_24h_168h(day=1, predicted="1.00", actual="1.00"),),
        _LAG_24H_EVALUATOR_NON_FINITE_MESSAGE,
    )


def test_two_feature_evaluator_failure_propagates_unchanged() -> None:
    _assert_fails(
        (_lag_24h(day=1, predicted="1.00", actual="1.00"),),
        (_lag_24h_168h(day=1, predicted="Infinity", actual="1.00"),),
        _LAG_24H_168H_EVALUATOR_NON_FINITE_MESSAGE,
    )


def test_repeated_equivalent_calls_are_value_equivalent() -> None:
    lag_24h_predictions = (
        _lag_24h(day=1, predicted="10.00", actual="12.00"),
        _lag_24h(day=2, predicted="20.00", actual="17.00"),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h(day=1, predicted="11.00", actual="12.00"),
        _lag_24h_168h(day=2, predicted="16.00", actual="17.00"),
    )
    assert _compare(lag_24h_predictions, lag_24h_168h_predictions) == _compare(
        lag_24h_predictions, lag_24h_168h_predictions
    )


def test_input_cohorts_and_objects_are_not_modified() -> None:
    lag_24h_prediction = _lag_24h(day=1, predicted="10.00", actual="12.00")
    lag_24h_168h_prediction = _lag_24h_168h(day=1, predicted="11.00", actual="12.00")
    lag_24h_predictions = (lag_24h_prediction,)
    lag_24h_168h_predictions = (lag_24h_168h_prediction,)
    _compare(lag_24h_predictions, lag_24h_168h_predictions)
    assert lag_24h_predictions == (lag_24h_prediction,)
    assert lag_24h_168h_predictions == (lag_24h_168h_prediction,)
    assert lag_24h_prediction.predicted_amount_per_mwh == Decimal("10.00")
    assert lag_24h_prediction.actual_amount_per_mwh == Decimal("12.00")
    assert lag_24h_168h_prediction.predicted_amount_per_mwh == Decimal("11.00")
    assert lag_24h_168h_prediction.actual_amount_per_mwh == Decimal("12.00")
    assert lag_24h_168h_prediction.market_id == "market-1"
    assert lag_24h_168h_prediction.currency == "AMD"


def test_result_contract_is_frozen_slotted_and_exactly_four_fields() -> None:
    result_fields = fields(DAMPriceLag24hVsLag24h168hOLSMAEComparison)
    names = tuple(item.name for item in result_fields)
    assert names == FOUR_FIELDS
    assert DAMPriceLag24hVsLag24h168hOLSMAEComparison.__slots__ == names
    for item in result_fields:
        assert item.default is MISSING
        assert item.default_factory is MISSING
    result = _compare(
        (_lag_24h(day=1, predicted="10.00", actual="12.00"),),
        (_lag_24h_168h(day=1, predicted="11.00", actual="12.00"),),
    )
    with pytest.raises(FrozenInstanceError):
        result.case_count = 99  # type: ignore[misc]


def test_result_exposes_no_winner_champion_or_extra_metric_fields() -> None:
    names = {item.name for item in fields(DAMPriceLag24hVsLag24h168hOLSMAEComparison)}
    assert names == set(FOUR_FIELDS)
    forbidden = {
        "market_id",
        "winner",
        "champion",
        "preferred_model",
        "better_model",
        "improvement",
        "percentage_improvement",
        "delta",
        "ratio",
        "threshold",
        "rank",
        "score",
        "confidence",
        "significance",
        "mse",
        "rmse",
        "mape",
        "metadata",
    }
    assert forbidden.isdisjoint(names)


def test_metric_values_are_decimal_not_float() -> None:
    result = _compare(
        (_lag_24h(day=1, predicted="100.10", actual="200.33"),),
        (_lag_24h_168h(day=1, predicted="200.33", actual="200.33"),),
    )
    assert isinstance(result.lag_24h_mae_amount_per_mwh, Decimal)
    assert isinstance(result.lag_24h_168h_mae_amount_per_mwh, Decimal)
    assert not isinstance(result.lag_24h_mae_amount_per_mwh, float)
    assert not isinstance(result.lag_24h_168h_mae_amount_per_mwh, float)
    assert result.lag_24h_mae_amount_per_mwh == Decimal("100.23")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("0")


def test_comparison_is_synchronous_and_keyword_only() -> None:
    function = compare_dam_price_lag_24h_vs_lag_24h_168h_ols_mae
    assert not inspect.iscoroutinefunction(function)
    parameters = inspect.signature(function).parameters
    assert tuple(parameters) == ("lag_24h_predictions", "lag_24h_168h_predictions")
    for parameter in parameters.values():
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty
