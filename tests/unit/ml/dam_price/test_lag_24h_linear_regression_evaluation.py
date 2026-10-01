"""Lag-24h ordinary-least-squares DAM Price MAE evaluation."""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime
from decimal import Decimal

import pytest

# ``energy_trading.domain.models`` must initialize before
# ``energy_trading.domain.value_objects`` because value-object modules import
# canonical models during their own initialization. Importing the models
# package explicitly keeps that pre-existing order.
import energy_trading.domain.models  # noqa: F401
from energy_trading.application.errors import InvalidRequestError
from energy_trading.ml.dam_price.lag_24h_linear_regression_evaluation import (
    DAMPriceLag24hLinearRegressionMAEResult,
    evaluate_dam_price_lag_24h_linear_regression_mae,
)
from energy_trading.ml.dam_price.lag_24h_linear_regression_prediction import (
    DAMPriceLag24hLinearRegressionPrediction,
)

_EMPTY_PREDICTIONS_MESSAGE = (
    "DAM Price lag-24h linear regression MAE evaluation requires at least one prediction."
)
_MIXED_MARKET_MESSAGE = (
    "DAM Price lag-24h linear regression MAE evaluation requires predictions from exactly one "
    "market."
)
_MIXED_CURRENCY_MESSAGE = (
    "DAM Price lag-24h linear regression MAE evaluation requires predictions in exactly one "
    "currency."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "DAM Price lag-24h linear regression MAE evaluation requires unique target timestamps."
)
_OUT_OF_ORDER_MESSAGE = (
    "DAM Price lag-24h linear regression MAE evaluation requires strictly increasing target "
    "timestamps."
)
_NON_FINITE_VALUES_MESSAGE = (
    "DAM Price lag-24h linear regression MAE evaluation requires finite predicted and actual "
    "values."
)
_NON_FINITE_MAE_MESSAGE = (
    "DAM Price lag-24h linear regression MAE evaluation requires a finite MAE."
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
) -> DAMPriceLag24hLinearRegressionPrediction:
    return DAMPriceLag24hLinearRegressionPrediction(
        market_id=market_id,
        currency=currency,
        target_timestamp=_ts(day),
        predicted_amount_per_mwh=Decimal(predicted),
        actual_amount_per_mwh=Decimal(actual),
    )


def _evaluate(
    predictions: tuple[DAMPriceLag24hLinearRegressionPrediction, ...],
) -> DAMPriceLag24hLinearRegressionMAEResult:
    return evaluate_dam_price_lag_24h_linear_regression_mae(predictions=predictions)


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


def test_single_non_zero_prediction_uses_exact_absolute_difference() -> None:
    result = _evaluate((_prediction(day=1, predicted="10.25", actual="13.75"),))
    assert result.case_count == 1
    assert result.mae_amount_per_mwh == Decimal("3.50")


def test_multiple_predictions_average_absolute_errors_exactly() -> None:
    predictions = (
        _prediction(day=1, predicted="10.00", actual="12.00"),
        _prediction(day=2, predicted="20.00", actual="17.00"),
        _prediction(day=3, predicted="30.00", actual="30.00"),
    )
    result = _evaluate(predictions)
    assert result.case_count == 3
    assert result.mae_amount_per_mwh == (Decimal("2") + Decimal("3") + Decimal("0")) / 3


def test_positive_residual_becomes_positive_absolute_error() -> None:
    result = _evaluate((_prediction(day=1, predicted="100.00", actual="80.00"),))
    assert result.mae_amount_per_mwh == Decimal("20")


def test_negative_residual_becomes_positive_absolute_error() -> None:
    result = _evaluate((_prediction(day=1, predicted="80.00", actual="100.00"),))
    assert result.mae_amount_per_mwh == Decimal("20")


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
    assert result.mae_amount_per_mwh == (Decimal("5") + Decimal("2")) / 2


def test_zero_error_cases_remain_in_the_denominator() -> None:
    predictions = (
        _prediction(day=1, predicted="10.00", actual="10.00"),
        _prediction(day=2, predicted="10.00", actual="14.00"),
    )
    result = _evaluate(predictions)
    assert result.case_count == 2
    assert result.mae_amount_per_mwh == Decimal("2")


def test_repeating_division_is_not_integer_or_cent_rounded() -> None:
    predictions = (
        _prediction(day=1, predicted="1.00", actual="2.00"),
        _prediction(day=2, predicted="5.00", actual="5.00"),
        _prediction(day=3, predicted="7.00", actual="7.00"),
    )
    result = _evaluate(predictions)
    assert result.mae_amount_per_mwh == Decimal("1") / 3
    assert result.mae_amount_per_mwh != Decimal("0")
    assert result.mae_amount_per_mwh != Decimal("0.33")
    assert result.mae_amount_per_mwh != Decimal("0.333")
    assert isinstance(result.mae_amount_per_mwh, Decimal)


def test_decimal_arithmetic_does_not_introduce_float_values() -> None:
    result = _evaluate((_prediction(day=1, predicted="100.10", actual="200.33"),))
    assert isinstance(result.mae_amount_per_mwh, Decimal)
    assert not isinstance(result.mae_amount_per_mwh, float)
    assert result.mae_amount_per_mwh == Decimal("100.23")


def test_shared_cohort_currency_is_returned_exactly() -> None:
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
    assert "market-alpha" not in captured.value.message
    assert "market-beta" not in captured.value.message


def test_mixed_currencies_fail_closed_without_leaking_codes() -> None:
    predictions = (
        _prediction(day=1, predicted="10.00", actual="12.00", currency="AMD"),
        _prediction(day=2, predicted="20.00", actual="22.00", currency="EUR"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _evaluate(predictions)
    assert captured.value.message == _MIXED_CURRENCY_MESSAGE
    assert "AMD" not in captured.value.message
    assert "EUR" not in captured.value.message


def test_duplicate_target_timestamps_fail_closed() -> None:
    predictions = (
        _prediction(day=2, predicted="10.00", actual="12.00"),
        _prediction(day=2, predicted="20.00", actual="22.00"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _evaluate(predictions)
    assert captured.value.message == _DUPLICATE_TIMESTAMP_MESSAGE


def test_out_of_order_target_timestamps_fail_closed() -> None:
    predictions = (
        _prediction(day=3, predicted="10.00", actual="12.00"),
        _prediction(day=1, predicted="20.00", actual="22.00"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _evaluate(predictions)
    assert captured.value.message == _OUT_OF_ORDER_MESSAGE


def test_out_of_order_cohort_is_not_silently_sorted() -> None:
    late = _prediction(day=3, predicted="10.00", actual="12.00")
    early = _prediction(day=1, predicted="20.00", actual="22.00")
    with pytest.raises(InvalidRequestError) as captured:
        _evaluate((late, early))
    assert captured.value.message == _OUT_OF_ORDER_MESSAGE
    ordered = _evaluate((early, late))
    assert ordered.case_count == 2


def test_valid_strict_chronology_succeeds() -> None:
    predictions = (
        _prediction(day=1, predicted="10.00", actual="12.00"),
        _prediction(day=2, predicted="20.00", actual="22.00"),
        _prediction(day=4, predicted="30.00", actual="32.00"),
    )
    result = _evaluate(predictions)
    assert result.case_count == 3
    assert result.mae_amount_per_mwh == Decimal("2")


@pytest.mark.parametrize("predicted", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_predicted_amount_fails_closed(predicted: str) -> None:
    prediction = _prediction(day=1, predicted=predicted, actual="1.00")
    with pytest.raises(InvalidRequestError) as captured:
        _evaluate((prediction,))
    assert captured.value.message == _NON_FINITE_VALUES_MESSAGE


@pytest.mark.parametrize("actual", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_actual_amount_fails_closed(actual: str) -> None:
    prediction = _prediction(day=1, predicted="1.00", actual=actual)
    with pytest.raises(InvalidRequestError) as captured:
        _evaluate((prediction,))
    assert captured.value.message == _NON_FINITE_VALUES_MESSAGE


def test_decimal_arithmetic_failure_is_translated_not_leaked() -> None:
    # Subtracting these magnitudes leaves the default Decimal exponent range,
    # so the absolute error cannot be represented. The evaluator must translate
    # the Decimal arithmetic signal into the sanitized failure family rather
    # than leaking a raw Decimal exception or a non-finite MAE.
    prediction = _prediction(day=1, predicted="9E+999999", actual="-9E+999999")
    with pytest.raises(InvalidRequestError) as captured:
        _evaluate((prediction,))
    assert captured.value.message == _NON_FINITE_MAE_MESSAGE


def test_error_messages_leak_no_raw_values() -> None:
    predictions = (
        _prediction(
            day=1,
            predicted="111.11",
            actual="222.22",
            market_id="market-secret",
            currency="AMD",
        ),
        _prediction(
            day=2,
            predicted="333.33",
            actual="444.44",
            market_id="market-other",
            currency="AMD",
        ),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _evaluate(predictions)
    message = captured.value.message
    for leak in ("market-secret", "market-other", "111.11", "222.22", "333.33", "444.44"):
        assert leak not in message

    mixed_currency = (
        _prediction(day=1, predicted="1.00", actual="2.00", currency="AMD"),
        _prediction(day=2, predicted="3.00", actual="4.00", currency="EUR"),
    )
    with pytest.raises(InvalidRequestError) as currency_captured:
        _evaluate(mixed_currency)
    assert "AMD" not in currency_captured.value.message
    assert "EUR" not in currency_captured.value.message


def test_input_predictions_are_not_mutated() -> None:
    first = _prediction(day=1, predicted="10.00", actual="12.00")
    second = _prediction(day=2, predicted="20.00", actual="17.00")
    predictions = (first, second)
    _evaluate(predictions)
    assert predictions == (first, second)
    assert first.predicted_amount_per_mwh == Decimal("10.00")
    assert first.actual_amount_per_mwh == Decimal("12.00")
    assert second.predicted_amount_per_mwh == Decimal("20.00")
    assert second.actual_amount_per_mwh == Decimal("17.00")
    assert first.market_id == "market-1"
    assert first.currency == "AMD"


def test_repeated_equal_calls_return_value_equal_results() -> None:
    predictions = (
        _prediction(day=1, predicted="10.00", actual="12.00"),
        _prediction(day=2, predicted="20.00", actual="17.00"),
    )
    assert _evaluate(predictions) == _evaluate(predictions)


def test_result_contract_is_frozen_slotted_and_exactly_three_fields() -> None:
    names = tuple(item.name for item in fields(DAMPriceLag24hLinearRegressionMAEResult))
    assert names == THREE_FIELDS
    assert DAMPriceLag24hLinearRegressionMAEResult.__slots__ == names
    result = _evaluate((_prediction(day=1, predicted="10.00", actual="12.00"),))
    with pytest.raises(FrozenInstanceError):
        result.case_count = 99  # type: ignore[misc]


def test_result_exposes_no_other_metric_identity_or_payload_fields() -> None:
    names = {item.name for item in fields(DAMPriceLag24hLinearRegressionMAEResult)}
    assert names == set(THREE_FIELDS)
    forbidden = {
        "market_id",
        "mse",
        "rmse",
        "mape",
        "smape",
        "r2",
        "bias",
        "median_absolute_error",
        "max_error",
        "residual",
        "residuals",
        "percentage_error",
        "directional_accuracy",
        "standard_deviation",
        "model_name",
        "model_version",
        "provider",
        "total_amount",
        "target_timestamp",
    }
    assert forbidden.isdisjoint(names)
    assert len(names) == 3


def test_evaluator_is_synchronous_and_keyword_only() -> None:
    assert not inspect.iscoroutinefunction(evaluate_dam_price_lag_24h_linear_regression_mae)
    parameters = inspect.signature(evaluate_dam_price_lag_24h_linear_regression_mae).parameters
    assert tuple(parameters) == ("predictions",)
    assert parameters["predictions"].kind is inspect.Parameter.KEYWORD_ONLY
