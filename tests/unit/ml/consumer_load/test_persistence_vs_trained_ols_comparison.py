"""Aligned persistence-versus-trained OLS Consumer Load MAE comparison."""

from __future__ import annotations  # noqa: I001

from math import isfinite

import pytest

from tests.unit.domain._factories import utc
from energy_trading.application.errors import InvalidRequestError
from energy_trading.ml.consumer_load.lag_24h_linear_regression_prediction import (
    ConsumerLoadLag24hLinearRegressionPrediction,
)
from energy_trading.ml.consumer_load.persistence_vs_trained_ols_comparison import (
    ConsumerLoadPersistenceVsTrainedOLSMAEComparison,
    compare_consumer_load_persistence_vs_trained_ols_mae,
)
from energy_trading.ml.consumer_load.previous_day_persistence_backtest import (
    PreviousDayPersistenceBacktestCase,
)

_EMPTY_BOTH_MESSAGE = (
    "Consumer Load persistence-versus-trained OLS MAE comparison requires "
    "a non-empty aligned cohort."
)
_EMPTY_PERSISTENCE_MESSAGE = (
    "Consumer Load persistence-versus-trained OLS MAE comparison requires "
    "a non-empty persistence cohort."
)
_EMPTY_TRAINED_MESSAGE = (
    "Consumer Load persistence-versus-trained OLS MAE comparison requires "
    "a non-empty trained OLS cohort."
)
_UNEQUAL_LENGTH_MESSAGE = (
    "Consumer Load persistence-versus-trained OLS MAE comparison requires "
    "equal persistence and trained case counts."
)
_MIXED_PERSISTENCE_CONSUMER_MESSAGE = (
    "Consumer Load persistence-versus-trained OLS MAE comparison requires "
    "persistence cases from exactly one consumer."
)
_MIXED_TRAINED_CONSUMER_MESSAGE = (
    "Consumer Load persistence-versus-trained OLS MAE comparison requires "
    "trained predictions from exactly one consumer."
)
_CONSUMER_MISMATCH_MESSAGE = (
    "Consumer Load persistence-versus-trained OLS MAE comparison requires "
    "persistence cases and trained predictions from the same consumer."
)
_DUPLICATE_PERSISTENCE_TIMESTAMP_MESSAGE = (
    "Consumer Load persistence-versus-trained OLS MAE comparison requires "
    "unique persistence target timestamps."
)
_DUPLICATE_TRAINED_TIMESTAMP_MESSAGE = (
    "Consumer Load persistence-versus-trained OLS MAE comparison requires "
    "unique trained target timestamps."
)
_OUT_OF_ORDER_PERSISTENCE_MESSAGE = (
    "Consumer Load persistence-versus-trained OLS MAE comparison requires "
    "strictly increasing persistence target timestamps."
)
_OUT_OF_ORDER_TRAINED_MESSAGE = (
    "Consumer Load persistence-versus-trained OLS MAE comparison requires "
    "strictly increasing trained target timestamps."
)
_TIMESTAMP_MISMATCH_MESSAGE = (
    "Consumer Load persistence-versus-trained OLS MAE comparison requires "
    "matching target timestamps at each aligned index."
)
_ACTUAL_MISMATCH_MESSAGE = (
    "Consumer Load persistence-versus-trained OLS MAE comparison requires "
    "matching actual MW values at each aligned index."
)
_RESULT_FIELDS = (
    "case_count",
    "persistence_mae_mw",
    "trained_ols_mae_mw",
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


def _trained_prediction(
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


def _compare(
    persistence_cases: tuple[PreviousDayPersistenceBacktestCase, ...],
    trained_predictions: tuple[ConsumerLoadLag24hLinearRegressionPrediction, ...],
) -> ConsumerLoadPersistenceVsTrainedOLSMAEComparison:
    return compare_consumer_load_persistence_vs_trained_ols_mae(
        persistence_cases=persistence_cases,
        trained_predictions=trained_predictions,
    )


def test_aligned_cohort_reports_exact_case_count_and_both_mae_values() -> None:
    persistence_cases = (
        _persistence_case(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),
        _persistence_case(hour=11, predicted_value_mw=5.0, actual_value_mw=3.0),
        _persistence_case(hour=12, predicted_value_mw=8.0, actual_value_mw=11.0),
    )
    trained_predictions = (
        _trained_prediction(hour=10, predicted_value_mw=3.0, actual_value_mw=2.0),
        _trained_prediction(hour=11, predicted_value_mw=4.0, actual_value_mw=3.0),
        _trained_prediction(hour=12, predicted_value_mw=10.0, actual_value_mw=11.0),
    )
    result = _compare(persistence_cases, trained_predictions)
    expected_persistence = (abs(1.0 - 2.0) + abs(5.0 - 3.0) + abs(8.0 - 11.0)) / 3
    expected_trained = (abs(3.0 - 2.0) + abs(4.0 - 3.0) + abs(10.0 - 11.0)) / 3
    assert result.case_count == 3
    assert result.persistence_mae_mw == expected_persistence
    assert result.persistence_mae_mw == 2.0
    assert result.trained_ols_mae_mw == expected_trained
    assert result.trained_ols_mae_mw == 1.0


def test_trained_ols_can_have_lower_mae_without_winner_field() -> None:
    result = _compare(
        (_persistence_case(hour=10, predicted_value_mw=10.0, actual_value_mw=4.0),),
        (_trained_prediction(hour=10, predicted_value_mw=5.0, actual_value_mw=4.0),),
    )
    assert result.persistence_mae_mw == 6.0
    assert result.trained_ols_mae_mw == 1.0
    assert result.trained_ols_mae_mw < result.persistence_mae_mw
    assert not hasattr(result, "winner")
    assert not hasattr(result, "champion")
    assert not hasattr(result, "selected_model")


def test_persistence_can_have_lower_mae_without_selection_behavior() -> None:
    result = _compare(
        (_persistence_case(hour=10, predicted_value_mw=5.0, actual_value_mw=4.0),),
        (_trained_prediction(hour=10, predicted_value_mw=10.0, actual_value_mw=4.0),),
    )
    assert result.persistence_mae_mw == 1.0
    assert result.trained_ols_mae_mw == 6.0
    assert result.persistence_mae_mw < result.trained_ols_mae_mw
    assert not hasattr(result, "winner")
    assert not hasattr(result, "selected_model")


def test_equal_mae_values_do_not_introduce_a_tie_policy() -> None:
    result = _compare(
        (_persistence_case(hour=10, predicted_value_mw=1.0, actual_value_mw=4.0),),
        (_trained_prediction(hour=10, predicted_value_mw=7.0, actual_value_mw=4.0),),
    )
    assert result.persistence_mae_mw == 3.0
    assert result.trained_ols_mae_mw == 3.0
    assert not hasattr(result, "tie")
    assert not hasattr(result, "winner")


def test_negative_trained_prediction_is_scored_normally() -> None:
    result = _compare(
        (_persistence_case(hour=10, predicted_value_mw=4.0, actual_value_mw=4.0),),
        (_trained_prediction(hour=10, predicted_value_mw=-4.0, actual_value_mw=4.0),),
    )
    assert result.persistence_mae_mw == 0.0
    assert result.trained_ols_mae_mw == 8.0
    assert result.trained_ols_mae_mw == abs(-4.0 - 4.0)
    assert result.trained_ols_mae_mw != abs(0.0 - 4.0)


def test_single_aligned_case_is_valid() -> None:
    result = _compare(
        (_persistence_case(hour=10, predicted_value_mw=4.5, actual_value_mw=7.25),),
        (_trained_prediction(hour=10, predicted_value_mw=6.25, actual_value_mw=7.25),),
    )
    assert result.case_count == 1
    assert result.persistence_mae_mw == 2.75
    assert result.trained_ols_mae_mw == 1.0


def test_result_is_frozen_slotted_with_exactly_three_fields() -> None:
    result = _compare(
        (_persistence_case(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),),
        (_trained_prediction(hour=10, predicted_value_mw=3.0, actual_value_mw=2.0),),
    )
    assert ConsumerLoadPersistenceVsTrainedOLSMAEComparison.__slots__ == _RESULT_FIELDS
    assert result.__slots__ == _RESULT_FIELDS
    with pytest.raises(AttributeError):
        result.case_count = 0  # type: ignore[misc]
    assert not hasattr(result, "__dict__")
    forbidden_attrs = (
        "winner",
        "champion",
        "selected_model",
        "improvement",
        "percentage_improvement",
        "delta",
        "ratio",
        "threshold",
        "rmse",
        "mape",
        "metadata",
        "model_name",
        "consumer_id",
    )
    for name in forbidden_attrs:
        assert not hasattr(result, name)


def test_both_empty_tuples_fail_closed() -> None:
    with pytest.raises(InvalidRequestError, match=_EMPTY_BOTH_MESSAGE) as caught:
        _compare((), ())
    assert caught.value.code == "invalid_request"


def test_empty_persistence_and_nonempty_trained_fail_closed() -> None:
    trained = (_trained_prediction(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),)
    with pytest.raises(InvalidRequestError, match=_EMPTY_PERSISTENCE_MESSAGE) as caught:
        _compare((), trained)
    assert caught.value.code == "invalid_request"


def test_nonempty_persistence_and_empty_trained_fail_closed() -> None:
    persistence = (_persistence_case(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),)
    with pytest.raises(InvalidRequestError, match=_EMPTY_TRAINED_MESSAGE) as caught:
        _compare(persistence, ())
    assert caught.value.code == "invalid_request"


def test_unequal_lengths_fail_closed_without_truncation() -> None:
    persistence_cases = (
        _persistence_case(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),
        _persistence_case(hour=11, predicted_value_mw=3.0, actual_value_mw=4.0),
    )
    trained_predictions = (
        _trained_prediction(hour=10, predicted_value_mw=1.5, actual_value_mw=2.0),
    )
    with pytest.raises(InvalidRequestError, match=_UNEQUAL_LENGTH_MESSAGE) as caught:
        _compare(persistence_cases, trained_predictions)
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
    trained_predictions = (
        _trained_prediction(
            hour=10,
            predicted_value_mw=1.5,
            actual_value_mw=2.0,
            consumer_id="consumer-1",
        ),
        _trained_prediction(
            hour=11,
            predicted_value_mw=3.5,
            actual_value_mw=4.0,
            consumer_id="consumer-1",
        ),
    )
    with pytest.raises(InvalidRequestError, match=_MIXED_PERSISTENCE_CONSUMER_MESSAGE) as caught:
        _compare(persistence_cases, trained_predictions)
    assert caught.value.code == "invalid_request"
    assert "consumer-1" not in caught.value.message
    assert "consumer-2" not in caught.value.message


def test_mixed_trained_consumers_fail_closed_without_raw_ids() -> None:
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
    trained_predictions = (
        _trained_prediction(
            hour=10,
            predicted_value_mw=1.5,
            actual_value_mw=2.0,
            consumer_id="consumer-1",
        ),
        _trained_prediction(
            hour=11,
            predicted_value_mw=3.5,
            actual_value_mw=4.0,
            consumer_id="consumer-2",
        ),
    )
    with pytest.raises(InvalidRequestError, match=_MIXED_TRAINED_CONSUMER_MESSAGE) as caught:
        _compare(persistence_cases, trained_predictions)
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
    trained_predictions = (
        _trained_prediction(
            hour=10,
            predicted_value_mw=1.5,
            actual_value_mw=2.0,
            consumer_id="consumer-2",
        ),
    )
    with pytest.raises(InvalidRequestError, match=_CONSUMER_MISMATCH_MESSAGE) as caught:
        _compare(persistence_cases, trained_predictions)
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
    trained_predictions = (
        _trained_prediction(hour=10, predicted_value_mw=1.5, actual_value_mw=2.0),
        _trained_prediction(hour=11, predicted_value_mw=3.5, actual_value_mw=4.0),
    )
    with pytest.raises(
        InvalidRequestError,
        match=_DUPLICATE_PERSISTENCE_TIMESTAMP_MESSAGE,
    ) as caught:
        _compare(persistence_cases, trained_predictions)
    assert caught.value.code == "invalid_request"


def test_trained_duplicate_timestamp_fails_closed() -> None:
    stamp = utc(hour=10)
    persistence_cases = (
        _persistence_case(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),
        _persistence_case(hour=11, predicted_value_mw=3.0, actual_value_mw=4.0),
    )
    trained_predictions = (
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
    with pytest.raises(
        InvalidRequestError,
        match=_DUPLICATE_TRAINED_TIMESTAMP_MESSAGE,
    ) as caught:
        _compare(persistence_cases, trained_predictions)
    assert caught.value.code == "invalid_request"


def test_persistence_out_of_order_timestamps_fail_closed() -> None:
    persistence_cases = (
        _persistence_case(hour=12, predicted_value_mw=1.0, actual_value_mw=2.0),
        _persistence_case(hour=10, predicted_value_mw=3.0, actual_value_mw=4.0),
    )
    trained_predictions = (
        _trained_prediction(hour=10, predicted_value_mw=1.5, actual_value_mw=2.0),
        _trained_prediction(hour=12, predicted_value_mw=3.5, actual_value_mw=4.0),
    )
    with pytest.raises(InvalidRequestError, match=_OUT_OF_ORDER_PERSISTENCE_MESSAGE) as caught:
        _compare(persistence_cases, trained_predictions)
    assert caught.value.code == "invalid_request"


def test_trained_out_of_order_timestamps_fail_closed() -> None:
    persistence_cases = (
        _persistence_case(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),
        _persistence_case(hour=12, predicted_value_mw=3.0, actual_value_mw=4.0),
    )
    trained_predictions = (
        _trained_prediction(hour=12, predicted_value_mw=1.5, actual_value_mw=2.0),
        _trained_prediction(hour=10, predicted_value_mw=3.5, actual_value_mw=4.0),
    )
    with pytest.raises(InvalidRequestError, match=_OUT_OF_ORDER_TRAINED_MESSAGE) as caught:
        _compare(persistence_cases, trained_predictions)
    assert caught.value.code == "invalid_request"


def test_pairwise_timestamp_mismatch_fails_closed() -> None:
    persistence_cases = (
        _persistence_case(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),
        _persistence_case(hour=12, predicted_value_mw=3.0, actual_value_mw=4.0),
    )
    trained_predictions = (
        _trained_prediction(hour=10, predicted_value_mw=1.5, actual_value_mw=2.0),
        _trained_prediction(hour=13, predicted_value_mw=3.5, actual_value_mw=4.0),
    )
    with pytest.raises(InvalidRequestError, match=_TIMESTAMP_MISMATCH_MESSAGE) as caught:
        _compare(persistence_cases, trained_predictions)
    assert caught.value.code == "invalid_request"


def test_pairwise_actual_mismatch_fails_closed_without_numeric_values() -> None:
    persistence_cases = (_persistence_case(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),)
    trained_predictions = (
        _trained_prediction(hour=10, predicted_value_mw=1.5, actual_value_mw=9.75),
    )
    with pytest.raises(InvalidRequestError, match=_ACTUAL_MISMATCH_MESSAGE) as caught:
        _compare(persistence_cases, trained_predictions)
    assert caught.value.code == "invalid_request"
    assert "2.0" not in caught.value.message
    assert "9.75" not in caught.value.message


def test_input_tuples_are_not_mutated() -> None:
    first_case = _persistence_case(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0)
    second_case = _persistence_case(hour=12, predicted_value_mw=5.0, actual_value_mw=3.0)
    first_prediction = _trained_prediction(hour=10, predicted_value_mw=3.0, actual_value_mw=2.0)
    second_prediction = _trained_prediction(hour=12, predicted_value_mw=4.0, actual_value_mw=3.0)
    persistence_cases = (first_case, second_case)
    trained_predictions = (first_prediction, second_prediction)
    original_case_ids = tuple(id(item) for item in persistence_cases)
    original_prediction_ids = tuple(id(item) for item in trained_predictions)
    _compare(persistence_cases, trained_predictions)
    assert persistence_cases == (first_case, second_case)
    assert trained_predictions == (first_prediction, second_prediction)
    assert tuple(id(item) for item in persistence_cases) == original_case_ids
    assert tuple(id(item) for item in trained_predictions) == original_prediction_ids
    assert first_case.predicted_value_mw == 1.0
    assert first_prediction.predicted_value_mw == 3.0


def test_repeated_equal_input_returns_value_equal_result() -> None:
    persistence_cases = (
        _persistence_case(hour=10, predicted_value_mw=1.0, actual_value_mw=2.0),
        _persistence_case(hour=12, predicted_value_mw=5.0, actual_value_mw=3.0),
    )
    trained_predictions = (
        _trained_prediction(hour=10, predicted_value_mw=3.0, actual_value_mw=2.0),
        _trained_prediction(hour=12, predicted_value_mw=4.0, actual_value_mw=3.0),
    )
    first = _compare(persistence_cases, trained_predictions)
    second = _compare(persistence_cases, trained_predictions)
    assert first == second
    assert first is not second


def test_return_contract_uses_int_count_and_finite_float_mae() -> None:
    persistence_cases = (_persistence_case(hour=10, predicted_value_mw=4.5, actual_value_mw=7.25),)
    trained_predictions = (
        _trained_prediction(hour=10, predicted_value_mw=6.25, actual_value_mw=7.25),
    )
    result = _compare(persistence_cases, trained_predictions)
    assert isinstance(result, ConsumerLoadPersistenceVsTrainedOLSMAEComparison)
    assert isinstance(persistence_cases, tuple)
    assert isinstance(trained_predictions, tuple)
    assert type(result.case_count) is int
    assert type(result.persistence_mae_mw) is float
    assert type(result.trained_ols_mae_mw) is float
    assert isfinite(result.persistence_mae_mw)
    assert isfinite(result.trained_ols_mae_mw)
    assert result.case_count == 1
    assert result.persistence_mae_mw == 2.75
    assert result.trained_ols_mae_mw == 1.0


def test_mae_values_correspond_to_each_published_artifact() -> None:
    persistence_cases = (
        _persistence_case(hour=10, predicted_value_mw=0.0, actual_value_mw=10.0),
        _persistence_case(hour=11, predicted_value_mw=0.0, actual_value_mw=10.0),
    )
    trained_predictions = (
        _trained_prediction(hour=10, predicted_value_mw=9.0, actual_value_mw=10.0),
        _trained_prediction(hour=11, predicted_value_mw=9.0, actual_value_mw=10.0),
    )
    result = _compare(persistence_cases, trained_predictions)
    assert result.persistence_mae_mw == 10.0
    assert result.trained_ols_mae_mw == 1.0
    assert result.persistence_mae_mw != result.trained_ols_mae_mw
