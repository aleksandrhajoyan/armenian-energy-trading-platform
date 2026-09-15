"""Lag-24h ordinary-least-squares Consumer Load MAE evaluation."""

from __future__ import annotations  # noqa: I001

from math import isfinite

import pytest

from tests.unit.domain._factories import utc
from energy_trading.application.errors import InvalidRequestError
from energy_trading.ml.consumer_load.lag_24h_linear_regression_evaluation import (
    ConsumerLoadLag24hLinearRegressionMAEResult,
    evaluate_consumer_load_lag_24h_linear_regression_mae,
)
from energy_trading.ml.consumer_load.lag_24h_linear_regression_prediction import (
    ConsumerLoadLag24hLinearRegressionPrediction,
)

_EMPTY_PREDICTIONS_MESSAGE = (
    "Consumer Load lag-24h linear regression MAE evaluation requires at least one prediction."
)
_MIXED_CONSUMER_MESSAGE = (
    "Consumer Load lag-24h linear regression MAE evaluation requires "
    "predictions from exactly one consumer."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "Consumer Load lag-24h linear regression MAE evaluation requires unique target timestamps."
)
_OUT_OF_ORDER_MESSAGE = (
    "Consumer Load lag-24h linear regression MAE evaluation requires strictly "
    "increasing target timestamps."
)
_NON_FINITE_VALUES_MESSAGE = (
    "Consumer Load lag-24h linear regression MAE evaluation requires finite "
    "predicted and actual values."
)
_NON_FINITE_MAE_MESSAGE = (
    "Consumer Load lag-24h linear regression MAE evaluation requires a finite MAE."
)
_RESULT_FIELDS = (
    "case_count",
    "mae_mw",
)


def _prediction(
    *,
    hour: int,
    predicted_value_mw: float,
    actual_value_mw: float,
    consumer_id: str = "consumer-1",
) -> ConsumerLoadLag24hLinearRegressionPrediction:
    return ConsumerLoadLag24hLinearRegressionPrediction(
        consumer_id=consumer_id,
        target_timestamp=utc(hour=hour),
        predicted_value_mw=predicted_value_mw,
        actual_value_mw=actual_value_mw,
    )


def _evaluate(
    predictions: tuple[ConsumerLoadLag24hLinearRegressionPrediction, ...],
) -> ConsumerLoadLag24hLinearRegressionMAEResult:
    return evaluate_consumer_load_lag_24h_linear_regression_mae(predictions=predictions)


def test_several_predictions_calculate_exact_mae() -> None:
    predictions = (
        _prediction(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),
        _prediction(hour=11, predicted_value_mw=5.0, actual_value_mw=3.0),
        _prediction(hour=12, predicted_value_mw=8.0, actual_value_mw=11.0),
    )
    result = _evaluate(predictions)
    expected = (abs(1.0 - 2.0) + abs(5.0 - 3.0) + abs(8.0 - 11.0)) / 3
    assert result.case_count == 3
    assert result.mae_mw == expected
    assert result.mae_mw == 2.0


def test_exact_match_predictions_give_mae_zero() -> None:
    predictions = (
        _prediction(hour=10, predicted_value_mw=7.25, actual_value_mw=7.25),
        _prediction(hour=12, predicted_value_mw=4.0, actual_value_mw=4.0),
    )
    result = _evaluate(predictions)
    assert result.case_count == 2
    assert result.mae_mw == 0.0


def test_negative_prediction_is_measured_without_clamping() -> None:
    result = _evaluate(
        (_prediction(hour=10, predicted_value_mw=-4.0, actual_value_mw=4.0),),
    )
    assert result.mae_mw == 8.0
    assert result.mae_mw == abs(-4.0 - 4.0)
    assert result.mae_mw != abs(0.0 - 4.0)


def test_mixed_positive_and_negative_residuals_use_absolute_error() -> None:
    predictions = (
        _prediction(hour=10, predicted_value_mw=10.0, actual_value_mw=7.0),
        _prediction(hour=11, predicted_value_mw=4.0, actual_value_mw=7.0),
    )
    result = _evaluate(predictions)
    signed_mean = ((10.0 - 7.0) + (4.0 - 7.0)) / 2
    assert signed_mean == 0.0
    assert result.mae_mw == 3.0
    assert result.mae_mw == (abs(10.0 - 7.0) + abs(4.0 - 7.0)) / 2


def test_single_case_mae_equals_that_absolute_error() -> None:
    result = _evaluate(
        (_prediction(hour=10, predicted_value_mw=4.5, actual_value_mw=7.25),),
    )
    assert result.case_count == 1
    assert result.mae_mw == 2.75


def test_result_is_frozen_slotted_with_exactly_two_fields() -> None:
    result = _evaluate(
        (_prediction(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),),
    )
    assert ConsumerLoadLag24hLinearRegressionMAEResult.__slots__ == _RESULT_FIELDS
    assert result.__slots__ == _RESULT_FIELDS
    with pytest.raises(AttributeError):
        result.mae_mw = 0.0  # type: ignore[misc]
    assert not hasattr(result, "__dict__")
    forbidden_attrs = (
        "rmse",
        "mse",
        "mape",
        "r2",
        "bias",
        "metadata",
        "model_name",
        "consumer_id",
        "improvement",
    )
    for name in forbidden_attrs:
        assert not hasattr(result, name)


def test_empty_predictions_fail_closed() -> None:
    with pytest.raises(InvalidRequestError, match=_EMPTY_PREDICTIONS_MESSAGE) as caught:
        _evaluate(())
    assert caught.value.code == "invalid_request"


def test_mixed_consumers_fail_closed_without_raw_ids() -> None:
    predictions = (
        _prediction(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0, consumer_id="consumer-1"),
        _prediction(hour=12, predicted_value_mw=3.0, actual_value_mw=4.0, consumer_id="consumer-2"),
    )
    with pytest.raises(InvalidRequestError, match=_MIXED_CONSUMER_MESSAGE) as caught:
        _evaluate(predictions)
    assert caught.value.code == "invalid_request"
    assert "consumer-1" not in caught.value.message
    assert "consumer-2" not in caught.value.message


def test_duplicate_target_timestamps_fail_closed() -> None:
    stamp = utc(hour=12)
    predictions = (
        _prediction(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),
        ConsumerLoadLag24hLinearRegressionPrediction(
            consumer_id="consumer-1",
            target_timestamp=stamp,
            predicted_value_mw=3.0,
            actual_value_mw=4.0,
        ),
        ConsumerLoadLag24hLinearRegressionPrediction(
            consumer_id="consumer-1",
            target_timestamp=stamp,
            predicted_value_mw=5.0,
            actual_value_mw=6.0,
        ),
    )
    with pytest.raises(InvalidRequestError, match=_DUPLICATE_TIMESTAMP_MESSAGE) as caught:
        _evaluate(predictions)
    assert caught.value.code == "invalid_request"


def test_out_of_order_timestamps_fail_closed() -> None:
    predictions = (
        _prediction(hour=14, predicted_value_mw=2.0, actual_value_mw=3.0),
        _prediction(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),
    )
    with pytest.raises(InvalidRequestError, match=_OUT_OF_ORDER_MESSAGE) as caught:
        _evaluate(predictions)
    assert caught.value.code == "invalid_request"


@pytest.mark.parametrize("predicted_value_mw", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_predicted_value_is_rejected(predicted_value_mw: float) -> None:
    with pytest.raises(InvalidRequestError, match=_NON_FINITE_VALUES_MESSAGE) as caught:
        _evaluate(
            (
                _prediction(
                    hour=10,
                    predicted_value_mw=predicted_value_mw,
                    actual_value_mw=4.0,
                ),
            ),
        )
    assert caught.value.code == "invalid_request"


def test_overflowing_absolute_error_fails_closed() -> None:
    predicted_value_mw = -1e308
    actual_value_mw = 1e308
    assert isfinite(predicted_value_mw)
    assert isfinite(actual_value_mw)
    with pytest.raises(InvalidRequestError, match=_NON_FINITE_MAE_MESSAGE) as caught:
        _evaluate(
            (
                _prediction(
                    hour=10,
                    predicted_value_mw=predicted_value_mw,
                    actual_value_mw=actual_value_mw,
                ),
            ),
        )
    assert caught.value.code == "invalid_request"


def test_input_prediction_tuple_is_not_mutated() -> None:
    first = _prediction(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0)
    second = _prediction(hour=12, predicted_value_mw=5.0, actual_value_mw=3.0)
    predictions = (first, second)
    original_ids = tuple(id(item) for item in predictions)
    _evaluate(predictions)
    assert predictions == (first, second)
    assert tuple(id(item) for item in predictions) == original_ids
    assert predictions[0] is first
    assert predictions[1] is second
    assert first.predicted_value_mw == 1.0
    assert first.actual_value_mw == 2.0


def test_repeated_equal_input_returns_value_equal_result() -> None:
    predictions = (
        _prediction(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),
        _prediction(hour=12, predicted_value_mw=5.0, actual_value_mw=3.0),
    )
    first = _evaluate(predictions)
    second = _evaluate(predictions)
    assert first == second
    assert first is not second


def test_return_contract_uses_int_count_and_finite_float_mae() -> None:
    result = _evaluate(
        (_prediction(hour=10, predicted_value_mw=4.5, actual_value_mw=7.25),),
    )
    assert isinstance(result, ConsumerLoadLag24hLinearRegressionMAEResult)
    assert type(result.case_count) is int
    assert type(result.mae_mw) is float
    assert isfinite(result.mae_mw)
    assert result.case_count == 1
    assert result.mae_mw == 2.75
