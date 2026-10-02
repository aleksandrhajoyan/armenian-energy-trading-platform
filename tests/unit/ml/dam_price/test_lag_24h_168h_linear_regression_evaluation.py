"""Lag-24h plus lag-168h ordinary-least-squares DAM Price MAE evaluation."""

from __future__ import annotations

import inspect
from dataclasses import MISSING, FrozenInstanceError, fields
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation, Overflow, localcontext

import pytest

# ``energy_trading.domain.models`` must initialize before
# ``energy_trading.domain.value_objects`` because value-object modules import
# canonical models during their own initialization. Importing the models
# package explicitly keeps that pre-existing order.
import energy_trading.domain.models  # noqa: F401
from energy_trading.application.errors import InvalidRequestError
from energy_trading.ml.dam_price.lag_24h_168h_linear_regression_evaluation import (
    DAMPriceLag24h168hLinearRegressionMAEResult,
    evaluate_dam_price_lag_24h_168h_linear_regression_mae,
)
from energy_trading.ml.dam_price.lag_24h_168h_linear_regression_prediction import (
    DAMPriceLag24h168hLinearRegressionPrediction,
)

_EMPTY_PREDICTIONS_MESSAGE = (
    "DAM Price 24h+168h linear regression MAE evaluation requires at least one prediction."
)
_MIXED_MARKET_MESSAGE = (
    "DAM Price 24h+168h linear regression MAE evaluation requires predictions from exactly "
    "one market."
)
_MIXED_CURRENCY_MESSAGE = (
    "DAM Price 24h+168h linear regression MAE evaluation requires predictions in exactly "
    "one currency."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "DAM Price 24h+168h linear regression MAE evaluation requires unique target timestamps."
)
_OUT_OF_ORDER_MESSAGE = (
    "DAM Price 24h+168h linear regression MAE evaluation requires strictly increasing "
    "target timestamps."
)
_NON_FINITE_VALUES_MESSAGE = (
    "DAM Price 24h+168h linear regression MAE evaluation requires finite predicted and "
    "actual values."
)
_NON_FINITE_MAE_MESSAGE = (
    "DAM Price 24h+168h linear regression MAE evaluation requires a finite MAE."
)

THREE_FIELDS = ("case_count", "currency", "mae_amount_per_mwh")


def _ts(day: int, hour: int = 16) -> datetime:
    return datetime(2026, 10, day, hour, 0, 0, tzinfo=UTC)


def _prediction(
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


def _evaluate(
    predictions: tuple[DAMPriceLag24h168hLinearRegressionPrediction, ...],
) -> DAMPriceLag24h168hLinearRegressionMAEResult:
    return evaluate_dam_price_lag_24h_168h_linear_regression_mae(predictions=predictions)


def test_empty_prediction_tuple_fails_closed() -> None:
    with pytest.raises(InvalidRequestError) as captured:
        _evaluate(())
    assert captured.value.message == _EMPTY_PREDICTIONS_MESSAGE


def test_single_zero_error_prediction_has_exact_zero_mae() -> None:
    result = _evaluate((_prediction(day=1, predicted="42.50", actual="42.50"),))
    assert result.case_count == 1
    assert result.currency == "AMD"
    assert result.mae_amount_per_mwh == Decimal("0")
    assert isinstance(result.mae_amount_per_mwh, Decimal)


def test_all_zero_error_cohort_has_exact_zero_mae() -> None:
    predictions = (
        _prediction(day=1, predicted="10.00", actual="10.00"),
        _prediction(day=2, predicted="-3.00", actual="-3.00"),
        _prediction(day=3, predicted="0", actual="0"),
    )
    result = _evaluate(predictions)
    assert result.case_count == 3
    assert result.mae_amount_per_mwh == Decimal("0")


def test_single_non_zero_prediction_uses_exact_absolute_difference() -> None:
    result = _evaluate((_prediction(day=1, predicted="10.25", actual="13.75"),))
    assert result.case_count == 1
    assert result.mae_amount_per_mwh == Decimal("3.50")


def test_multiple_predictions_average_absolute_errors_exactly() -> None:
    predictions = (
        _prediction(day=1, predicted="10.00", actual="12.00"),
        _prediction(day=2, predicted="20.00", actual="17.00"),
        _prediction(day=3, predicted="30.00", actual="30.00"),
        _prediction(day=4, predicted="41.00", actual="40.00"),
    )
    result = _evaluate(predictions)
    assert result.case_count == 4
    assert result.mae_amount_per_mwh == Decimal("1.5")


def test_positive_residual_becomes_positive_absolute_error() -> None:
    result = _evaluate((_prediction(day=1, predicted="100.00", actual="80.00"),))
    assert result.mae_amount_per_mwh == Decimal("20")


def test_negative_residual_becomes_positive_absolute_error() -> None:
    result = _evaluate((_prediction(day=1, predicted="80.00", actual="100.00"),))
    assert result.mae_amount_per_mwh == Decimal("20")


def test_mixed_sign_residuals_do_not_cancel() -> None:
    predictions = (
        _prediction(day=1, predicted="110.00", actual="100.00"),
        _prediction(day=2, predicted="90.00", actual="100.00"),
    )
    result = _evaluate(predictions)
    assert result.mae_amount_per_mwh == Decimal("10")


def test_negative_predicted_dam_price_scores_normally() -> None:
    result = _evaluate((_prediction(day=1, predicted="-10.00", actual="5.00"),))
    assert result.mae_amount_per_mwh == Decimal("15")


def test_negative_actual_dam_price_scores_normally() -> None:
    result = _evaluate((_prediction(day=1, predicted="25.00", actual="-25.00"),))
    assert result.mae_amount_per_mwh == Decimal("50")


def test_both_amounts_negative_use_ordinary_absolute_difference() -> None:
    result = _evaluate((_prediction(day=1, predicted="-10.00", actual="-15.00"),))
    assert result.mae_amount_per_mwh == Decimal("5")


def test_all_negative_cohort_scores_without_clamping() -> None:
    predictions = (
        _prediction(day=1, predicted="-10.00", actual="-15.00"),
        _prediction(day=2, predicted="-20.00", actual="-18.00"),
    )
    result = _evaluate(predictions)
    assert result.case_count == 2
    assert result.mae_amount_per_mwh == Decimal("3.5")


def test_zero_error_cases_remain_in_the_denominator() -> None:
    predictions = (
        _prediction(day=1, predicted="10.00", actual="10.00"),
        _prediction(day=2, predicted="10.00", actual="14.00"),
    )
    result = _evaluate(predictions)
    assert result.case_count == 2
    assert result.mae_amount_per_mwh == Decimal("2")


def test_case_count_matches_cohort_cardinality() -> None:
    predictions = tuple(
        _prediction(day=day, predicted=str(day), actual=str(day + 1)) for day in range(1, 8)
    )
    result = _evaluate(predictions)
    assert result.case_count == len(predictions) == 7
    assert result.mae_amount_per_mwh == Decimal("1")


def test_repeating_division_is_not_integer_or_cent_rounded() -> None:
    predictions = (
        _prediction(day=1, predicted="1.00", actual="2.00"),
        _prediction(day=2, predicted="5.00", actual="5.00"),
        _prediction(day=3, predicted="7.00", actual="7.00"),
    )
    result = _evaluate(predictions)
    assert result.mae_amount_per_mwh == Decimal("1.00") / 3
    assert result.mae_amount_per_mwh != Decimal("0")
    assert result.mae_amount_per_mwh != Decimal("0.33")
    assert result.mae_amount_per_mwh != Decimal("0.333")
    assert isinstance(result.mae_amount_per_mwh, Decimal)


def test_decimal_arithmetic_does_not_introduce_float_values() -> None:
    result = _evaluate((_prediction(day=1, predicted="100.10", actual="200.33"),))
    assert isinstance(result.mae_amount_per_mwh, Decimal)
    assert not isinstance(result.mae_amount_per_mwh, float)
    assert result.mae_amount_per_mwh == Decimal("100.23")


def test_non_default_cohort_currency_is_returned_exactly() -> None:
    predictions = (
        _prediction(day=1, predicted="11.00", actual="13.00", market_id="market-7", currency="EUR"),
        _prediction(day=2, predicted="21.00", actual="19.00", market_id="market-7", currency="EUR"),
    )
    result = _evaluate(predictions)
    assert result.currency == "EUR"
    assert result.mae_amount_per_mwh == Decimal("2")


def test_mixed_markets_fail_closed_without_leaking_ids() -> None:
    predictions = (
        _prediction(day=1, predicted="10.00", actual="12.00", market_id="market-alpha"),
        _prediction(day=2, predicted="20.00", actual="22.00", market_id="market-beta"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _evaluate(predictions)
    assert captured.value.message == _MIXED_MARKET_MESSAGE
    assert "market-alpha" not in str(captured.value)
    assert "market-beta" not in str(captured.value)


def test_mixed_currencies_fail_closed_without_leaking_codes() -> None:
    predictions = (
        _prediction(day=1, predicted="10.00", actual="12.00", currency="AMD"),
        _prediction(day=2, predicted="20.00", actual="22.00", currency="EUR"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _evaluate(predictions)
    assert captured.value.message == _MIXED_CURRENCY_MESSAGE
    assert "AMD" not in str(captured.value)
    assert "EUR" not in str(captured.value)


def test_duplicate_target_timestamps_fail_closed() -> None:
    predictions = (
        _prediction(day=2, predicted="10.00", actual="12.00"),
        _prediction(day=2, predicted="20.00", actual="22.00"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _evaluate(predictions)
    assert captured.value.message == _DUPLICATE_TIMESTAMP_MESSAGE
    assert "2026" not in str(captured.value)


def test_out_of_order_target_timestamps_fail_closed() -> None:
    predictions = (
        _prediction(day=3, predicted="10.00", actual="12.00"),
        _prediction(day=1, predicted="20.00", actual="22.00"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _evaluate(predictions)
    assert captured.value.message == _OUT_OF_ORDER_MESSAGE
    assert "2026" not in str(captured.value)


def test_descending_cohort_is_not_silently_sorted() -> None:
    first = _prediction(day=1, predicted="10.00", actual="12.00")
    second = _prediction(day=2, predicted="20.00", actual="22.00")
    third = _prediction(day=3, predicted="30.00", actual="32.00")
    with pytest.raises(InvalidRequestError) as captured:
        _evaluate((third, second, first))
    assert captured.value.message == _OUT_OF_ORDER_MESSAGE
    ordered = _evaluate((first, second, third))
    assert ordered.case_count == 3
    assert ordered.mae_amount_per_mwh == Decimal("2")


@pytest.mark.parametrize("predicted", ["NaN", "sNaN", "Infinity", "-Infinity"])
def test_non_finite_predicted_amount_fails_closed(predicted: str) -> None:
    prediction = _prediction(day=1, predicted=predicted, actual="1.00")
    with pytest.raises(InvalidRequestError) as captured:
        _evaluate((prediction,))
    assert captured.value.message == _NON_FINITE_VALUES_MESSAGE


@pytest.mark.parametrize("actual", ["NaN", "sNaN", "Infinity", "-Infinity"])
def test_non_finite_actual_amount_fails_closed(actual: str) -> None:
    prediction = _prediction(day=1, predicted="1.00", actual=actual)
    with pytest.raises(InvalidRequestError) as captured:
        _evaluate((prediction,))
    assert captured.value.message == _NON_FINITE_VALUES_MESSAGE


def test_later_non_finite_value_produces_no_result() -> None:
    predictions = (
        _prediction(day=1, predicted="1.00", actual="2.00"),
        _prediction(day=2, predicted="3.00", actual="NaN"),
    )
    result: DAMPriceLag24h168hLinearRegressionMAEResult | None = None
    with pytest.raises(InvalidRequestError) as captured:
        result = _evaluate(predictions)
    assert captured.value.message == _NON_FINITE_VALUES_MESSAGE
    assert result is None


def test_subtraction_overflow_is_translated_not_leaked() -> None:
    # The difference leaves the default Decimal exponent range, so the
    # absolute error cannot be represented. The Decimal signal must become the
    # sanitized failure family with causal chaining.
    prediction = _prediction(day=1, predicted="9E+999999", actual="-9E+999999")
    with pytest.raises(InvalidRequestError) as captured:
        _evaluate((prediction,))
    assert captured.value.message == _NON_FINITE_MAE_MESSAGE
    assert isinstance(captured.value.__cause__, Overflow)
    assert "E+999999" not in str(captured.value)


def test_accumulation_overflow_is_translated_not_leaked() -> None:
    # Each absolute error is representable, but their sum is not.
    predictions = (
        _prediction(day=1, predicted="6E+999999", actual="0"),
        _prediction(day=2, predicted="0", actual="6E+999999"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _evaluate(predictions)
    assert captured.value.message == _NON_FINITE_MAE_MESSAGE
    assert isinstance(captured.value.__cause__, Overflow)
    assert "E+999999" not in str(captured.value)


def test_non_finite_aggregate_fails_closed_when_signals_are_untrapped() -> None:
    # With Decimal traps disabled the overflowing accumulation silently
    # becomes Infinity; the evaluator must still refuse to return it.
    predictions = (
        _prediction(day=1, predicted="6E+999999", actual="0"),
        _prediction(day=2, predicted="0", actual="6E+999999"),
    )
    result: DAMPriceLag24h168hLinearRegressionMAEResult | None = None
    with localcontext() as context:
        context.traps[Overflow] = False
        context.traps[InvalidOperation] = False
        with pytest.raises(InvalidRequestError) as captured:
            result = _evaluate(predictions)
    assert captured.value.message == _NON_FINITE_MAE_MESSAGE
    assert result is None


def test_error_messages_leak_no_raw_values() -> None:
    sentinels = ("market-secret", "market-other", "111.11", "222.22", "333.33", "444.44")
    mixed_market = (
        _prediction(
            day=1, predicted="111.11", actual="222.22", market_id="market-secret", currency="AMD"
        ),
        _prediction(
            day=2, predicted="333.33", actual="444.44", market_id="market-other", currency="AMD"
        ),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _evaluate(mixed_market)
    for leak in sentinels:
        assert leak not in str(captured.value)

    mixed_currency = (
        _prediction(day=1, predicted="111.11", actual="222.22", currency="AMD"),
        _prediction(day=2, predicted="333.33", actual="444.44", currency="EUR"),
    )
    with pytest.raises(InvalidRequestError) as currency_captured:
        _evaluate(mixed_currency)
    for leak in ("AMD", "EUR", *sentinels):
        assert leak not in str(currency_captured.value)

    out_of_order = (
        _prediction(day=9, predicted="111.11", actual="222.22"),
        _prediction(day=8, predicted="333.33", actual="444.44"),
    )
    with pytest.raises(InvalidRequestError) as order_captured:
        _evaluate(out_of_order)
    for leak in ("2026", "market-1", "AMD", "[0]", "[1]", *sentinels):
        assert leak not in str(order_captured.value)


def test_input_predictions_are_not_mutated() -> None:
    first = _prediction(day=1, predicted="10.00", actual="12.00")
    second = _prediction(day=2, predicted="-20.00", actual="17.00")
    predictions = (first, second)
    _evaluate(predictions)
    assert predictions == (first, second)
    assert predictions[0] is first
    assert predictions[1] is second
    assert first == _prediction(day=1, predicted="10.00", actual="12.00")
    assert second == _prediction(day=2, predicted="-20.00", actual="17.00")


def test_repeated_equal_calls_return_value_equal_results() -> None:
    predictions = (
        _prediction(day=1, predicted="10.00", actual="12.00"),
        _prediction(day=2, predicted="20.00", actual="17.00"),
    )
    assert _evaluate(predictions) == _evaluate(predictions)


def test_result_contract_is_frozen_slotted_and_exactly_three_fields() -> None:
    result_fields = fields(DAMPriceLag24h168hLinearRegressionMAEResult)
    names = tuple(item.name for item in result_fields)
    assert names == THREE_FIELDS
    assert DAMPriceLag24h168hLinearRegressionMAEResult.__slots__ == names
    for item in result_fields:
        assert item.default is MISSING
        assert item.default_factory is MISSING
    result = _evaluate((_prediction(day=1, predicted="10.00", actual="12.00"),))
    with pytest.raises(FrozenInstanceError):
        result.case_count = 99  # type: ignore[misc]
    assert not hasattr(result, "__dict__")


def test_evaluator_is_synchronous_and_keyword_only() -> None:
    evaluator = evaluate_dam_price_lag_24h_168h_linear_regression_mae
    assert not inspect.iscoroutinefunction(evaluator)
    parameters = inspect.signature(evaluator).parameters
    assert tuple(parameters) == ("predictions",)
    assert parameters["predictions"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["predictions"].default is inspect.Parameter.empty
    with pytest.raises(TypeError):
        evaluator((_prediction(day=1, predicted="1", actual="1"),))  # type: ignore[misc]
