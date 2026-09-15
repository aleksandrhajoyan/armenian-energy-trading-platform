"""Lag-24h ordinary least-squares Consumer Load parameter fit."""

from __future__ import annotations

import pytest

from energy_trading.application.errors import InvalidRequestError
from energy_trading.ml.consumer_load.lag_24h_features import ConsumerLoadLag24hFeatureRow
from energy_trading.ml.consumer_load.lag_24h_linear_regression import (
    ConsumerLoadLag24hLinearRegressionFit,
    fit_consumer_load_lag_24h_linear_regression,
)
from tests.unit.domain._factories import utc

_TOO_FEW_ROWS_MESSAGE = (
    "Consumer Load lag-24h linear regression requires at least two training rows."
)
_MIXED_CONSUMER_MESSAGE = (
    "Consumer Load lag-24h linear regression requires rows from exactly one consumer."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "Consumer Load lag-24h linear regression requires unique target timestamps."
)
_OUT_OF_ORDER_MESSAGE = (
    "Consumer Load lag-24h linear regression requires strictly increasing target timestamps."
)
_ZERO_VARIANCE_MESSAGE = (
    "Consumer Load lag-24h linear regression requires non-zero variance in lag_24h_mw."
)
_FIT_FIELDS = (
    "slope",
    "intercept_mw",
)


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


def test_empty_tuple_fails_closed() -> None:
    with pytest.raises(InvalidRequestError, match=_TOO_FEW_ROWS_MESSAGE) as caught:
        fit_consumer_load_lag_24h_linear_regression(training_rows=())
    assert caught.value.code == "invalid_request"


def test_one_row_fails_closed() -> None:
    rows = (_row(hour=10, lag_mw=1.0, value_mw=3.0),)
    with pytest.raises(InvalidRequestError, match=_TOO_FEW_ROWS_MESSAGE) as caught:
        fit_consumer_load_lag_24h_linear_regression(training_rows=rows)
    assert caught.value.code == "invalid_request"


def test_exact_two_point_line_recovers_slope_and_intercept() -> None:
    rows = (
        _row(hour=10, lag_mw=1.0, value_mw=3.0),
        _row(hour=12, lag_mw=2.0, value_mw=5.0),
    )
    result = fit_consumer_load_lag_24h_linear_regression(training_rows=rows)
    assert result.slope == 2.0
    assert result.intercept_mw == 1.0


def test_several_points_on_an_exact_line_recover_expected_fit() -> None:
    rows = (
        _row(hour=8, lag_mw=1.0, value_mw=3.0),
        _row(hour=9, lag_mw=2.0, value_mw=5.0),
        _row(hour=10, lag_mw=3.0, value_mw=7.0),
        _row(hour=11, lag_mw=4.0, value_mw=9.0),
    )
    result = fit_consumer_load_lag_24h_linear_regression(training_rows=rows)
    assert result.slope == 2.0
    assert result.intercept_mw == 1.0


def test_non_perfect_data_produces_exact_ols_result() -> None:
    rows = (
        _row(hour=8, lag_mw=1.0, value_mw=1.0),
        _row(hour=9, lag_mw=2.0, value_mw=2.0),
        _row(hour=10, lag_mw=3.0, value_mw=2.0),
    )
    result = fit_consumer_load_lag_24h_linear_regression(training_rows=rows)
    assert result.slope == pytest.approx(0.5)
    assert result.intercept_mw == pytest.approx(2.0 / 3.0)


def test_positive_intercept_is_preserved() -> None:
    rows = (
        _row(hour=10, lag_mw=1.0, value_mw=5.0),
        _row(hour=12, lag_mw=2.0, value_mw=7.0),
    )
    result = fit_consumer_load_lag_24h_linear_regression(training_rows=rows)
    assert result.slope == 2.0
    assert result.intercept_mw == 3.0
    assert result.intercept_mw > 0.0


def test_negative_intercept_is_allowed_and_preserved() -> None:
    rows = (
        _row(hour=10, lag_mw=2.0, value_mw=1.0),
        _row(hour=12, lag_mw=4.0, value_mw=5.0),
    )
    result = fit_consumer_load_lag_24h_linear_regression(training_rows=rows)
    assert result.slope == 2.0
    assert result.intercept_mw == -3.0
    assert result.intercept_mw < 0.0


def test_zero_slope_is_valid_when_targets_are_constant_and_features_vary() -> None:
    rows = (
        _row(hour=8, lag_mw=1.0, value_mw=5.0),
        _row(hour=9, lag_mw=2.0, value_mw=5.0),
        _row(hour=10, lag_mw=3.0, value_mw=5.0),
    )
    result = fit_consumer_load_lag_24h_linear_regression(training_rows=rows)
    assert result.slope == 0.0
    assert result.intercept_mw == 5.0


def test_identical_feature_values_fail_as_degenerate() -> None:
    rows = (
        _row(hour=10, lag_mw=4.0, value_mw=1.0),
        _row(hour=12, lag_mw=4.0, value_mw=9.0),
    )
    with pytest.raises(InvalidRequestError, match=_ZERO_VARIANCE_MESSAGE) as caught:
        fit_consumer_load_lag_24h_linear_regression(training_rows=rows)
    assert caught.value.code == "invalid_request"


def test_partially_repeated_feature_values_are_valid_when_variance_is_nonzero() -> None:
    rows = (
        _row(hour=8, lag_mw=1.0, value_mw=2.0),
        _row(hour=9, lag_mw=1.0, value_mw=3.0),
        _row(hour=10, lag_mw=2.0, value_mw=5.0),
    )
    result = fit_consumer_load_lag_24h_linear_regression(training_rows=rows)
    assert result.slope == pytest.approx(2.5)
    assert result.intercept_mw == pytest.approx(0.0)


def test_mixed_consumers_fail_closed_without_raw_ids() -> None:
    rows = (
        _row(hour=10, lag_mw=1.0, value_mw=3.0, consumer_id="consumer-1"),
        _row(hour=12, lag_mw=2.0, value_mw=5.0, consumer_id="consumer-2"),
    )
    with pytest.raises(InvalidRequestError, match=_MIXED_CONSUMER_MESSAGE) as caught:
        fit_consumer_load_lag_24h_linear_regression(training_rows=rows)
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
        fit_consumer_load_lag_24h_linear_regression(training_rows=rows)
    assert caught.value.code == "invalid_request"


def test_out_of_order_timestamps_fail_closed() -> None:
    rows = (
        _row(hour=14, lag_mw=2.0, value_mw=5.0),
        _row(hour=10, lag_mw=1.0, value_mw=3.0),
    )
    with pytest.raises(InvalidRequestError, match=_OUT_OF_ORDER_MESSAGE) as caught:
        fit_consumer_load_lag_24h_linear_regression(training_rows=rows)
    assert caught.value.code == "invalid_request"


def test_input_order_is_not_silently_sorted() -> None:
    rows = (
        _row(hour=14, lag_mw=2.0, value_mw=5.0),
        _row(hour=10, lag_mw=1.0, value_mw=3.0),
    )
    with pytest.raises(InvalidRequestError, match=_OUT_OF_ORDER_MESSAGE):
        fit_consumer_load_lag_24h_linear_regression(training_rows=rows)


def test_input_tuple_and_rows_are_not_mutated() -> None:
    first = _row(hour=10, lag_mw=1.0, value_mw=3.0)
    second = _row(hour=12, lag_mw=2.0, value_mw=5.0)
    rows = (first, second)
    original_ids = tuple(id(row) for row in rows)
    result = fit_consumer_load_lag_24h_linear_regression(training_rows=rows)
    assert rows == (first, second)
    assert tuple(id(row) for row in rows) == original_ids
    assert rows[0] is first
    assert rows[1] is second
    assert first.lag_24h_mw == 1.0
    assert first.target_value_mw == 3.0
    assert second.lag_24h_mw == 2.0
    assert second.target_value_mw == 5.0
    assert result.slope == 2.0


def test_repeated_equal_input_yields_value_equal_fit() -> None:
    rows = (
        _row(hour=10, lag_mw=1.0, value_mw=3.0),
        _row(hour=12, lag_mw=2.0, value_mw=5.0),
    )
    first = fit_consumer_load_lag_24h_linear_regression(training_rows=rows)
    second = fit_consumer_load_lag_24h_linear_regression(training_rows=rows)
    assert first == second
    assert first is not second


def test_result_is_frozen_slotted_with_exactly_two_fields() -> None:
    result = fit_consumer_load_lag_24h_linear_regression(
        training_rows=(
            _row(hour=10, lag_mw=1.0, value_mw=3.0),
            _row(hour=12, lag_mw=2.0, value_mw=5.0),
        ),
    )
    assert ConsumerLoadLag24hLinearRegressionFit.__slots__ == _FIT_FIELDS
    with pytest.raises(AttributeError):
        result.slope = 0.0  # type: ignore[misc]
    assert not hasattr(result, "__dict__")


def test_result_contract_has_exactly_slope_and_intercept() -> None:
    result = fit_consumer_load_lag_24h_linear_regression(
        training_rows=(
            _row(hour=10, lag_mw=1.0, value_mw=3.0),
            _row(hour=12, lag_mw=2.0, value_mw=5.0),
        ),
    )
    assert result.__slots__ == _FIT_FIELDS
    forbidden_attrs = (
        "consumer_id",
        "training_row_count",
        "mae",
        "rmse",
        "r2",
        "residuals",
        "metadata",
        "version",
        "feature_names",
        "workflow_id",
        "predictions",
    )
    for name in forbidden_attrs:
        assert not hasattr(result, name)


def test_fit_does_not_convert_mw_to_mwh() -> None:
    rows = (
        _row(hour=10, lag_mw=1.25, value_mw=3.5),
        _row(hour=12, lag_mw=2.5, value_mw=6.0),
    )
    result = fit_consumer_load_lag_24h_linear_regression(training_rows=rows)
    assert result.slope == 2.0
    assert result.intercept_mw == 1.0


def test_fit_does_not_round_parameters() -> None:
    rows = (
        _row(hour=8, lag_mw=0.5, value_mw=1.25),
        _row(hour=9, lag_mw=1.0, value_mw=2.0),
        _row(hour=10, lag_mw=1.5, value_mw=2.75),
    )
    result = fit_consumer_load_lag_24h_linear_regression(training_rows=rows)
    assert result.slope == 1.5
    assert result.intercept_mw == 0.5


def test_module_has_no_prediction_or_metric_behavior() -> None:
    from energy_trading.ml.consumer_load import lag_24h_linear_regression as fit_module

    assert not hasattr(fit_module, "predict")
    result = fit_consumer_load_lag_24h_linear_regression(
        training_rows=(
            _row(hour=10, lag_mw=1.0, value_mw=3.0),
            _row(hour=12, lag_mw=2.0, value_mw=5.0),
        ),
    )
    assert not hasattr(result, "predict")
    assert not hasattr(result, "mae_mw")
    assert not hasattr(result, "rmse")
    assert not hasattr(result, "r2")


def test_chronology_and_mw_values_are_only_read() -> None:
    first = _row(hour=10, lag_mw=1.0, value_mw=3.0)
    second = _row(hour=12, lag_mw=2.0, value_mw=5.0)
    original_first = (
        first.consumer_id,
        first.target_timestamp,
        first.lag_24h_mw,
        first.target_value_mw,
    )
    original_second = (
        second.consumer_id,
        second.target_timestamp,
        second.lag_24h_mw,
        second.target_value_mw,
    )
    fit_consumer_load_lag_24h_linear_regression(training_rows=(first, second))
    assert (
        first.consumer_id,
        first.target_timestamp,
        first.lag_24h_mw,
        first.target_value_mw,
    ) == original_first
    assert (
        second.consumer_id,
        second.target_timestamp,
        second.lag_24h_mw,
        second.target_value_mw,
    ) == original_second
