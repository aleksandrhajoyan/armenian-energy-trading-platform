"""Lag-24h plus lag-168h ordinary-least-squares Consumer Load evaluation prediction."""

from __future__ import annotations

from math import isfinite

import pytest

from energy_trading.application.errors import InvalidRequestError
from energy_trading.ml.consumer_load.lag_24h_168h_features import (
    ConsumerLoadLag24h168hFeatureRow,
)
from energy_trading.ml.consumer_load.lag_24h_168h_linear_regression import (
    ConsumerLoadLag24h168hLinearRegressionFit,
)
from energy_trading.ml.consumer_load.lag_24h_168h_linear_regression_prediction import (
    ConsumerLoadLag24h168hLinearRegressionPrediction,
    predict_consumer_load_lag_24h_168h_linear_regression,
)
from tests.unit.domain._factories import utc

_EMPTY_ROWS_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression prediction "
    "requires at least one evaluation row."
)
_MIXED_CONSUMER_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression prediction "
    "requires rows from exactly one consumer."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression prediction "
    "requires unique target timestamps."
)
_OUT_OF_ORDER_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression prediction "
    "requires strictly increasing target timestamps."
)
_NON_FINITE_FIT_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression prediction "
    "requires finite fitted coefficients and intercept."
)
_NON_FINITE_PREDICTION_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression prediction "
    "requires finite predicted values."
)
_PREDICTION_FIELDS = (
    "consumer_id",
    "target_timestamp",
    "predicted_value_mw",
    "actual_value_mw",
)
_FINITE_FIT = ConsumerLoadLag24h168hLinearRegressionFit(
    lag_24h_coefficient=3.0,
    lag_168h_coefficient=5.0,
    intercept_mw=2.0,
)


def _row(
    *,
    hour: int,
    lag_24h_mw: float,
    lag_168h_mw: float,
    target_value_mw: float,
    consumer_id: str = "consumer-1",
    day: int = 15,
) -> ConsumerLoadLag24h168hFeatureRow:
    return ConsumerLoadLag24h168hFeatureRow(
        consumer_id=consumer_id,
        target_timestamp=utc(day=day, hour=hour),
        lag_24h_mw=lag_24h_mw,
        lag_168h_mw=lag_168h_mw,
        target_value_mw=target_value_mw,
    )


def _predict(
    *,
    fit: ConsumerLoadLag24h168hLinearRegressionFit = _FINITE_FIT,
    evaluation_rows: tuple[ConsumerLoadLag24h168hFeatureRow, ...],
) -> tuple[ConsumerLoadLag24h168hLinearRegressionPrediction, ...]:
    return predict_consumer_load_lag_24h_168h_linear_regression(
        fit=fit,
        evaluation_rows=evaluation_rows,
    )


def test_exact_prediction_from_known_fit_and_one_row() -> None:
    result = _predict(
        evaluation_rows=(_row(hour=8, lag_24h_mw=1.0, lag_168h_mw=2.0, target_value_mw=9.0),)
    )
    assert len(result) == 1
    assert result[0].predicted_value_mw == 2.0 + 3.0 * 1.0 + 5.0 * 2.0
    assert result[0].predicted_value_mw == 15.0


def test_multiple_predictions_preserve_evaluation_row_order() -> None:
    first = _row(hour=8, lag_24h_mw=1.0, lag_168h_mw=1.0, target_value_mw=10.0)
    second = _row(hour=9, lag_24h_mw=2.0, lag_168h_mw=1.0, target_value_mw=13.0)
    third = _row(hour=10, lag_24h_mw=1.0, lag_168h_mw=2.0, target_value_mw=15.0)
    result = _predict(evaluation_rows=(first, second, third))
    assert tuple(item.target_timestamp for item in result) == (
        first.target_timestamp,
        second.target_timestamp,
        third.target_timestamp,
    )
    assert result[0].predicted_value_mw == 10.0
    assert result[1].predicted_value_mw == 13.0
    assert result[2].predicted_value_mw == 15.0


def test_both_coefficients_participate() -> None:
    row = _row(hour=8, lag_24h_mw=1.0, lag_168h_mw=2.0, target_value_mw=9.0)
    result = _predict(evaluation_rows=(row,))
    intercept_only = _FINITE_FIT.intercept_mw
    without_168h = intercept_only + _FINITE_FIT.lag_24h_coefficient * row.lag_24h_mw
    without_24h = intercept_only + _FINITE_FIT.lag_168h_coefficient * row.lag_168h_mw
    assert result[0].predicted_value_mw == 15.0
    assert result[0].predicted_value_mw != intercept_only
    assert result[0].predicted_value_mw != without_168h
    assert result[0].predicted_value_mw != without_24h


def test_intercept_participates() -> None:
    row = _row(hour=8, lag_24h_mw=1.0, lag_168h_mw=1.0, target_value_mw=4.0)
    with_intercept = ConsumerLoadLag24h168hLinearRegressionFit(
        lag_24h_coefficient=1.0,
        lag_168h_coefficient=1.0,
        intercept_mw=7.0,
    )
    without_intercept = ConsumerLoadLag24h168hLinearRegressionFit(
        lag_24h_coefficient=1.0,
        lag_168h_coefficient=1.0,
        intercept_mw=0.0,
    )
    with_result = _predict(fit=with_intercept, evaluation_rows=(row,))
    without_result = _predict(fit=without_intercept, evaluation_rows=(row,))
    assert with_result[0].predicted_value_mw == 9.0
    assert without_result[0].predicted_value_mw == 2.0
    assert with_result[0].predicted_value_mw != without_result[0].predicted_value_mw


def test_identity_and_actual_target_are_preserved() -> None:
    first = _row(hour=8, lag_24h_mw=1.0, lag_168h_mw=1.0, target_value_mw=9.5)
    second = _row(hour=9, lag_24h_mw=2.0, lag_168h_mw=1.0, target_value_mw=4.25)
    result = _predict(evaluation_rows=(first, second))
    assert result[0].consumer_id == first.consumer_id
    assert result[1].consumer_id == second.consumer_id
    assert result[0].target_timestamp == first.target_timestamp
    assert result[1].target_timestamp == second.target_timestamp
    assert result[0].actual_value_mw == first.target_value_mw
    assert result[1].actual_value_mw == second.target_value_mw
    assert result[0].actual_value_mw is first.target_value_mw
    assert result[1].actual_value_mw is second.target_value_mw


def test_prediction_dto_is_frozen_slotted_with_exactly_four_fields() -> None:
    result = _predict(
        evaluation_rows=(_row(hour=8, lag_24h_mw=1.0, lag_168h_mw=2.0, target_value_mw=9.0),)
    )
    prediction = result[0]
    assert ConsumerLoadLag24h168hLinearRegressionPrediction.__slots__ == _PREDICTION_FIELDS
    assert prediction.__slots__ == _PREDICTION_FIELDS
    with pytest.raises(AttributeError):
        prediction.predicted_value_mw = 0.0  # type: ignore[misc]
    assert not hasattr(prediction, "__dict__")
    forbidden_attrs = (
        "lag_24h_coefficient",
        "lag_168h_coefficient",
        "intercept_mw",
        "lag_24h_mw",
        "lag_168h_mw",
        "residual",
        "error",
        "mae",
        "rmse",
        "metadata",
        "confidence",
        "winner",
        "champion",
        "model_id",
        "workflow_id",
    )
    for name in forbidden_attrs:
        assert not hasattr(prediction, name)


def test_negative_finite_prediction_is_preserved_without_clamping() -> None:
    fit = ConsumerLoadLag24h168hLinearRegressionFit(
        lag_24h_coefficient=1.0,
        lag_168h_coefficient=1.0,
        intercept_mw=-10.0,
    )
    result = _predict(
        fit=fit,
        evaluation_rows=(_row(hour=8, lag_24h_mw=2.0, lag_168h_mw=1.0, target_value_mw=4.0),),
    )
    assert result[0].predicted_value_mw == -7.0
    assert result[0].predicted_value_mw < 0.0
    assert result[0].actual_value_mw == 4.0


def test_exact_finite_zero_prediction_is_valid() -> None:
    fit = ConsumerLoadLag24h168hLinearRegressionFit(
        lag_24h_coefficient=1.0,
        lag_168h_coefficient=1.0,
        intercept_mw=-5.0,
    )
    result = _predict(
        fit=fit,
        evaluation_rows=(_row(hour=8, lag_24h_mw=2.0, lag_168h_mw=3.0, target_value_mw=6.0),),
    )
    assert result[0].predicted_value_mw == 0.0
    assert isfinite(result[0].predicted_value_mw)


def test_positive_prediction_is_valid() -> None:
    result = _predict(
        evaluation_rows=(_row(hour=8, lag_24h_mw=1.0, lag_168h_mw=1.0, target_value_mw=10.0),)
    )
    assert result[0].predicted_value_mw == 10.0
    assert result[0].predicted_value_mw > 0.0


def test_empty_evaluation_input_fails_closed() -> None:
    with pytest.raises(InvalidRequestError, match=_EMPTY_ROWS_MESSAGE) as caught:
        _predict(evaluation_rows=())
    assert caught.value.code == "invalid_request"


def test_mixed_consumers_fail_closed_without_raw_ids() -> None:
    rows = (
        _row(hour=8, lag_24h_mw=1.0, lag_168h_mw=1.0, target_value_mw=3.0),
        _row(
            hour=9,
            lag_24h_mw=2.0,
            lag_168h_mw=1.0,
            target_value_mw=5.0,
            consumer_id="consumer-2",
        ),
    )
    with pytest.raises(InvalidRequestError, match=_MIXED_CONSUMER_MESSAGE) as caught:
        _predict(evaluation_rows=rows)
    assert caught.value.code == "invalid_request"
    assert "consumer-1" not in caught.value.message
    assert "consumer-2" not in caught.value.message


def test_duplicate_target_timestamps_fail_closed() -> None:
    stamp = utc(day=15, hour=9)
    rows = (
        _row(hour=8, lag_24h_mw=1.0, lag_168h_mw=1.0, target_value_mw=3.0),
        ConsumerLoadLag24h168hFeatureRow(
            consumer_id="consumer-1",
            target_timestamp=stamp,
            lag_24h_mw=2.0,
            lag_168h_mw=1.0,
            target_value_mw=5.0,
        ),
        ConsumerLoadLag24h168hFeatureRow(
            consumer_id="consumer-1",
            target_timestamp=stamp,
            lag_24h_mw=3.0,
            lag_168h_mw=2.0,
            target_value_mw=7.0,
        ),
    )
    with pytest.raises(InvalidRequestError, match=_DUPLICATE_TIMESTAMP_MESSAGE) as caught:
        _predict(evaluation_rows=rows)
    assert caught.value.code == "invalid_request"


def test_out_of_order_timestamps_fail_closed() -> None:
    rows = (
        _row(hour=10, lag_24h_mw=2.0, lag_168h_mw=1.0, target_value_mw=5.0),
        _row(hour=8, lag_24h_mw=1.0, lag_168h_mw=1.0, target_value_mw=3.0),
    )
    with pytest.raises(InvalidRequestError, match=_OUT_OF_ORDER_MESSAGE) as caught:
        _predict(evaluation_rows=rows)
    assert caught.value.code == "invalid_request"


@pytest.mark.parametrize("lag_24h_coefficient", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_lag_24h_coefficient_is_rejected(lag_24h_coefficient: float) -> None:
    fit = ConsumerLoadLag24h168hLinearRegressionFit(
        lag_24h_coefficient=lag_24h_coefficient,
        lag_168h_coefficient=5.0,
        intercept_mw=2.0,
    )
    with pytest.raises(InvalidRequestError, match=_NON_FINITE_FIT_MESSAGE) as caught:
        _predict(
            fit=fit,
            evaluation_rows=(_row(hour=8, lag_24h_mw=1.0, lag_168h_mw=1.0, target_value_mw=3.0),),
        )
    assert caught.value.code == "invalid_request"


@pytest.mark.parametrize("lag_168h_coefficient", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_lag_168h_coefficient_is_rejected(lag_168h_coefficient: float) -> None:
    fit = ConsumerLoadLag24h168hLinearRegressionFit(
        lag_24h_coefficient=3.0,
        lag_168h_coefficient=lag_168h_coefficient,
        intercept_mw=2.0,
    )
    with pytest.raises(InvalidRequestError, match=_NON_FINITE_FIT_MESSAGE) as caught:
        _predict(
            fit=fit,
            evaluation_rows=(_row(hour=8, lag_24h_mw=1.0, lag_168h_mw=1.0, target_value_mw=3.0),),
        )
    assert caught.value.code == "invalid_request"


@pytest.mark.parametrize("intercept_mw", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_intercept_is_rejected(intercept_mw: float) -> None:
    fit = ConsumerLoadLag24h168hLinearRegressionFit(
        lag_24h_coefficient=3.0,
        lag_168h_coefficient=5.0,
        intercept_mw=intercept_mw,
    )
    with pytest.raises(InvalidRequestError, match=_NON_FINITE_FIT_MESSAGE) as caught:
        _predict(
            fit=fit,
            evaluation_rows=(_row(hour=8, lag_24h_mw=1.0, lag_168h_mw=1.0, target_value_mw=3.0),),
        )
    assert caught.value.code == "invalid_request"


def test_finite_large_values_causing_non_finite_prediction_fail_closed() -> None:
    fit = ConsumerLoadLag24h168hLinearRegressionFit(
        lag_24h_coefficient=1.0e308,
        lag_168h_coefficient=0.0,
        intercept_mw=0.0,
    )
    assert isfinite(fit.lag_24h_coefficient)
    assert isfinite(fit.lag_168h_coefficient)
    assert isfinite(fit.intercept_mw)
    row = _row(hour=8, lag_24h_mw=2.0, lag_168h_mw=1.0, target_value_mw=3.0)
    assert isfinite(row.lag_24h_mw)
    assert isfinite(row.lag_168h_mw)
    with pytest.raises(InvalidRequestError, match=_NON_FINITE_PREDICTION_MESSAGE) as caught:
        _predict(fit=fit, evaluation_rows=(row,))
    assert caught.value.code == "invalid_request"


def test_later_row_non_finite_prediction_does_not_return_a_partial_tuple() -> None:
    fit = ConsumerLoadLag24h168hLinearRegressionFit(
        lag_24h_coefficient=1.0e308,
        lag_168h_coefficient=0.0,
        intercept_mw=0.0,
    )
    rows = (
        _row(hour=8, lag_24h_mw=0.0, lag_168h_mw=1.0, target_value_mw=3.0),
        _row(hour=9, lag_24h_mw=2.0, lag_168h_mw=1.0, target_value_mw=5.0),
    )
    with pytest.raises(InvalidRequestError, match=_NON_FINITE_PREDICTION_MESSAGE):
        _predict(fit=fit, evaluation_rows=rows)


def test_fit_and_evaluation_rows_are_not_mutated_and_repeated_calls_match() -> None:
    fit = ConsumerLoadLag24h168hLinearRegressionFit(
        lag_24h_coefficient=3.0,
        lag_168h_coefficient=5.0,
        intercept_mw=2.0,
    )
    first = _row(hour=8, lag_24h_mw=1.0, lag_168h_mw=1.0, target_value_mw=10.0)
    second = _row(hour=9, lag_24h_mw=2.0, lag_168h_mw=1.0, target_value_mw=13.0)
    rows = (first, second)
    original_fit = (fit.lag_24h_coefficient, fit.lag_168h_coefficient, fit.intercept_mw)
    original_ids = tuple(id(row) for row in rows)
    first_result = _predict(fit=fit, evaluation_rows=rows)
    second_result = _predict(fit=fit, evaluation_rows=rows)
    assert (fit.lag_24h_coefficient, fit.lag_168h_coefficient, fit.intercept_mw) == original_fit
    assert rows == (first, second)
    assert tuple(id(row) for row in rows) == original_ids
    assert rows[0] is first
    assert rows[1] is second
    assert first.lag_24h_mw == 1.0
    assert first.lag_168h_mw == 1.0
    assert first.target_value_mw == 10.0
    assert second.lag_24h_mw == 2.0
    assert first_result == second_result
    assert first_result is not second_result


def test_return_contract_uses_tuple_of_exact_prediction_dto() -> None:
    rows = (
        _row(hour=8, lag_24h_mw=1.0, lag_168h_mw=1.0, target_value_mw=10.0),
        _row(hour=9, lag_24h_mw=2.0, lag_168h_mw=1.0, target_value_mw=4.5),
    )
    result = _predict(evaluation_rows=rows)
    assert type(result) is tuple
    assert len(result) == 2
    for index, prediction in enumerate(result):
        assert type(prediction) is ConsumerLoadLag24h168hLinearRegressionPrediction
        assert type(prediction.predicted_value_mw) is float
        assert isfinite(prediction.predicted_value_mw)
        assert prediction.actual_value_mw == rows[index].target_value_mw


def test_feature_roles_are_not_swapped() -> None:
    row = _row(hour=8, lag_24h_mw=1.0, lag_168h_mw=2.0, target_value_mw=9.0)
    result = _predict(evaluation_rows=(row,))
    swapped = (
        _FINITE_FIT.intercept_mw
        + _FINITE_FIT.lag_24h_coefficient * row.lag_168h_mw
        + _FINITE_FIT.lag_168h_coefficient * row.lag_24h_mw
    )
    expected = (
        _FINITE_FIT.intercept_mw
        + _FINITE_FIT.lag_24h_coefficient * row.lag_24h_mw
        + _FINITE_FIT.lag_168h_coefficient * row.lag_168h_mw
    )
    assert result[0].predicted_value_mw == expected
    assert result[0].predicted_value_mw == 15.0
    assert swapped == 13.0
    assert result[0].predicted_value_mw != swapped
