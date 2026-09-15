"""Lag-24h plus lag-168h ordinary least-squares Consumer Load parameter fit."""

from __future__ import annotations

from math import isfinite

import pytest

from energy_trading.application.errors import InvalidRequestError
from energy_trading.ml.consumer_load.lag_24h_168h_features import (
    ConsumerLoadLag24h168hFeatureRow,
)
from energy_trading.ml.consumer_load.lag_24h_168h_linear_regression import (
    ConsumerLoadLag24h168hLinearRegressionFit,
    fit_consumer_load_lag_24h_168h_linear_regression,
)
from tests.unit.domain._factories import utc

_TOO_FEW_ROWS_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression requires "
    "at least three training rows."
)
_MIXED_CONSUMER_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression requires "
    "rows from exactly one consumer."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression requires unique target timestamps."
)
_OUT_OF_ORDER_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression requires "
    "strictly increasing target timestamps."
)
_SINGULAR_DESIGN_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression requires "
    "a full-rank two-feature design."
)
_NON_FINITE_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression requires "
    "finite fitted coefficients and intercept."
)
_FIT_FIELDS = (
    "lag_24h_coefficient",
    "lag_168h_coefficient",
    "intercept_mw",
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


def _known_fit_rows(
    *,
    lag_24h_coefficient: float,
    lag_168h_coefficient: float,
    intercept_mw: float,
    points: tuple[tuple[float, float], ...],
) -> tuple[ConsumerLoadLag24h168hFeatureRow, ...]:
    return tuple(
        _row(
            hour=8 + index,
            lag_24h_mw=lag_24h_mw,
            lag_168h_mw=lag_168h_mw,
            target_value_mw=(
                intercept_mw + lag_24h_coefficient * lag_24h_mw + lag_168h_coefficient * lag_168h_mw
            ),
        )
        for index, (lag_24h_mw, lag_168h_mw) in enumerate(points)
    )


def test_exact_known_two_feature_fit_recovers_coefficients_and_intercept() -> None:
    rows = _known_fit_rows(
        lag_24h_coefficient=3.0,
        lag_168h_coefficient=5.0,
        intercept_mw=2.0,
        points=((1.0, 1.0), (2.0, 1.0), (1.0, 2.0)),
    )
    result = fit_consumer_load_lag_24h_168h_linear_regression(training_rows=rows)
    assert result.lag_24h_coefficient == pytest.approx(3.0)
    assert result.lag_168h_coefficient == pytest.approx(5.0)
    assert result.intercept_mw == pytest.approx(2.0)


def test_second_exact_known_fit_recovers_different_coefficients() -> None:
    rows = _known_fit_rows(
        lag_24h_coefficient=4.0,
        lag_168h_coefficient=7.0,
        intercept_mw=1.0,
        points=((1.0, 2.0), (2.0, 2.0), (1.0, 3.0)),
    )
    result = fit_consumer_load_lag_24h_168h_linear_regression(training_rows=rows)
    assert result.lag_24h_coefficient == pytest.approx(4.0)
    assert result.lag_168h_coefficient == pytest.approx(7.0)
    assert result.intercept_mw == pytest.approx(1.0)


def test_negative_lag_24h_coefficient_is_preserved() -> None:
    rows = _known_fit_rows(
        lag_24h_coefficient=-2.0,
        lag_168h_coefficient=3.0,
        intercept_mw=10.0,
        points=((1.0, 1.0), (2.0, 1.0), (1.0, 2.0)),
    )
    result = fit_consumer_load_lag_24h_168h_linear_regression(training_rows=rows)
    assert result.lag_24h_coefficient == pytest.approx(-2.0)
    assert result.lag_168h_coefficient == pytest.approx(3.0)
    assert result.intercept_mw == pytest.approx(10.0)
    assert result.lag_24h_coefficient < 0.0


def test_negative_lag_168h_coefficient_is_preserved() -> None:
    rows = _known_fit_rows(
        lag_24h_coefficient=2.0,
        lag_168h_coefficient=-3.0,
        intercept_mw=10.0,
        points=((1.0, 1.0), (2.0, 1.0), (1.0, 2.0)),
    )
    result = fit_consumer_load_lag_24h_168h_linear_regression(training_rows=rows)
    assert result.lag_24h_coefficient == pytest.approx(2.0)
    assert result.lag_168h_coefficient == pytest.approx(-3.0)
    assert result.intercept_mw == pytest.approx(10.0)
    assert result.lag_168h_coefficient < 0.0


def test_negative_intercept_is_preserved() -> None:
    rows = _known_fit_rows(
        lag_24h_coefficient=2.0,
        lag_168h_coefficient=3.0,
        intercept_mw=-4.0,
        points=((1.0, 1.0), (2.0, 1.0), (1.0, 2.0)),
    )
    result = fit_consumer_load_lag_24h_168h_linear_regression(training_rows=rows)
    assert result.lag_24h_coefficient == pytest.approx(2.0)
    assert result.lag_168h_coefficient == pytest.approx(3.0)
    assert result.intercept_mw == pytest.approx(-4.0)
    assert result.intercept_mw < 0.0


def test_zero_lag_24h_coefficient_is_valid_when_design_is_full_rank() -> None:
    rows = _known_fit_rows(
        lag_24h_coefficient=0.0,
        lag_168h_coefficient=2.0,
        intercept_mw=5.0,
        points=((1.0, 1.0), (2.0, 1.0), (1.0, 2.0)),
    )
    result = fit_consumer_load_lag_24h_168h_linear_regression(training_rows=rows)
    assert result.lag_24h_coefficient == pytest.approx(0.0)
    assert result.lag_168h_coefficient == pytest.approx(2.0)
    assert result.intercept_mw == pytest.approx(5.0)


def test_zero_lag_168h_coefficient_is_valid_when_design_is_full_rank() -> None:
    rows = _known_fit_rows(
        lag_24h_coefficient=2.0,
        lag_168h_coefficient=0.0,
        intercept_mw=5.0,
        points=((1.0, 1.0), (2.0, 1.0), (1.0, 2.0)),
    )
    result = fit_consumer_load_lag_24h_168h_linear_regression(training_rows=rows)
    assert result.lag_24h_coefficient == pytest.approx(2.0)
    assert result.lag_168h_coefficient == pytest.approx(0.0)
    assert result.intercept_mw == pytest.approx(5.0)


def test_minimum_valid_three_row_full_rank_fit() -> None:
    rows = _known_fit_rows(
        lag_24h_coefficient=1.5,
        lag_168h_coefficient=0.5,
        intercept_mw=0.25,
        points=((1.0, 2.0), (3.0, 2.0), (1.0, 4.0)),
    )
    assert len(rows) == 3
    result = fit_consumer_load_lag_24h_168h_linear_regression(training_rows=rows)
    assert result.lag_24h_coefficient == pytest.approx(1.5)
    assert result.lag_168h_coefficient == pytest.approx(0.5)
    assert result.intercept_mw == pytest.approx(0.25)


def test_result_is_frozen_slotted_with_exactly_three_fields() -> None:
    result = fit_consumer_load_lag_24h_168h_linear_regression(
        training_rows=_known_fit_rows(
            lag_24h_coefficient=3.0,
            lag_168h_coefficient=5.0,
            intercept_mw=2.0,
            points=((1.0, 1.0), (2.0, 1.0), (1.0, 2.0)),
        ),
    )
    assert ConsumerLoadLag24h168hLinearRegressionFit.__slots__ == _FIT_FIELDS
    with pytest.raises(AttributeError):
        result.lag_24h_coefficient = 0.0  # type: ignore[misc]
    assert not hasattr(result, "__dict__")
    forbidden_attrs = (
        "slope",
        "consumer_id",
        "training_row_count",
        "mae",
        "rmse",
        "r2",
        "residuals",
        "metadata",
        "feature_names",
        "covariance",
        "determinant",
        "winner",
        "champion",
        "workflow_id",
        "predictions",
    )
    for name in forbidden_attrs:
        assert not hasattr(result, name)


def test_empty_training_rows_fail_closed() -> None:
    with pytest.raises(InvalidRequestError, match=_TOO_FEW_ROWS_MESSAGE) as caught:
        fit_consumer_load_lag_24h_168h_linear_regression(training_rows=())
    assert caught.value.code == "invalid_request"


def test_one_training_row_fails_closed() -> None:
    rows = (_row(hour=8, lag_24h_mw=1.0, lag_168h_mw=2.0, target_value_mw=3.0),)
    with pytest.raises(InvalidRequestError, match=_TOO_FEW_ROWS_MESSAGE) as caught:
        fit_consumer_load_lag_24h_168h_linear_regression(training_rows=rows)
    assert caught.value.code == "invalid_request"


def test_two_training_rows_fail_closed() -> None:
    rows = (
        _row(hour=8, lag_24h_mw=1.0, lag_168h_mw=2.0, target_value_mw=3.0),
        _row(hour=9, lag_24h_mw=2.0, lag_168h_mw=1.0, target_value_mw=5.0),
    )
    with pytest.raises(InvalidRequestError, match=_TOO_FEW_ROWS_MESSAGE) as caught:
        fit_consumer_load_lag_24h_168h_linear_regression(training_rows=rows)
    assert caught.value.code == "invalid_request"


def test_mixed_consumers_fail_closed_without_raw_ids() -> None:
    rows = (
        _row(hour=8, lag_24h_mw=1.0, lag_168h_mw=1.0, target_value_mw=10.0),
        _row(
            hour=9,
            lag_24h_mw=2.0,
            lag_168h_mw=1.0,
            target_value_mw=13.0,
            consumer_id="consumer-2",
        ),
        _row(hour=10, lag_24h_mw=1.0, lag_168h_mw=2.0, target_value_mw=15.0),
    )
    with pytest.raises(InvalidRequestError, match=_MIXED_CONSUMER_MESSAGE) as caught:
        fit_consumer_load_lag_24h_168h_linear_regression(training_rows=rows)
    assert caught.value.code == "invalid_request"
    assert "consumer-1" not in caught.value.message
    assert "consumer-2" not in caught.value.message


def test_duplicate_timestamps_fail_closed() -> None:
    stamp = utc(day=15, hour=9)
    rows = (
        _row(hour=8, lag_24h_mw=1.0, lag_168h_mw=1.0, target_value_mw=10.0),
        ConsumerLoadLag24h168hFeatureRow(
            consumer_id="consumer-1",
            target_timestamp=stamp,
            lag_24h_mw=2.0,
            lag_168h_mw=1.0,
            target_value_mw=13.0,
        ),
        ConsumerLoadLag24h168hFeatureRow(
            consumer_id="consumer-1",
            target_timestamp=stamp,
            lag_24h_mw=1.0,
            lag_168h_mw=2.0,
            target_value_mw=15.0,
        ),
    )
    with pytest.raises(InvalidRequestError, match=_DUPLICATE_TIMESTAMP_MESSAGE) as caught:
        fit_consumer_load_lag_24h_168h_linear_regression(training_rows=rows)
    assert caught.value.code == "invalid_request"


def test_out_of_order_timestamps_fail_closed() -> None:
    rows = (
        _row(hour=10, lag_24h_mw=1.0, lag_168h_mw=2.0, target_value_mw=15.0),
        _row(hour=9, lag_24h_mw=2.0, lag_168h_mw=1.0, target_value_mw=13.0),
        _row(hour=8, lag_24h_mw=1.0, lag_168h_mw=1.0, target_value_mw=10.0),
    )
    with pytest.raises(InvalidRequestError, match=_OUT_OF_ORDER_MESSAGE) as caught:
        fit_consumer_load_lag_24h_168h_linear_regression(training_rows=rows)
    assert caught.value.code == "invalid_request"


def test_zero_variance_in_lag_24h_fails_closed() -> None:
    rows = (
        _row(hour=8, lag_24h_mw=4.0, lag_168h_mw=1.0, target_value_mw=3.0),
        _row(hour=9, lag_24h_mw=4.0, lag_168h_mw=2.0, target_value_mw=5.0),
        _row(hour=10, lag_24h_mw=4.0, lag_168h_mw=3.0, target_value_mw=7.0),
    )
    with pytest.raises(InvalidRequestError, match=_SINGULAR_DESIGN_MESSAGE) as caught:
        fit_consumer_load_lag_24h_168h_linear_regression(training_rows=rows)
    assert caught.value.code == "invalid_request"


def test_zero_variance_in_lag_168h_fails_closed() -> None:
    rows = (
        _row(hour=8, lag_24h_mw=1.0, lag_168h_mw=4.0, target_value_mw=3.0),
        _row(hour=9, lag_24h_mw=2.0, lag_168h_mw=4.0, target_value_mw=5.0),
        _row(hour=10, lag_24h_mw=3.0, lag_168h_mw=4.0, target_value_mw=7.0),
    )
    with pytest.raises(InvalidRequestError, match=_SINGULAR_DESIGN_MESSAGE) as caught:
        fit_consumer_load_lag_24h_168h_linear_regression(training_rows=rows)
    assert caught.value.code == "invalid_request"


def test_perfect_collinearity_fails_closed() -> None:
    rows = (
        _row(hour=8, lag_24h_mw=1.0, lag_168h_mw=3.0, target_value_mw=4.0),
        _row(hour=9, lag_24h_mw=2.0, lag_168h_mw=5.0, target_value_mw=8.0),
        _row(hour=10, lag_24h_mw=3.0, lag_168h_mw=7.0, target_value_mw=12.0),
    )
    with pytest.raises(InvalidRequestError, match=_SINGULAR_DESIGN_MESSAGE) as caught:
        fit_consumer_load_lag_24h_168h_linear_regression(training_rows=rows)
    assert caught.value.code == "invalid_request"


def test_singular_design_is_not_reduced_to_one_feature_regression() -> None:
    rows = (
        _row(hour=8, lag_24h_mw=1.0, lag_168h_mw=4.0, target_value_mw=3.0),
        _row(hour=9, lag_24h_mw=2.0, lag_168h_mw=4.0, target_value_mw=5.0),
        _row(hour=10, lag_24h_mw=3.0, lag_168h_mw=4.0, target_value_mw=7.0),
    )
    with pytest.raises(InvalidRequestError, match=_SINGULAR_DESIGN_MESSAGE):
        fit_consumer_load_lag_24h_168h_linear_regression(training_rows=rows)


def test_input_tuple_and_row_objects_are_not_mutated() -> None:
    first = _row(hour=8, lag_24h_mw=1.0, lag_168h_mw=1.0, target_value_mw=10.0)
    second = _row(hour=9, lag_24h_mw=2.0, lag_168h_mw=1.0, target_value_mw=13.0)
    third = _row(hour=10, lag_24h_mw=1.0, lag_168h_mw=2.0, target_value_mw=15.0)
    rows = (first, second, third)
    original_ids = tuple(id(row) for row in rows)
    result = fit_consumer_load_lag_24h_168h_linear_regression(training_rows=rows)
    assert rows == (first, second, third)
    assert tuple(id(row) for row in rows) == original_ids
    assert rows[0] is first
    assert rows[1] is second
    assert rows[2] is third
    assert first.lag_24h_mw == 1.0
    assert first.lag_168h_mw == 1.0
    assert first.target_value_mw == 10.0
    assert result.lag_24h_coefficient == pytest.approx(3.0)


def test_repeated_equivalent_input_returns_value_equivalent_fit() -> None:
    rows = _known_fit_rows(
        lag_24h_coefficient=3.0,
        lag_168h_coefficient=5.0,
        intercept_mw=2.0,
        points=((1.0, 1.0), (2.0, 1.0), (1.0, 2.0)),
    )
    first = fit_consumer_load_lag_24h_168h_linear_regression(training_rows=rows)
    second = fit_consumer_load_lag_24h_168h_linear_regression(training_rows=rows)
    assert first == second
    assert first is not second


def test_return_fields_are_finite_floats() -> None:
    result = fit_consumer_load_lag_24h_168h_linear_regression(
        training_rows=_known_fit_rows(
            lag_24h_coefficient=3.0,
            lag_168h_coefficient=5.0,
            intercept_mw=2.0,
            points=((1.0, 1.0), (2.0, 1.0), (1.0, 2.0)),
        ),
    )
    assert type(result.lag_24h_coefficient) is float
    assert type(result.lag_168h_coefficient) is float
    assert type(result.intercept_mw) is float
    assert isfinite(result.lag_24h_coefficient)
    assert isfinite(result.lag_168h_coefficient)
    assert isfinite(result.intercept_mw)


def test_signed_coefficients_and_intercept_are_not_clamped() -> None:
    rows = _known_fit_rows(
        lag_24h_coefficient=-1.5,
        lag_168h_coefficient=-2.25,
        intercept_mw=-0.5,
        points=((1.0, 1.0), (2.0, 1.0), (1.0, 2.0)),
    )
    result = fit_consumer_load_lag_24h_168h_linear_regression(training_rows=rows)
    assert result.lag_24h_coefficient == pytest.approx(-1.5)
    assert result.lag_168h_coefficient == pytest.approx(-2.25)
    assert result.intercept_mw == pytest.approx(-0.5)
    assert result.lag_24h_coefficient < 0.0
    assert result.lag_168h_coefficient < 0.0
    assert result.intercept_mw < 0.0


def test_feature_roles_are_not_swapped() -> None:
    rows = _known_fit_rows(
        lag_24h_coefficient=3.0,
        lag_168h_coefficient=5.0,
        intercept_mw=2.0,
        points=((1.0, 1.0), (2.0, 1.0), (1.0, 2.0), (3.0, 4.0)),
    )
    result = fit_consumer_load_lag_24h_168h_linear_regression(training_rows=rows)
    assert result.lag_24h_coefficient == pytest.approx(3.0)
    assert result.lag_168h_coefficient == pytest.approx(5.0)
    assert result.lag_24h_coefficient != result.lag_168h_coefficient
    assert result.intercept_mw == pytest.approx(2.0)


def test_finite_large_values_fail_closed_without_raw_arithmetic_exception() -> None:
    large_finite = 1.0e200
    assert isfinite(large_finite)
    rows = (
        _row(hour=8, lag_24h_mw=large_finite, lag_168h_mw=1.0, target_value_mw=1.0),
        _row(hour=9, lag_24h_mw=1.0, lag_168h_mw=2.0, target_value_mw=2.0),
        _row(hour=10, lag_24h_mw=2.0, lag_168h_mw=3.0, target_value_mw=large_finite),
    )
    with pytest.raises(InvalidRequestError, match=_NON_FINITE_MESSAGE) as caught:
        fit_consumer_load_lag_24h_168h_linear_regression(training_rows=rows)
    assert caught.value.code == "invalid_request"
    assert isfinite(rows[0].lag_24h_mw)
    assert isfinite(rows[2].target_value_mw)
