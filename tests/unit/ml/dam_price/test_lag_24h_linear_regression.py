"""Lag-24h ordinary least-squares DAM Price parameter fit."""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from energy_trading.application.errors import InvalidRequestError
from energy_trading.ml.dam_price.lag_24h_features import DAMPriceLag24hFeatureRow
from energy_trading.ml.dam_price.lag_24h_linear_regression import (
    DAMPriceLag24hLinearRegressionFit,
    fit_dam_price_lag_24h_linear_regression,
)

_TOO_FEW_ROWS_MESSAGE = "DAM Price lag-24h linear regression requires at least two training rows."
_NON_FINITE_FIT_MESSAGE = (
    "DAM Price lag-24h linear regression requires finite fitted slope and intercept."
)
_MIXED_MARKET_MESSAGE = "DAM Price lag-24h linear regression requires rows from exactly one market."
_MIXED_CURRENCY_MESSAGE = (
    "DAM Price lag-24h linear regression requires rows in exactly one currency."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "DAM Price lag-24h linear regression requires unique target timestamps."
)
_OUT_OF_ORDER_MESSAGE = (
    "DAM Price lag-24h linear regression requires strictly increasing target timestamps."
)
_ZERO_VARIANCE_MESSAGE = (
    "DAM Price lag-24h linear regression requires non-zero variance in lag_24h_amount_per_mwh."
)
_NON_FINITE_INPUT_MESSAGE = (
    "DAM Price lag-24h linear regression requires finite feature and target values."
)


def _ts(day: int, hour: int = 16) -> datetime:
    return datetime(2026, 10, day, hour, 0, 0, tzinfo=UTC)


def _row(
    *,
    day: int,
    lag: str = "1",
    target: str = "1",
    market_id: str = "market-1",
    currency: str = "AMD",
) -> DAMPriceLag24hFeatureRow:
    return DAMPriceLag24hFeatureRow(
        market_id=market_id,
        currency=currency,
        target_timestamp=_ts(day),
        lag_24h_amount_per_mwh=Decimal(lag),
        target_amount_per_mwh=Decimal(target),
    )


def _fit(
    rows: tuple[DAMPriceLag24hFeatureRow, ...],
) -> DAMPriceLag24hLinearRegressionFit:
    return fit_dam_price_lag_24h_linear_regression(training_rows=rows)


def test_empty_input_fails_closed() -> None:
    with pytest.raises(InvalidRequestError) as captured:
        _fit(())
    assert captured.value.message == _TOO_FEW_ROWS_MESSAGE


def test_one_row_fails_closed() -> None:
    with pytest.raises(InvalidRequestError) as captured:
        _fit((_row(day=1, lag="2", target="3"),))
    assert captured.value.message == _TOO_FEW_ROWS_MESSAGE


def test_exact_two_point_line_recovers_parameters() -> None:
    fit = _fit((_row(day=1, lag="1", target="3"), _row(day=2, lag="2", target="5")))
    assert fit.slope == Decimal("2")
    assert fit.intercept_amount_per_mwh == Decimal("1")
    assert isinstance(fit.slope, Decimal)
    assert isinstance(fit.intercept_amount_per_mwh, Decimal)


def test_exact_multi_point_line_recovers_parameters() -> None:
    rows = (
        _row(day=1, lag="1", target="3"),
        _row(day=2, lag="2", target="5"),
        _row(day=3, lag="3", target="7"),
    )
    fit = _fit(rows)
    assert fit.slope == Decimal("2")
    assert fit.intercept_amount_per_mwh == Decimal("1")


def test_non_perfect_data_matches_manual_decimal_ols() -> None:
    # x = 5, 9; y = 1, 3  ->  x_mean = 7, y_mean = 2
    # numerator = (-2)(-1) + (2)(1) = 4 ; denominator = 4 + 4 = 8
    # slope = 0.5 ; intercept = 2 - 0.5 * 7 = -1.5
    fit = _fit((_row(day=1, lag="5", target="1"), _row(day=2, lag="9", target="3")))
    assert fit.slope == Decimal("4") / Decimal("8")
    assert fit.slope == Decimal("0.5")
    assert fit.intercept_amount_per_mwh == Decimal("-1.5")


def test_positive_intercept_is_preserved() -> None:
    fit = _fit((_row(day=1, lag="10", target="25"), _row(day=2, lag="20", target="45")))
    assert fit.slope == Decimal("2")
    assert fit.intercept_amount_per_mwh == Decimal("5")
    assert fit.intercept_amount_per_mwh > 0


def test_negative_intercept_is_preserved() -> None:
    fit = _fit((_row(day=1, lag="0", target="-4"), _row(day=2, lag="2", target="0")))
    assert fit.slope == Decimal("2")
    assert fit.intercept_amount_per_mwh == Decimal("-4")
    assert fit.intercept_amount_per_mwh < 0


def test_zero_intercept_is_accepted() -> None:
    fit = _fit((_row(day=1, lag="1", target="3"), _row(day=2, lag="2", target="6")))
    assert fit.slope == Decimal("3")
    assert fit.intercept_amount_per_mwh == Decimal("0")


def test_positive_slope_is_preserved() -> None:
    fit = _fit((_row(day=1, lag="1", target="1"), _row(day=2, lag="4", target="10")))
    assert fit.slope == Decimal("3")
    assert fit.slope > 0


def test_negative_slope_is_preserved() -> None:
    fit = _fit((_row(day=1, lag="1", target="10"), _row(day=2, lag="4", target="1")))
    assert fit.slope == Decimal("-3")
    assert fit.slope < 0


def test_zero_slope_with_constant_targets_is_valid() -> None:
    rows = (
        _row(day=1, lag="1", target="7"),
        _row(day=2, lag="3", target="7"),
        _row(day=3, lag="5", target="7"),
    )
    fit = _fit(rows)
    assert fit.slope == Decimal("0")
    assert fit.intercept_amount_per_mwh == Decimal("7")


def test_zero_feature_variance_fails_closed() -> None:
    rows = (
        _row(day=1, lag="4", target="1"),
        _row(day=2, lag="4", target="9"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _fit(rows)
    assert captured.value.message == _ZERO_VARIANCE_MESSAGE


def test_partially_repeated_feature_values_remain_valid() -> None:
    # x = 2, 2, 8 ; y = 1, 3, 5 -> x_mean = 4, y_mean = 3,
    # numerator = 12, denominator = 24, so slope = 0.5 and intercept = 1.
    rows = (
        _row(day=1, lag="2", target="1"),
        _row(day=2, lag="2", target="3"),
        _row(day=3, lag="8", target="5"),
    )
    fit = _fit(rows)
    assert fit.slope == Decimal("12") / Decimal("24")
    assert fit.slope == Decimal("0.5")
    assert fit.intercept_amount_per_mwh == Decimal("1")
    # Repeated x-values alone do not make the fit degenerate.
    assert fit.slope != Decimal("0")


def test_negative_derived_values_are_valid_without_clamping() -> None:
    rows = (
        _row(day=1, lag="-20", target="-30"),
        _row(day=2, lag="-10", target="-10"),
    )
    fit = _fit(rows)
    assert fit.slope == Decimal("2")
    assert fit.intercept_amount_per_mwh == Decimal("10")
    assert fit.intercept_amount_per_mwh > 0


def test_mixed_markets_fail_closed_without_leaking_ids() -> None:
    rows = (
        _row(day=1, lag="1", target="1", market_id="market-alpha"),
        _row(day=2, lag="2", target="2", market_id="market-beta"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _fit(rows)
    assert captured.value.message == _MIXED_MARKET_MESSAGE
    assert "market-alpha" not in captured.value.message
    assert "market-beta" not in captured.value.message


def test_mixed_currencies_fail_closed_without_leaking_codes() -> None:
    rows = (
        _row(day=1, lag="1", target="1", currency="AMD"),
        _row(day=2, lag="2", target="2", currency="EUR"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _fit(rows)
    assert captured.value.message == _MIXED_CURRENCY_MESSAGE
    assert "AMD" not in captured.value.message
    assert "EUR" not in captured.value.message


def test_duplicate_target_timestamps_fail_closed() -> None:
    rows = (
        _row(day=2, lag="1", target="1"),
        _row(day=2, lag="2", target="2"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _fit(rows)
    assert captured.value.message == _DUPLICATE_TIMESTAMP_MESSAGE


def test_out_of_order_target_timestamps_fail_closed() -> None:
    rows = (
        _row(day=3, lag="1", target="1"),
        _row(day=1, lag="2", target="2"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _fit(rows)
    assert captured.value.message == _OUT_OF_ORDER_MESSAGE


def test_out_of_order_input_is_not_silently_sorted() -> None:
    late = _row(day=3, lag="1", target="1")
    early = _row(day=1, lag="2", target="2")
    with pytest.raises(InvalidRequestError) as captured:
        _fit((late, early))
    assert captured.value.message == _OUT_OF_ORDER_MESSAGE
    reversed_fit = _fit((early, late))
    assert reversed_fit.slope == Decimal("1")


def test_non_finite_feature_value_fails_closed() -> None:
    rows = (
        _row(day=1, lag="1", target="1"),
        _row(day=2, lag="2", target="2"),
    )
    poisoned = DAMPriceLag24hFeatureRow(
        market_id="market-1",
        currency="AMD",
        target_timestamp=rows[1].target_timestamp,
        lag_24h_amount_per_mwh=Decimal("NaN"),
        target_amount_per_mwh=rows[1].target_amount_per_mwh,
    )
    with pytest.raises(InvalidRequestError) as captured:
        _fit((rows[0], poisoned))
    assert captured.value.message == _NON_FINITE_INPUT_MESSAGE


def test_non_finite_target_value_fails_closed() -> None:
    first = _row(day=1, lag="1", target="1")
    poisoned = DAMPriceLag24hFeatureRow(
        market_id="market-1",
        currency="AMD",
        target_timestamp=_ts(2),
        lag_24h_amount_per_mwh=Decimal("2"),
        target_amount_per_mwh=Decimal("Infinity"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _fit((first, poisoned))
    assert captured.value.message == _NON_FINITE_INPUT_MESSAGE


def test_non_finite_feature_value_fails_closed_for_first_row_too() -> None:
    poisoned = DAMPriceLag24hFeatureRow(
        market_id="market-1",
        currency="AMD",
        target_timestamp=_ts(1),
        lag_24h_amount_per_mwh=Decimal("-Infinity"),
        target_amount_per_mwh=Decimal("1"),
    )
    second = _row(day=2, lag="2", target="2")
    with pytest.raises(InvalidRequestError) as captured:
        _fit((poisoned, second))
    assert captured.value.message == _NON_FINITE_INPUT_MESSAGE


def test_extreme_cohort_fails_closed_rather_than_returning_non_finite() -> None:
    # Squared deviations of this magnitude exceed the context exponent range,
    # so OLS parameters cannot be finite. The fitter must translate that
    # Decimal arithmetic signal into the sanitized failure family rather than
    # leaking a raw Decimal exception or returning a non-finite value.
    rows = (
        _row(day=1, lag="1E+600000", target="1"),
        _row(day=2, lag="5E+600000", target="2"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _fit(rows)
    assert captured.value.message == _NON_FINITE_FIT_MESSAGE


def test_result_is_not_rounded_or_quantized() -> None:
    # 1.00 / 3 produces a non-terminating quotient under the default context;
    # the fitter must not round or quantize it.
    rows = (
        _row(day=1, lag="1.00", target="0"),
        _row(day=2, lag="4.00", target="1.00"),
    )
    fit = _fit(rows)
    assert fit.slope == Decimal("1.00") / Decimal("3.00")
    assert fit.slope != Decimal("0.33")
    assert fit.slope != Decimal("0.333")


def test_input_rows_are_not_mutated() -> None:
    first = _row(day=1, lag="1", target="3")
    second = _row(day=2, lag="2", target="5")
    rows = (first, second)
    _fit(rows)
    assert rows == (first, second)
    assert first.lag_24h_amount_per_mwh == Decimal("1")
    assert second.target_amount_per_mwh == Decimal("5")


def test_repeated_equal_input_is_value_equivalent() -> None:
    rows = (_row(day=1, lag="1", target="3"), _row(day=2, lag="2", target="5"))
    assert _fit(rows) == _fit(rows)


def test_result_contract_is_frozen_slotted_and_exactly_two_fields() -> None:
    names = tuple(item.name for item in fields(DAMPriceLag24hLinearRegressionFit))
    assert names == ("slope", "intercept_amount_per_mwh")
    assert DAMPriceLag24hLinearRegressionFit.__slots__ == names
    fit = _fit((_row(day=1, lag="1", target="3"), _row(day=2, lag="2", target="5")))
    with pytest.raises(FrozenInstanceError):
        fit.slope = Decimal("0")  # type: ignore[misc]


def test_result_exposes_no_identity_metric_or_metadata_fields() -> None:
    names = {item.name for item in fields(DAMPriceLag24hLinearRegressionFit)}
    forbidden = {
        "market_id",
        "currency",
        "case_count",
        "row_count",
        "mae",
        "mse",
        "rmse",
        "r2",
        "residual",
        "model_name",
        "model_version",
        "provider",
        "timestamp",
        "generated_at",
        "forecast_run_id",
    }
    assert forbidden.isdisjoint(names)
    assert len(names) == 2


def test_fitter_is_synchronous_and_keyword_only() -> None:
    assert not inspect.iscoroutinefunction(fit_dam_price_lag_24h_linear_regression)
    parameters = inspect.signature(fit_dam_price_lag_24h_linear_regression).parameters
    assert tuple(parameters) == ("training_rows",)
    assert parameters["training_rows"].kind is inspect.Parameter.KEYWORD_ONLY


def test_fit_ignores_row_position_and_uses_only_amount_values() -> None:
    # Two cohorts with identical (x, y) values but different calendar spacing
    # must produce identical parameters.
    dense = (
        _row(day=1, lag="1", target="3"),
        _row(day=2, lag="2", target="5"),
        _row(day=3, lag="3", target="7"),
    )
    sparse = (
        _row(day=1, lag="1", target="3"),
        _row(day=9, lag="2", target="5"),
        _row(day=20, lag="3", target="7"),
    )
    assert _fit(dense) == _fit(sparse)
