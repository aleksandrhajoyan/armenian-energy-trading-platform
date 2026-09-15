"""Aligned three-way persistence-versus-OLS Consumer Load MAE comparison."""

from __future__ import annotations  # noqa: I001

from math import isfinite

import pytest

from tests.unit.domain._factories import utc
from energy_trading.application.errors import InvalidRequestError
from energy_trading.ml.consumer_load.lag_24h_168h_linear_regression_evaluation import (
    evaluate_consumer_load_lag_24h_168h_linear_regression_mae,
)
from energy_trading.ml.consumer_load.lag_24h_168h_linear_regression_prediction import (
    ConsumerLoadLag24h168hLinearRegressionPrediction,
)
from energy_trading.ml.consumer_load.lag_24h_linear_regression_evaluation import (
    evaluate_consumer_load_lag_24h_linear_regression_mae,
)
from energy_trading.ml.consumer_load.lag_24h_linear_regression_prediction import (
    ConsumerLoadLag24hLinearRegressionPrediction,
)
from energy_trading.ml.consumer_load.persistence_vs_lag_24h_vs_lag_24h_168h_ols_comparison import (
    ConsumerLoadPersistenceVsLag24hVsLag24h168hOLSMAEComparison,
    compare_consumer_load_persistence_vs_lag_24h_vs_lag_24h_168h_ols_mae,
)
from energy_trading.ml.consumer_load.previous_day_persistence_backtest import (
    PreviousDayPersistenceBacktestCase,
)
from energy_trading.ml.consumer_load.previous_day_persistence_evaluation import (
    evaluate_previous_day_persistence_mae,
)

_EMPTY_ALL_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires a non-empty aligned cohort."
)
_EMPTY_PERSISTENCE_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires a non-empty persistence cohort."
)
_EMPTY_LAG_24H_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires a non-empty one-feature cohort."
)
_EMPTY_LAG_24H_168H_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires a non-empty two-feature cohort."
)
_UNEQUAL_LENGTH_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires equal persistence, one-feature, and two-feature case "
    "counts."
)
_MIXED_PERSISTENCE_CONSUMER_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires persistence cases from exactly one consumer."
)
_MIXED_LAG_24H_CONSUMER_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires one-feature predictions from exactly one consumer."
)
_MIXED_LAG_24H_168H_CONSUMER_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires two-feature predictions from exactly one consumer."
)
_CONSUMER_MISMATCH_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires persistence cases, one-feature predictions, and "
    "two-feature predictions from the same consumer."
)
_DUPLICATE_PERSISTENCE_TIMESTAMP_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires unique persistence target timestamps."
)
_DUPLICATE_LAG_24H_TIMESTAMP_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires unique one-feature target timestamps."
)
_DUPLICATE_LAG_24H_168H_TIMESTAMP_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires unique two-feature target timestamps."
)
_OUT_OF_ORDER_PERSISTENCE_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires strictly increasing persistence target timestamps."
)
_OUT_OF_ORDER_LAG_24H_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires strictly increasing one-feature target timestamps."
)
_OUT_OF_ORDER_LAG_24H_168H_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires strictly increasing two-feature target timestamps."
)
_TIMESTAMP_MISMATCH_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires matching target timestamps at each aligned index."
)
_ACTUAL_MISMATCH_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires matching actual MW values at each aligned index."
)
_PERSISTENCE_EMPTY_CASES_MESSAGE = (
    "Previous-day persistence MAE evaluation requires at least one backtest case."
)
_LAG_24H_NON_FINITE_VALUES_MESSAGE = (
    "Consumer Load lag-24h linear regression MAE evaluation requires finite "
    "predicted and actual values."
)
_LAG_24H_168H_NON_FINITE_VALUES_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression MAE evaluation "
    "requires finite predicted and actual values."
)
_RESULT_FIELDS = (
    "case_count",
    "persistence_mae_mw",
    "lag_24h_mae_mw",
    "lag_24h_168h_mae_mw",
)


def _persistence_case(
    *,
    hour: int,
    predicted_value_mw: float,
    actual_value_mw: float,
    consumer_id: str = "consumer-1",
) -> PreviousDayPersistenceBacktestCase:
    return PreviousDayPersistenceBacktestCase(
        consumer_id=consumer_id,
        target_timestamp=utc(hour=hour),
        predicted_value_mw=predicted_value_mw,
        actual_value_mw=actual_value_mw,
    )


def _lag_24h_prediction(
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


def _lag_24h_168h_prediction(
    *,
    hour: int,
    predicted_value_mw: float,
    actual_value_mw: float,
    consumer_id: str = "consumer-1",
) -> ConsumerLoadLag24h168hLinearRegressionPrediction:
    return ConsumerLoadLag24h168hLinearRegressionPrediction(
        consumer_id=consumer_id,
        target_timestamp=utc(hour=hour),
        predicted_value_mw=predicted_value_mw,
        actual_value_mw=actual_value_mw,
    )


def _compare(
    persistence_cases: tuple[PreviousDayPersistenceBacktestCase, ...],
    lag_24h_predictions: tuple[ConsumerLoadLag24hLinearRegressionPrediction, ...],
    lag_24h_168h_predictions: tuple[ConsumerLoadLag24h168hLinearRegressionPrediction, ...],
) -> ConsumerLoadPersistenceVsLag24hVsLag24h168hOLSMAEComparison:
    return compare_consumer_load_persistence_vs_lag_24h_vs_lag_24h_168h_ols_mae(
        persistence_cases=persistence_cases,
        lag_24h_predictions=lag_24h_predictions,
        lag_24h_168h_predictions=lag_24h_168h_predictions,
    )


def test_aligned_cohort_reports_exact_case_count_and_three_mae_values() -> None:
    persistence_cases = (
        _persistence_case(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),
        _persistence_case(hour=11, predicted_value_mw=5.0, actual_value_mw=3.0),
        _persistence_case(hour=12, predicted_value_mw=8.0, actual_value_mw=11.0),
    )
    lag_24h_predictions = (
        _lag_24h_prediction(hour=10, predicted_value_mw=4.0, actual_value_mw=2.0),
        _lag_24h_prediction(hour=11, predicted_value_mw=6.0, actual_value_mw=3.0),
        _lag_24h_prediction(hour=12, predicted_value_mw=7.0, actual_value_mw=11.0),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h_prediction(hour=10, predicted_value_mw=3.0, actual_value_mw=2.0),
        _lag_24h_168h_prediction(hour=11, predicted_value_mw=4.0, actual_value_mw=3.0),
        _lag_24h_168h_prediction(hour=12, predicted_value_mw=10.0, actual_value_mw=11.0),
    )
    result = _compare(persistence_cases, lag_24h_predictions, lag_24h_168h_predictions)
    expected_persistence = (abs(1.0 - 2.0) + abs(5.0 - 3.0) + abs(8.0 - 11.0)) / 3
    expected_lag_24h = (abs(4.0 - 2.0) + abs(6.0 - 3.0) + abs(7.0 - 11.0)) / 3
    expected_lag_24h_168h = (abs(3.0 - 2.0) + abs(4.0 - 3.0) + abs(10.0 - 11.0)) / 3
    persistence_result = evaluate_previous_day_persistence_mae(cases=persistence_cases)
    lag_24h_result = evaluate_consumer_load_lag_24h_linear_regression_mae(
        predictions=lag_24h_predictions,
    )
    lag_24h_168h_result = evaluate_consumer_load_lag_24h_168h_linear_regression_mae(
        predictions=lag_24h_168h_predictions,
    )
    assert result.case_count == 3
    assert result.case_count == persistence_result.case_count
    assert result.case_count == lag_24h_result.case_count
    assert result.case_count == lag_24h_168h_result.case_count
    assert result.persistence_mae_mw == expected_persistence
    assert result.persistence_mae_mw == 2.0
    assert result.persistence_mae_mw == persistence_result.mae_mw
    assert result.lag_24h_mae_mw == expected_lag_24h
    assert result.lag_24h_mae_mw == 3.0
    assert result.lag_24h_mae_mw == lag_24h_result.mae_mw
    assert result.lag_24h_168h_mae_mw == expected_lag_24h_168h
    assert result.lag_24h_168h_mae_mw == 1.0
    assert result.lag_24h_168h_mae_mw == lag_24h_168h_result.mae_mw
    assert result.persistence_mae_mw != result.lag_24h_mae_mw
    assert result.persistence_mae_mw != result.lag_24h_168h_mae_mw
    assert result.lag_24h_mae_mw != result.lag_24h_168h_mae_mw


def test_result_is_frozen_slotted_with_exactly_four_fields() -> None:
    result = _compare(
        (_persistence_case(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),),
        (_lag_24h_prediction(hour=10, predicted_value_mw=4.0, actual_value_mw=2.0),),
        (_lag_24h_168h_prediction(hour=10, predicted_value_mw=3.0, actual_value_mw=2.0),),
    )
    assert ConsumerLoadPersistenceVsLag24hVsLag24h168hOLSMAEComparison.__slots__ == _RESULT_FIELDS
    assert result.__slots__ == _RESULT_FIELDS
    with pytest.raises(AttributeError):
        result.case_count = 0  # type: ignore[misc]
    assert not hasattr(result, "__dict__")
    forbidden_attrs = (
        "winner",
        "champion",
        "preferred_model",
        "selected_model",
        "better_model",
        "ranking",
        "rank",
        "improvement",
        "percentage_improvement",
        "relative_improvement",
        "delta",
        "ratio",
        "threshold",
        "recommendation",
        "rmse",
        "mape",
        "r2",
        "bias",
        "metadata",
        "model_name",
        "consumer_id",
        "trained_ols_mae_mw",
    )
    for name in forbidden_attrs:
        assert not hasattr(result, name)


def test_negative_finite_one_feature_prediction_is_scored_normally() -> None:
    result = _compare(
        (_persistence_case(hour=10, predicted_value_mw=4.0, actual_value_mw=4.0),),
        (_lag_24h_prediction(hour=10, predicted_value_mw=-4.0, actual_value_mw=4.0),),
        (_lag_24h_168h_prediction(hour=10, predicted_value_mw=5.0, actual_value_mw=4.0),),
    )
    assert result.persistence_mae_mw == 0.0
    assert result.lag_24h_mae_mw == 8.0
    assert result.lag_24h_mae_mw == abs(-4.0 - 4.0)
    assert result.lag_24h_mae_mw != abs(0.0 - 4.0)
    assert result.lag_24h_168h_mae_mw == 1.0


def test_negative_finite_two_feature_prediction_is_scored_normally() -> None:
    result = _compare(
        (_persistence_case(hour=10, predicted_value_mw=4.0, actual_value_mw=4.0),),
        (_lag_24h_prediction(hour=10, predicted_value_mw=5.0, actual_value_mw=4.0),),
        (_lag_24h_168h_prediction(hour=10, predicted_value_mw=-4.0, actual_value_mw=4.0),),
    )
    assert result.persistence_mae_mw == 0.0
    assert result.lag_24h_mae_mw == 1.0
    assert result.lag_24h_168h_mae_mw == 8.0
    assert result.lag_24h_168h_mae_mw == abs(-4.0 - 4.0)
    assert result.lag_24h_168h_mae_mw != abs(0.0 - 4.0)


def test_single_aligned_case_is_valid() -> None:
    result = _compare(
        (_persistence_case(hour=10, predicted_value_mw=4.5, actual_value_mw=7.25),),
        (_lag_24h_prediction(hour=10, predicted_value_mw=5.25, actual_value_mw=7.25),),
        (_lag_24h_168h_prediction(hour=10, predicted_value_mw=6.25, actual_value_mw=7.25),),
    )
    assert result.case_count == 1
    assert result.persistence_mae_mw == 2.75
    assert result.lag_24h_mae_mw == 2.0
    assert result.lag_24h_168h_mae_mw == 1.0


def test_all_empty_tuples_fail_closed() -> None:
    with pytest.raises(InvalidRequestError, match=_EMPTY_ALL_MESSAGE) as caught:
        _compare((), (), ())
    assert caught.value.code == "invalid_request"


def test_empty_persistence_and_nonempty_ols_cohorts_fail_closed() -> None:
    lag_24h = (_lag_24h_prediction(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),)
    lag_24h_168h = (_lag_24h_168h_prediction(hour=10, predicted_value_mw=1.5, actual_value_mw=2.0),)
    with pytest.raises(InvalidRequestError, match=_EMPTY_PERSISTENCE_MESSAGE) as caught:
        _compare((), lag_24h, lag_24h_168h)
    assert caught.value.code == "invalid_request"


def test_empty_one_feature_and_nonempty_other_cohorts_fail_closed() -> None:
    persistence = (_persistence_case(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),)
    lag_24h_168h = (_lag_24h_168h_prediction(hour=10, predicted_value_mw=1.5, actual_value_mw=2.0),)
    with pytest.raises(InvalidRequestError, match=_EMPTY_LAG_24H_MESSAGE) as caught:
        _compare(persistence, (), lag_24h_168h)
    assert caught.value.code == "invalid_request"


def test_empty_two_feature_and_nonempty_other_cohorts_fail_closed() -> None:
    persistence = (_persistence_case(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),)
    lag_24h = (_lag_24h_prediction(hour=10, predicted_value_mw=1.5, actual_value_mw=2.0),)
    with pytest.raises(InvalidRequestError, match=_EMPTY_LAG_24H_168H_MESSAGE) as caught:
        _compare(persistence, lag_24h, ())
    assert caught.value.code == "invalid_request"


def test_unequal_lengths_fail_closed_without_truncation() -> None:
    persistence_cases = (
        _persistence_case(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),
        _persistence_case(hour=11, predicted_value_mw=3.0, actual_value_mw=4.0),
    )
    lag_24h_predictions = (
        _lag_24h_prediction(hour=10, predicted_value_mw=1.5, actual_value_mw=2.0),
        _lag_24h_prediction(hour=11, predicted_value_mw=3.5, actual_value_mw=4.0),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h_prediction(hour=10, predicted_value_mw=1.25, actual_value_mw=2.0),
    )
    with pytest.raises(InvalidRequestError, match=_UNEQUAL_LENGTH_MESSAGE) as caught:
        _compare(persistence_cases, lag_24h_predictions, lag_24h_168h_predictions)
    assert caught.value.code == "invalid_request"


def test_mixed_persistence_consumers_fail_closed_without_raw_ids() -> None:
    persistence_cases = (
        _persistence_case(
            hour=10,
            predicted_value_mw=1.0,
            actual_value_mw=2.0,
            consumer_id="consumer-1",
        ),
        _persistence_case(
            hour=11,
            predicted_value_mw=3.0,
            actual_value_mw=4.0,
            consumer_id="consumer-2",
        ),
    )
    lag_24h_predictions = (
        _lag_24h_prediction(
            hour=10,
            predicted_value_mw=1.5,
            actual_value_mw=2.0,
            consumer_id="consumer-1",
        ),
        _lag_24h_prediction(
            hour=11,
            predicted_value_mw=3.5,
            actual_value_mw=4.0,
            consumer_id="consumer-1",
        ),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h_prediction(
            hour=10,
            predicted_value_mw=1.25,
            actual_value_mw=2.0,
            consumer_id="consumer-1",
        ),
        _lag_24h_168h_prediction(
            hour=11,
            predicted_value_mw=3.25,
            actual_value_mw=4.0,
            consumer_id="consumer-1",
        ),
    )
    with pytest.raises(InvalidRequestError, match=_MIXED_PERSISTENCE_CONSUMER_MESSAGE) as caught:
        _compare(persistence_cases, lag_24h_predictions, lag_24h_168h_predictions)
    assert caught.value.code == "invalid_request"
    assert "consumer-1" not in caught.value.message
    assert "consumer-2" not in caught.value.message


def test_mixed_one_feature_consumers_fail_closed_without_raw_ids() -> None:
    persistence_cases = (
        _persistence_case(
            hour=10,
            predicted_value_mw=1.0,
            actual_value_mw=2.0,
            consumer_id="consumer-1",
        ),
        _persistence_case(
            hour=11,
            predicted_value_mw=3.0,
            actual_value_mw=4.0,
            consumer_id="consumer-1",
        ),
    )
    lag_24h_predictions = (
        _lag_24h_prediction(
            hour=10,
            predicted_value_mw=1.5,
            actual_value_mw=2.0,
            consumer_id="consumer-1",
        ),
        _lag_24h_prediction(
            hour=11,
            predicted_value_mw=3.5,
            actual_value_mw=4.0,
            consumer_id="consumer-2",
        ),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h_prediction(
            hour=10,
            predicted_value_mw=1.25,
            actual_value_mw=2.0,
            consumer_id="consumer-1",
        ),
        _lag_24h_168h_prediction(
            hour=11,
            predicted_value_mw=3.25,
            actual_value_mw=4.0,
            consumer_id="consumer-1",
        ),
    )
    with pytest.raises(InvalidRequestError, match=_MIXED_LAG_24H_CONSUMER_MESSAGE) as caught:
        _compare(persistence_cases, lag_24h_predictions, lag_24h_168h_predictions)
    assert caught.value.code == "invalid_request"
    assert "consumer-1" not in caught.value.message
    assert "consumer-2" not in caught.value.message


def test_mixed_two_feature_consumers_fail_closed_without_raw_ids() -> None:
    persistence_cases = (
        _persistence_case(
            hour=10,
            predicted_value_mw=1.0,
            actual_value_mw=2.0,
            consumer_id="consumer-1",
        ),
        _persistence_case(
            hour=11,
            predicted_value_mw=3.0,
            actual_value_mw=4.0,
            consumer_id="consumer-1",
        ),
    )
    lag_24h_predictions = (
        _lag_24h_prediction(
            hour=10,
            predicted_value_mw=1.5,
            actual_value_mw=2.0,
            consumer_id="consumer-1",
        ),
        _lag_24h_prediction(
            hour=11,
            predicted_value_mw=3.5,
            actual_value_mw=4.0,
            consumer_id="consumer-1",
        ),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h_prediction(
            hour=10,
            predicted_value_mw=1.25,
            actual_value_mw=2.0,
            consumer_id="consumer-1",
        ),
        _lag_24h_168h_prediction(
            hour=11,
            predicted_value_mw=3.25,
            actual_value_mw=4.0,
            consumer_id="consumer-2",
        ),
    )
    with pytest.raises(
        InvalidRequestError,
        match=_MIXED_LAG_24H_168H_CONSUMER_MESSAGE,
    ) as caught:
        _compare(persistence_cases, lag_24h_predictions, lag_24h_168h_predictions)
    assert caught.value.code == "invalid_request"
    assert "consumer-1" not in caught.value.message
    assert "consumer-2" not in caught.value.message


def test_consumer_mismatch_across_cohorts_fails_closed_without_raw_ids() -> None:
    persistence_cases = (
        _persistence_case(
            hour=10,
            predicted_value_mw=1.0,
            actual_value_mw=2.0,
            consumer_id="consumer-1",
        ),
    )
    lag_24h_predictions = (
        _lag_24h_prediction(
            hour=10,
            predicted_value_mw=1.5,
            actual_value_mw=2.0,
            consumer_id="consumer-1",
        ),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h_prediction(
            hour=10,
            predicted_value_mw=1.25,
            actual_value_mw=2.0,
            consumer_id="consumer-2",
        ),
    )
    with pytest.raises(InvalidRequestError, match=_CONSUMER_MISMATCH_MESSAGE) as caught:
        _compare(persistence_cases, lag_24h_predictions, lag_24h_168h_predictions)
    assert caught.value.code == "invalid_request"
    assert "consumer-1" not in caught.value.message
    assert "consumer-2" not in caught.value.message


def test_persistence_duplicate_timestamp_fails_closed() -> None:
    stamp = utc(hour=10)
    persistence_cases = (
        PreviousDayPersistenceBacktestCase(
            consumer_id="consumer-1",
            target_timestamp=stamp,
            predicted_value_mw=1.0,
            actual_value_mw=2.0,
        ),
        PreviousDayPersistenceBacktestCase(
            consumer_id="consumer-1",
            target_timestamp=stamp,
            predicted_value_mw=3.0,
            actual_value_mw=4.0,
        ),
    )
    lag_24h_predictions = (
        _lag_24h_prediction(hour=10, predicted_value_mw=1.5, actual_value_mw=2.0),
        _lag_24h_prediction(hour=11, predicted_value_mw=3.5, actual_value_mw=4.0),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h_prediction(hour=10, predicted_value_mw=1.25, actual_value_mw=2.0),
        _lag_24h_168h_prediction(hour=11, predicted_value_mw=3.25, actual_value_mw=4.0),
    )
    with pytest.raises(
        InvalidRequestError,
        match=_DUPLICATE_PERSISTENCE_TIMESTAMP_MESSAGE,
    ) as caught:
        _compare(persistence_cases, lag_24h_predictions, lag_24h_168h_predictions)
    assert caught.value.code == "invalid_request"


def test_one_feature_duplicate_timestamp_fails_closed() -> None:
    stamp = utc(hour=10)
    persistence_cases = (
        _persistence_case(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),
        _persistence_case(hour=11, predicted_value_mw=3.0, actual_value_mw=4.0),
    )
    lag_24h_predictions = (
        ConsumerLoadLag24hLinearRegressionPrediction(
            consumer_id="consumer-1",
            target_timestamp=stamp,
            predicted_value_mw=1.5,
            actual_value_mw=2.0,
        ),
        ConsumerLoadLag24hLinearRegressionPrediction(
            consumer_id="consumer-1",
            target_timestamp=stamp,
            predicted_value_mw=3.5,
            actual_value_mw=4.0,
        ),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h_prediction(hour=10, predicted_value_mw=1.25, actual_value_mw=2.0),
        _lag_24h_168h_prediction(hour=11, predicted_value_mw=3.25, actual_value_mw=4.0),
    )
    with pytest.raises(
        InvalidRequestError,
        match=_DUPLICATE_LAG_24H_TIMESTAMP_MESSAGE,
    ) as caught:
        _compare(persistence_cases, lag_24h_predictions, lag_24h_168h_predictions)
    assert caught.value.code == "invalid_request"


def test_two_feature_duplicate_timestamp_fails_closed() -> None:
    stamp = utc(hour=10)
    persistence_cases = (
        _persistence_case(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),
        _persistence_case(hour=11, predicted_value_mw=3.0, actual_value_mw=4.0),
    )
    lag_24h_predictions = (
        _lag_24h_prediction(hour=10, predicted_value_mw=1.5, actual_value_mw=2.0),
        _lag_24h_prediction(hour=11, predicted_value_mw=3.5, actual_value_mw=4.0),
    )
    lag_24h_168h_predictions = (
        ConsumerLoadLag24h168hLinearRegressionPrediction(
            consumer_id="consumer-1",
            target_timestamp=stamp,
            predicted_value_mw=1.25,
            actual_value_mw=2.0,
        ),
        ConsumerLoadLag24h168hLinearRegressionPrediction(
            consumer_id="consumer-1",
            target_timestamp=stamp,
            predicted_value_mw=3.25,
            actual_value_mw=4.0,
        ),
    )
    with pytest.raises(
        InvalidRequestError,
        match=_DUPLICATE_LAG_24H_168H_TIMESTAMP_MESSAGE,
    ) as caught:
        _compare(persistence_cases, lag_24h_predictions, lag_24h_168h_predictions)
    assert caught.value.code == "invalid_request"


def test_persistence_out_of_order_timestamps_fail_closed() -> None:
    persistence_cases = (
        _persistence_case(hour=12, predicted_value_mw=1.0, actual_value_mw=2.0),
        _persistence_case(hour=10, predicted_value_mw=3.0, actual_value_mw=4.0),
    )
    lag_24h_predictions = (
        _lag_24h_prediction(hour=10, predicted_value_mw=1.5, actual_value_mw=2.0),
        _lag_24h_prediction(hour=12, predicted_value_mw=3.5, actual_value_mw=4.0),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h_prediction(hour=10, predicted_value_mw=1.25, actual_value_mw=2.0),
        _lag_24h_168h_prediction(hour=12, predicted_value_mw=3.25, actual_value_mw=4.0),
    )
    with pytest.raises(InvalidRequestError, match=_OUT_OF_ORDER_PERSISTENCE_MESSAGE) as caught:
        _compare(persistence_cases, lag_24h_predictions, lag_24h_168h_predictions)
    assert caught.value.code == "invalid_request"


def test_one_feature_out_of_order_timestamps_fail_closed() -> None:
    persistence_cases = (
        _persistence_case(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),
        _persistence_case(hour=12, predicted_value_mw=3.0, actual_value_mw=4.0),
    )
    lag_24h_predictions = (
        _lag_24h_prediction(hour=12, predicted_value_mw=1.5, actual_value_mw=2.0),
        _lag_24h_prediction(hour=10, predicted_value_mw=3.5, actual_value_mw=4.0),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h_prediction(hour=10, predicted_value_mw=1.25, actual_value_mw=2.0),
        _lag_24h_168h_prediction(hour=12, predicted_value_mw=3.25, actual_value_mw=4.0),
    )
    with pytest.raises(InvalidRequestError, match=_OUT_OF_ORDER_LAG_24H_MESSAGE) as caught:
        _compare(persistence_cases, lag_24h_predictions, lag_24h_168h_predictions)
    assert caught.value.code == "invalid_request"


def test_two_feature_out_of_order_timestamps_fail_closed() -> None:
    persistence_cases = (
        _persistence_case(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),
        _persistence_case(hour=12, predicted_value_mw=3.0, actual_value_mw=4.0),
    )
    lag_24h_predictions = (
        _lag_24h_prediction(hour=10, predicted_value_mw=1.5, actual_value_mw=2.0),
        _lag_24h_prediction(hour=12, predicted_value_mw=3.5, actual_value_mw=4.0),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h_prediction(hour=12, predicted_value_mw=1.25, actual_value_mw=2.0),
        _lag_24h_168h_prediction(hour=10, predicted_value_mw=3.25, actual_value_mw=4.0),
    )
    with pytest.raises(InvalidRequestError, match=_OUT_OF_ORDER_LAG_24H_168H_MESSAGE) as caught:
        _compare(persistence_cases, lag_24h_predictions, lag_24h_168h_predictions)
    assert caught.value.code == "invalid_request"


def test_same_timestamps_in_different_order_fail_closed_without_sorting() -> None:
    persistence_cases = (
        _persistence_case(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),
        _persistence_case(hour=12, predicted_value_mw=3.0, actual_value_mw=4.0),
    )
    lag_24h_predictions = (
        _lag_24h_prediction(hour=12, predicted_value_mw=1.5, actual_value_mw=4.0),
        _lag_24h_prediction(hour=10, predicted_value_mw=3.5, actual_value_mw=2.0),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h_prediction(hour=10, predicted_value_mw=1.25, actual_value_mw=2.0),
        _lag_24h_168h_prediction(hour=12, predicted_value_mw=3.25, actual_value_mw=4.0),
    )
    with pytest.raises(InvalidRequestError, match=_OUT_OF_ORDER_LAG_24H_MESSAGE) as caught:
        _compare(persistence_cases, lag_24h_predictions, lag_24h_168h_predictions)
    assert caught.value.code == "invalid_request"


def test_persistence_versus_one_feature_timestamp_mismatch_fails_closed() -> None:
    persistence_cases = (
        _persistence_case(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),
        _persistence_case(hour=12, predicted_value_mw=3.0, actual_value_mw=4.0),
    )
    lag_24h_predictions = (
        _lag_24h_prediction(hour=10, predicted_value_mw=1.5, actual_value_mw=2.0),
        _lag_24h_prediction(hour=13, predicted_value_mw=3.5, actual_value_mw=4.0),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h_prediction(hour=10, predicted_value_mw=1.25, actual_value_mw=2.0),
        _lag_24h_168h_prediction(hour=12, predicted_value_mw=3.25, actual_value_mw=4.0),
    )
    with pytest.raises(InvalidRequestError, match=_TIMESTAMP_MISMATCH_MESSAGE) as caught:
        _compare(persistence_cases, lag_24h_predictions, lag_24h_168h_predictions)
    assert caught.value.code == "invalid_request"


def test_persistence_versus_two_feature_timestamp_mismatch_fails_closed() -> None:
    persistence_cases = (
        _persistence_case(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),
        _persistence_case(hour=12, predicted_value_mw=3.0, actual_value_mw=4.0),
    )
    lag_24h_predictions = (
        _lag_24h_prediction(hour=10, predicted_value_mw=1.5, actual_value_mw=2.0),
        _lag_24h_prediction(hour=12, predicted_value_mw=3.5, actual_value_mw=4.0),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h_prediction(hour=10, predicted_value_mw=1.25, actual_value_mw=2.0),
        _lag_24h_168h_prediction(hour=13, predicted_value_mw=3.25, actual_value_mw=4.0),
    )
    with pytest.raises(InvalidRequestError, match=_TIMESTAMP_MISMATCH_MESSAGE) as caught:
        _compare(persistence_cases, lag_24h_predictions, lag_24h_168h_predictions)
    assert caught.value.code == "invalid_request"


def test_one_feature_versus_two_feature_timestamp_mismatch_fails_closed() -> None:
    persistence_cases = (
        _persistence_case(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),
        _persistence_case(hour=12, predicted_value_mw=3.0, actual_value_mw=4.0),
    )
    lag_24h_predictions = (
        _lag_24h_prediction(hour=10, predicted_value_mw=1.5, actual_value_mw=2.0),
        _lag_24h_prediction(hour=13, predicted_value_mw=3.5, actual_value_mw=4.0),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h_prediction(hour=10, predicted_value_mw=1.25, actual_value_mw=2.0),
        _lag_24h_168h_prediction(hour=14, predicted_value_mw=3.25, actual_value_mw=4.0),
    )
    with pytest.raises(InvalidRequestError, match=_TIMESTAMP_MISMATCH_MESSAGE) as caught:
        _compare(persistence_cases, lag_24h_predictions, lag_24h_168h_predictions)
    assert caught.value.code == "invalid_request"


def test_actual_mismatch_fails_closed_without_numeric_values() -> None:
    persistence_cases = (_persistence_case(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),)
    lag_24h_predictions = (
        _lag_24h_prediction(hour=10, predicted_value_mw=1.5, actual_value_mw=2.0),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h_prediction(hour=10, predicted_value_mw=1.25, actual_value_mw=9.75),
    )
    with pytest.raises(InvalidRequestError, match=_ACTUAL_MISMATCH_MESSAGE) as caught:
        _compare(persistence_cases, lag_24h_predictions, lag_24h_168h_predictions)
    assert caught.value.code == "invalid_request"
    assert "2.0" not in caught.value.message
    assert "9.75" not in caught.value.message


def test_persistence_evaluator_errors_propagate(monkeypatch: pytest.MonkeyPatch) -> None:
    persistence_cases = (_persistence_case(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),)
    lag_24h_predictions = (
        _lag_24h_prediction(hour=10, predicted_value_mw=1.5, actual_value_mw=2.0),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h_prediction(hour=10, predicted_value_mw=1.25, actual_value_mw=2.0),
    )

    def _raise_persistence_error(
        *,
        cases: tuple[PreviousDayPersistenceBacktestCase, ...],
    ) -> None:
        del cases
        raise InvalidRequestError(_PERSISTENCE_EMPTY_CASES_MESSAGE)

    monkeypatch.setattr(
        "energy_trading.ml.consumer_load.persistence_vs_lag_24h_vs_lag_24h_168h_ols_comparison."
        "evaluate_previous_day_persistence_mae",
        _raise_persistence_error,
    )
    with pytest.raises(InvalidRequestError, match=_PERSISTENCE_EMPTY_CASES_MESSAGE) as caught:
        _compare(persistence_cases, lag_24h_predictions, lag_24h_168h_predictions)
    assert caught.value.code == "invalid_request"


def test_one_feature_evaluator_errors_propagate() -> None:
    persistence_cases = (_persistence_case(hour=10, predicted_value_mw=1.5, actual_value_mw=2.0),)
    lag_24h_predictions = (
        _lag_24h_prediction(hour=10, predicted_value_mw=float("nan"), actual_value_mw=2.0),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h_prediction(hour=10, predicted_value_mw=1.25, actual_value_mw=2.0),
    )
    with pytest.raises(
        InvalidRequestError,
        match=_LAG_24H_NON_FINITE_VALUES_MESSAGE,
    ) as caught:
        _compare(persistence_cases, lag_24h_predictions, lag_24h_168h_predictions)
    assert caught.value.code == "invalid_request"


def test_two_feature_evaluator_errors_propagate() -> None:
    persistence_cases = (_persistence_case(hour=10, predicted_value_mw=1.5, actual_value_mw=2.0),)
    lag_24h_predictions = (
        _lag_24h_prediction(hour=10, predicted_value_mw=1.5, actual_value_mw=2.0),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h_prediction(hour=10, predicted_value_mw=float("nan"), actual_value_mw=2.0),
    )
    with pytest.raises(
        InvalidRequestError,
        match=_LAG_24H_168H_NON_FINITE_VALUES_MESSAGE,
    ) as caught:
        _compare(persistence_cases, lag_24h_predictions, lag_24h_168h_predictions)
    assert caught.value.code == "invalid_request"


def test_input_tuples_are_not_mutated() -> None:
    first_case = _persistence_case(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0)
    second_case = _persistence_case(hour=12, predicted_value_mw=5.0, actual_value_mw=3.0)
    first_lag_24h = _lag_24h_prediction(hour=10, predicted_value_mw=2.0, actual_value_mw=2.0)
    second_lag_24h = _lag_24h_prediction(hour=12, predicted_value_mw=6.0, actual_value_mw=3.0)
    first_lag_24h_168h = _lag_24h_168h_prediction(
        hour=10,
        predicted_value_mw=3.0,
        actual_value_mw=2.0,
    )
    second_lag_24h_168h = _lag_24h_168h_prediction(
        hour=12,
        predicted_value_mw=4.0,
        actual_value_mw=3.0,
    )
    persistence_cases = (first_case, second_case)
    lag_24h_predictions = (first_lag_24h, second_lag_24h)
    lag_24h_168h_predictions = (first_lag_24h_168h, second_lag_24h_168h)
    original_case_ids = tuple(id(item) for item in persistence_cases)
    original_lag_24h_ids = tuple(id(item) for item in lag_24h_predictions)
    original_lag_24h_168h_ids = tuple(id(item) for item in lag_24h_168h_predictions)
    _compare(persistence_cases, lag_24h_predictions, lag_24h_168h_predictions)
    assert persistence_cases == (first_case, second_case)
    assert lag_24h_predictions == (first_lag_24h, second_lag_24h)
    assert lag_24h_168h_predictions == (first_lag_24h_168h, second_lag_24h_168h)
    assert tuple(id(item) for item in persistence_cases) == original_case_ids
    assert tuple(id(item) for item in lag_24h_predictions) == original_lag_24h_ids
    assert tuple(id(item) for item in lag_24h_168h_predictions) == original_lag_24h_168h_ids
    assert first_case.predicted_value_mw == 1.0
    assert first_lag_24h.predicted_value_mw == 2.0
    assert first_lag_24h_168h.predicted_value_mw == 3.0


def test_repeated_equal_input_returns_value_equal_result() -> None:
    persistence_cases = (
        _persistence_case(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),
        _persistence_case(hour=12, predicted_value_mw=5.0, actual_value_mw=3.0),
    )
    lag_24h_predictions = (
        _lag_24h_prediction(hour=10, predicted_value_mw=2.0, actual_value_mw=2.0),
        _lag_24h_prediction(hour=12, predicted_value_mw=6.0, actual_value_mw=3.0),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h_prediction(hour=10, predicted_value_mw=3.0, actual_value_mw=2.0),
        _lag_24h_168h_prediction(hour=12, predicted_value_mw=4.0, actual_value_mw=3.0),
    )
    first = _compare(persistence_cases, lag_24h_predictions, lag_24h_168h_predictions)
    second = _compare(persistence_cases, lag_24h_predictions, lag_24h_168h_predictions)
    assert first == second
    assert first is not second


def test_return_contract_uses_int_count_and_finite_float_mae() -> None:
    persistence_cases = (_persistence_case(hour=10, predicted_value_mw=4.5, actual_value_mw=7.25),)
    lag_24h_predictions = (
        _lag_24h_prediction(hour=10, predicted_value_mw=5.25, actual_value_mw=7.25),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h_prediction(hour=10, predicted_value_mw=6.25, actual_value_mw=7.25),
    )
    result = _compare(persistence_cases, lag_24h_predictions, lag_24h_168h_predictions)
    assert isinstance(result, ConsumerLoadPersistenceVsLag24hVsLag24h168hOLSMAEComparison)
    assert isinstance(persistence_cases, tuple)
    assert isinstance(lag_24h_predictions, tuple)
    assert isinstance(lag_24h_168h_predictions, tuple)
    assert type(result.case_count) is int
    assert type(result.persistence_mae_mw) is float
    assert type(result.lag_24h_mae_mw) is float
    assert type(result.lag_24h_168h_mae_mw) is float
    assert isfinite(result.persistence_mae_mw)
    assert isfinite(result.lag_24h_mae_mw)
    assert isfinite(result.lag_24h_168h_mae_mw)
    assert result.case_count == 1
    assert result.persistence_mae_mw == 2.75
    assert result.lag_24h_mae_mw == 2.0
    assert result.lag_24h_168h_mae_mw == 1.0
