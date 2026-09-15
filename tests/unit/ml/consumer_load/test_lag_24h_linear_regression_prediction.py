"""Lag-24h ordinary-least-squares Consumer Load evaluation prediction."""

from __future__ import annotations

from math import isfinite

import pytest

from energy_trading.application.errors import InvalidRequestError
from energy_trading.ml.consumer_load.lag_24h_features import ConsumerLoadLag24hFeatureRow
from energy_trading.ml.consumer_load.lag_24h_linear_regression import (
    ConsumerLoadLag24hLinearRegressionFit,
)
from energy_trading.ml.consumer_load.lag_24h_linear_regression_prediction import (
    ConsumerLoadLag24hLinearRegressionPrediction,
    predict_consumer_load_lag_24h_linear_regression,
)
from tests.unit.domain._factories import utc

_EMPTY_ROWS_MESSAGE = (
    "Consumer Load lag-24h linear regression prediction requires at least one evaluation row."
)
_MIXED_CONSUMER_MESSAGE = (
    "Consumer Load lag-24h linear regression prediction requires rows from exactly one consumer."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "Consumer Load lag-24h linear regression prediction requires unique target timestamps."
)
_OUT_OF_ORDER_MESSAGE = (
    "Consumer Load lag-24h linear regression prediction requires strictly "
    "increasing target timestamps."
)
_NON_FINITE_FIT_MESSAGE = (
    "Consumer Load lag-24h linear regression prediction requires finite slope and intercept."
)
_NON_FINITE_PREDICTION_MESSAGE = (
    "Consumer Load lag-24h linear regression prediction requires finite predicted values."
)
_PREDICTION_FIELDS = (
    "consumer_id",
    "target_timestamp",
    "predicted_value_mw",
    "actual_value_mw",
)
_FINITE_FIT = ConsumerLoadLag24hLinearRegressionFit(slope=2.0, intercept_mw=1.0)


def _row(
    *,
    hour: int,
    day: int = 1,
    value_mw: float = 8.0,
    lag_mw: float = 4.0,
    consumer_id: str = "consumer-1",
) -> ConsumerLoadLag24hFeatureRow:
    return ConsumerLoadLag24hFeatureRow(
        consumer_id=consumer_id,
        target_timestamp=utc(day=day, hour=hour),
        lag_24h_mw=lag_mw,
        target_value_mw=value_mw,
    )


def _predict(
    *,
    fit: ConsumerLoadLag24hLinearRegressionFit = _FINITE_FIT,
    evaluation_rows: tuple[ConsumerLoadLag24hFeatureRow, ...],
) -> tuple[ConsumerLoadLag24hLinearRegressionPrediction, ...]:
    return predict_consumer_load_lag_24h_linear_regression(
        fit=fit,
        evaluation_rows=evaluation_rows,
    )


def test_basic_deterministic_prediction_uses_exact_ols_formula() -> None:
    rows = (
        _row(hour=10, lag_mw=1.0, value_mw=9.0),
        _row(hour=12, lag_mw=2.0, value_mw=8.0),
        _row(hour=14, lag_mw=3.0, value_mw=7.0),
    )
    result = _predict(evaluation_rows=rows)
    assert result[0].predicted_value_mw == 3.0
    assert result[1].predicted_value_mw == 5.0
    assert result[2].predicted_value_mw == 7.0
    assert result[0].predicted_value_mw == 2.0 * 1.0 + 1.0
    assert result[1].predicted_value_mw == 2.0 * 2.0 + 1.0
    assert result[2].predicted_value_mw == 2.0 * 3.0 + 1.0


def test_identity_and_actual_target_are_preserved_in_input_order() -> None:
    first = _row(hour=10, lag_mw=1.0, value_mw=9.5)
    second = _row(hour=12, lag_mw=2.0, value_mw=4.25)
    result = _predict(evaluation_rows=(first, second))
    assert result[0].consumer_id == first.consumer_id
    assert result[1].consumer_id == second.consumer_id
    assert result[0].target_timestamp == first.target_timestamp
    assert result[1].target_timestamp == second.target_timestamp
    assert result[0].actual_value_mw == first.target_value_mw
    assert result[1].actual_value_mw == second.target_value_mw
    assert result[0].actual_value_mw is first.target_value_mw
    assert result[1].actual_value_mw is second.target_value_mw
    assert tuple(item.target_timestamp for item in result) == (
        first.target_timestamp,
        second.target_timestamp,
    )


def test_prediction_dto_is_frozen_slotted_with_exactly_four_fields() -> None:
    result = _predict(evaluation_rows=(_row(hour=10, lag_mw=1.0, value_mw=9.0),))
    prediction = result[0]
    assert ConsumerLoadLag24hLinearRegressionPrediction.__slots__ == _PREDICTION_FIELDS
    assert prediction.__slots__ == _PREDICTION_FIELDS
    with pytest.raises(AttributeError):
        prediction.predicted_value_mw = 0.0  # type: ignore[misc]
    assert not hasattr(prediction, "__dict__")
    forbidden_attrs = (
        "forecast_id",
        "generated_at",
        "model_name",
        "confidence",
        "mae",
        "rmse",
        "metadata",
        "workflow_id",
    )
    for name in forbidden_attrs:
        assert not hasattr(prediction, name)


def test_negative_finite_prediction_is_preserved_without_clamping() -> None:
    fit = ConsumerLoadLag24hLinearRegressionFit(slope=1.0, intercept_mw=-5.0)
    result = _predict(fit=fit, evaluation_rows=(_row(hour=10, lag_mw=1.0, value_mw=4.0),))
    assert result[0].predicted_value_mw == -4.0
    assert result[0].predicted_value_mw < 0.0
    assert result[0].actual_value_mw == 4.0


def test_exact_finite_zero_prediction_is_valid() -> None:
    fit = ConsumerLoadLag24hLinearRegressionFit(slope=1.0, intercept_mw=-2.0)
    result = _predict(fit=fit, evaluation_rows=(_row(hour=10, lag_mw=2.0, value_mw=6.0),))
    assert result[0].predicted_value_mw == 0.0
    assert isfinite(result[0].predicted_value_mw)


def test_empty_evaluation_input_fails_closed() -> None:
    with pytest.raises(InvalidRequestError, match=_EMPTY_ROWS_MESSAGE) as caught:
        _predict(evaluation_rows=())
    assert caught.value.code == "invalid_request"


def test_mixed_consumers_fail_closed_without_raw_ids() -> None:
    rows = (
        _row(hour=10, lag_mw=1.0, value_mw=3.0, consumer_id="consumer-1"),
        _row(hour=12, lag_mw=2.0, value_mw=5.0, consumer_id="consumer-2"),
    )
    with pytest.raises(InvalidRequestError, match=_MIXED_CONSUMER_MESSAGE) as caught:
        _predict(evaluation_rows=rows)
    assert caught.value.code == "invalid_request"
    assert "consumer-1" not in caught.value.message
    assert "consumer-2" not in caught.value.message


def test_duplicate_target_timestamps_fail_closed() -> None:
    stamp = utc(hour=12)
    rows = (
        _row(hour=10, lag_mw=1.0, value_mw=3.0),
        ConsumerLoadLag24hFeatureRow(
            consumer_id="consumer-1",
            target_timestamp=stamp,
            lag_24h_mw=2.0,
            target_value_mw=5.0,
        ),
        ConsumerLoadLag24hFeatureRow(
            consumer_id="consumer-1",
            target_timestamp=stamp,
            lag_24h_mw=3.0,
            target_value_mw=7.0,
        ),
    )
    with pytest.raises(InvalidRequestError, match=_DUPLICATE_TIMESTAMP_MESSAGE) as caught:
        _predict(evaluation_rows=rows)
    assert caught.value.code == "invalid_request"


def test_out_of_order_timestamps_fail_closed() -> None:
    rows = (
        _row(hour=14, lag_mw=2.0, value_mw=5.0),
        _row(hour=10, lag_mw=1.0, value_mw=3.0),
    )
    with pytest.raises(InvalidRequestError, match=_OUT_OF_ORDER_MESSAGE) as caught:
        _predict(evaluation_rows=rows)
    assert caught.value.code == "invalid_request"


def test_input_order_is_not_silently_sorted() -> None:
    rows = (
        _row(hour=14, lag_mw=2.0, value_mw=5.0),
        _row(hour=10, lag_mw=1.0, value_mw=3.0),
    )
    with pytest.raises(InvalidRequestError, match=_OUT_OF_ORDER_MESSAGE):
        _predict(evaluation_rows=rows)


@pytest.mark.parametrize("slope", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_slope_is_rejected(slope: float) -> None:
    fit = ConsumerLoadLag24hLinearRegressionFit(slope=slope, intercept_mw=1.0)
    with pytest.raises(InvalidRequestError, match=_NON_FINITE_FIT_MESSAGE) as caught:
        _predict(fit=fit, evaluation_rows=(_row(hour=10, lag_mw=1.0, value_mw=3.0),))
    assert caught.value.code == "invalid_request"


@pytest.mark.parametrize("intercept_mw", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_intercept_is_rejected(intercept_mw: float) -> None:
    fit = ConsumerLoadLag24hLinearRegressionFit(slope=2.0, intercept_mw=intercept_mw)
    with pytest.raises(InvalidRequestError, match=_NON_FINITE_FIT_MESSAGE) as caught:
        _predict(fit=fit, evaluation_rows=(_row(hour=10, lag_mw=1.0, value_mw=3.0),))
    assert caught.value.code == "invalid_request"


def test_non_finite_calculated_prediction_is_rejected() -> None:
    fit = ConsumerLoadLag24hLinearRegressionFit(slope=1e308, intercept_mw=0.0)
    assert isfinite(fit.slope)
    assert isfinite(fit.intercept_mw)
    row = _row(hour=10, lag_mw=2.0, value_mw=3.0)
    assert isfinite(row.lag_24h_mw)
    with pytest.raises(InvalidRequestError, match=_NON_FINITE_PREDICTION_MESSAGE) as caught:
        _predict(fit=fit, evaluation_rows=(row,))
    assert caught.value.code == "invalid_request"


def test_fit_and_evaluation_rows_are_not_mutated_and_repeated_calls_match() -> None:
    fit = ConsumerLoadLag24hLinearRegressionFit(slope=2.0, intercept_mw=1.0)
    first = _row(hour=10, lag_mw=1.0, value_mw=9.0)
    second = _row(hour=12, lag_mw=2.0, value_mw=8.0)
    rows = (first, second)
    original_fit = (fit.slope, fit.intercept_mw)
    original_ids = tuple(id(row) for row in rows)
    first_result = _predict(fit=fit, evaluation_rows=rows)
    second_result = _predict(fit=fit, evaluation_rows=rows)
    assert (fit.slope, fit.intercept_mw) == original_fit
    assert rows == (first, second)
    assert tuple(id(row) for row in rows) == original_ids
    assert rows[0] is first
    assert rows[1] is second
    assert first.lag_24h_mw == 1.0
    assert first.target_value_mw == 9.0
    assert second.lag_24h_mw == 2.0
    assert second.target_value_mw == 8.0
    assert first_result == second_result
    assert first_result is not second_result


def test_return_contract_uses_tuple_of_finite_floats_and_original_actuals() -> None:
    rows = (
        _row(hour=10, lag_mw=1.0, value_mw=9.0),
        _row(hour=12, lag_mw=2.0, value_mw=4.5),
    )
    result = _predict(evaluation_rows=rows)
    assert type(result) is tuple
    assert len(result) == 2
    for index, prediction in enumerate(result):
        assert isinstance(prediction, ConsumerLoadLag24hLinearRegressionPrediction)
        assert type(prediction.predicted_value_mw) is float
        assert isfinite(prediction.predicted_value_mw)
        assert prediction.actual_value_mw == rows[index].target_value_mw
