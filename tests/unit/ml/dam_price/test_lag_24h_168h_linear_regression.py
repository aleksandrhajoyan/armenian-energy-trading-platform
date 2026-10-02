"""Lag-24h plus lag-168h ordinary least-squares DAM Price parameter fit."""

from __future__ import annotations

import inspect
from dataclasses import MISSING, FrozenInstanceError, fields
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation, Overflow, localcontext

import pytest

from energy_trading.application.errors import InvalidRequestError

# ``energy_trading.domain.models`` must initialize before
# ``energy_trading.domain.value_objects`` because the domain models package
# imports ``EnergyPrice`` from it during its own initialization. Importing the
# models package explicitly keeps that pre-existing order; the fitter itself
# does not consume ``MarketPriceRecord``.
from energy_trading.domain.models.observations import MarketPriceRecord  # noqa: F401
from energy_trading.ml.dam_price import lag_24h_168h_linear_regression as fit_module
from energy_trading.ml.dam_price.lag_24h_168h_features import DAMPriceLag24h168hFeatureRow
from energy_trading.ml.dam_price.lag_24h_168h_linear_regression import (
    DAMPriceLag24h168hLinearRegressionFit,
    fit_dam_price_lag_24h_168h_linear_regression,
)

_PREFIX = "DAM Price 24h+168h linear regression requires"
_TOO_FEW_ROWS_MESSAGE = f"{_PREFIX} at least three training rows."
_MIXED_MARKET_MESSAGE = f"{_PREFIX} rows from exactly one market."
_MIXED_CURRENCY_MESSAGE = f"{_PREFIX} rows in exactly one currency."
_DUPLICATE_TIMESTAMP_MESSAGE = f"{_PREFIX} unique target timestamps."
_OUT_OF_ORDER_MESSAGE = f"{_PREFIX} strictly increasing target timestamps."
_SINGULAR_DESIGN_MESSAGE = f"{_PREFIX} a full-rank two-feature design."
_NON_FINITE_INPUT_MESSAGE = f"{_PREFIX} finite feature and target values."
_NON_FINITE_FIT_MESSAGE = f"{_PREFIX} finite fitted coefficients and intercept."

# Full-rank base design: x1 mean 1, x2 mean 1.25, so every exact linear
# target below keeps all Decimal quotients terminating.
_BASE_DESIGN = (("1", "0"), ("0", "1"), ("1", "1"), ("2", "3"))


def _ts(day: int, hour: int = 16) -> datetime:
    return datetime(2026, 10, day, hour, 0, 0, tzinfo=UTC)


def _row(
    *,
    day: int,
    lag_24h: str = "1",
    lag_168h: str = "1",
    target: str = "1",
    market_id: str = "market-1",
    currency: str = "AMD",
) -> DAMPriceLag24h168hFeatureRow:
    return DAMPriceLag24h168hFeatureRow(
        market_id=market_id,
        currency=currency,
        target_timestamp=_ts(day),
        lag_24h_amount_per_mwh=Decimal(lag_24h),
        lag_168h_amount_per_mwh=Decimal(lag_168h),
        target_amount_per_mwh=Decimal(target),
    )


def _linear_rows(
    *,
    lag_24h_coefficient: str,
    lag_168h_coefficient: str,
    intercept: str,
    design: tuple[tuple[str, str], ...] = _BASE_DESIGN,
) -> tuple[DAMPriceLag24h168hFeatureRow, ...]:
    a = Decimal(lag_24h_coefficient)
    b = Decimal(lag_168h_coefficient)
    c = Decimal(intercept)
    return tuple(
        _row(
            day=index + 1,
            lag_24h=x1,
            lag_168h=x2,
            target=str(a * Decimal(x1) + b * Decimal(x2) + c),
        )
        for index, (x1, x2) in enumerate(design)
    )


def _fit(
    rows: tuple[DAMPriceLag24h168hFeatureRow, ...],
) -> DAMPriceLag24h168hLinearRegressionFit:
    return fit_dam_price_lag_24h_168h_linear_regression(training_rows=rows)


def _assert_fails(rows: tuple[DAMPriceLag24h168hFeatureRow, ...], message: str) -> None:
    with pytest.raises(InvalidRequestError) as captured:
        _fit(rows)
    assert captured.value.message == message


def _poisoned(
    *,
    day: int,
    lag_24h: Decimal = Decimal("1"),
    lag_168h: Decimal = Decimal("1"),
    target: Decimal = Decimal("1"),
) -> DAMPriceLag24h168hFeatureRow:
    return DAMPriceLag24h168hFeatureRow(
        market_id="market-1",
        currency="AMD",
        target_timestamp=_ts(day),
        lag_24h_amount_per_mwh=lag_24h,
        lag_168h_amount_per_mwh=lag_168h,
        target_amount_per_mwh=target,
    )


# --- exact coefficient recovery -------------------------------------------


def test_exact_known_two_feature_equation_is_recovered() -> None:
    fit = _fit(_linear_rows(lag_24h_coefficient="2", lag_168h_coefficient="3", intercept="5"))
    assert fit == DAMPriceLag24h168hLinearRegressionFit(
        lag_24h_coefficient=Decimal("2"),
        lag_168h_coefficient=Decimal("3"),
        intercept_amount_per_mwh=Decimal("5"),
    )


def test_second_independent_exact_equation_is_recovered() -> None:
    # Separate three-row design (0,0), (3,0), (0,3): means 1 and 1.
    rows = _linear_rows(
        lag_24h_coefficient="-4",
        lag_168h_coefficient="0.5",
        intercept="-2",
        design=(("0", "0"), ("3", "0"), ("0", "3")),
    )
    fit = _fit(rows)
    assert fit.lag_24h_coefficient == Decimal("-4")
    assert fit.lag_168h_coefficient == Decimal("0.5")
    assert fit.intercept_amount_per_mwh == Decimal("-2")


def test_intercept_is_recovered_exactly() -> None:
    fit = _fit(_linear_rows(lag_24h_coefficient="1", lag_168h_coefficient="1", intercept="12.25"))
    assert fit.intercept_amount_per_mwh == Decimal("12.25")


def test_lag_24h_coefficient_role_is_correct() -> None:
    # The target depends only on the lag-24h feature.
    fit = _fit(_linear_rows(lag_24h_coefficient="6", lag_168h_coefficient="0", intercept="0"))
    assert fit.lag_24h_coefficient == Decimal("6")
    assert fit.lag_168h_coefficient == Decimal("0")


def test_lag_168h_coefficient_role_is_correct() -> None:
    # The target depends only on the lag-168h feature.
    fit = _fit(_linear_rows(lag_24h_coefficient="0", lag_168h_coefficient="6", intercept="0"))
    assert fit.lag_24h_coefficient == Decimal("0")
    assert fit.lag_168h_coefficient == Decimal("6")


def test_coefficients_are_not_swapped() -> None:
    fit = _fit(_linear_rows(lag_24h_coefficient="2", lag_168h_coefficient="7", intercept="1"))
    assert fit.lag_24h_coefficient == Decimal("2")
    assert fit.lag_168h_coefficient == Decimal("7")
    assert fit.lag_24h_coefficient != fit.lag_168h_coefficient


def test_positive_coefficients_are_valid() -> None:
    fit = _fit(_linear_rows(lag_24h_coefficient="0.75", lag_168h_coefficient="1.5", intercept="3"))
    assert fit.lag_24h_coefficient == Decimal("0.75")
    assert fit.lag_168h_coefficient == Decimal("1.5")
    assert fit.lag_24h_coefficient > 0
    assert fit.lag_168h_coefficient > 0


def test_negative_lag_24h_coefficient_is_valid() -> None:
    fit = _fit(_linear_rows(lag_24h_coefficient="-3", lag_168h_coefficient="2", intercept="4"))
    assert fit.lag_24h_coefficient == Decimal("-3")
    assert fit.lag_24h_coefficient < 0


def test_negative_lag_168h_coefficient_is_valid() -> None:
    fit = _fit(_linear_rows(lag_24h_coefficient="3", lag_168h_coefficient="-2", intercept="4"))
    assert fit.lag_168h_coefficient == Decimal("-2")
    assert fit.lag_168h_coefficient < 0


def test_negative_intercept_is_valid() -> None:
    fit = _fit(_linear_rows(lag_24h_coefficient="1", lag_168h_coefficient="2", intercept="-9"))
    assert fit.intercept_amount_per_mwh == Decimal("-9")
    assert fit.intercept_amount_per_mwh < 0


def test_zero_lag_24h_coefficient_is_valid_on_full_rank_design() -> None:
    fit = _fit(_linear_rows(lag_24h_coefficient="0", lag_168h_coefficient="4", intercept="1"))
    assert fit.lag_24h_coefficient == Decimal("0")
    assert fit.lag_168h_coefficient == Decimal("4")
    assert fit.intercept_amount_per_mwh == Decimal("1")


def test_zero_lag_168h_coefficient_is_valid_on_full_rank_design() -> None:
    fit = _fit(_linear_rows(lag_24h_coefficient="5", lag_168h_coefficient="0", intercept="-3"))
    assert fit.lag_24h_coefficient == Decimal("5")
    assert fit.lag_168h_coefficient == Decimal("0")
    assert fit.intercept_amount_per_mwh == Decimal("-3")


def test_zero_intercept_is_valid() -> None:
    fit = _fit(_linear_rows(lag_24h_coefficient="1", lag_168h_coefficient="1", intercept="0"))
    assert fit.intercept_amount_per_mwh == Decimal("0")


def test_minimum_three_row_full_rank_fit_succeeds() -> None:
    rows = _linear_rows(
        lag_24h_coefficient="2",
        lag_168h_coefficient="-1",
        intercept="10",
        design=(("0", "0"), ("3", "0"), ("0", "3")),
    )
    assert len(rows) == 3
    fit = _fit(rows)
    assert fit.lag_24h_coefficient == Decimal("2")
    assert fit.lag_168h_coefficient == Decimal("-1")
    assert fit.intercept_amount_per_mwh == Decimal("10")


def test_more_than_three_row_noisy_fit_matches_manual_decimal_ols() -> None:
    # x1 = 0, 2, 0, 2 ; x2 = 0, 0, 2, 2 ; y = 1, 5, 3, 9
    # means 1, 1, 4.5 ; s11 = s22 = 4, s12 = 0 ; t1 = 10, t2 = 6
    # determinant = 16 ; b1 = 40 / 16 = 2.5 ; b2 = 24 / 16 = 1.5
    # intercept = 4.5 - 2.5 - 1.5 = 0.5
    rows = (
        _row(day=1, lag_24h="0", lag_168h="0", target="1"),
        _row(day=2, lag_24h="2", lag_168h="0", target="5"),
        _row(day=3, lag_24h="0", lag_168h="2", target="3"),
        _row(day=4, lag_24h="2", lag_168h="2", target="9"),
    )
    fit = _fit(rows)
    assert fit.lag_24h_coefficient == Decimal("2.5")
    assert fit.lag_168h_coefficient == Decimal("1.5")
    assert fit.intercept_amount_per_mwh == Decimal("0.5")


def test_both_features_and_target_participate_numerically() -> None:
    base = _fit(_linear_rows(lag_24h_coefficient="2", lag_168h_coefficient="3", intercept="5"))
    shifted_lag_168h = list(
        _linear_rows(lag_24h_coefficient="2", lag_168h_coefficient="3", intercept="5")
    )
    first = shifted_lag_168h[0]
    shifted_lag_168h[0] = _row(
        day=1,
        lag_24h=str(first.lag_24h_amount_per_mwh),
        lag_168h="4",
        target=str(first.target_amount_per_mwh),
    )
    assert _fit(tuple(shifted_lag_168h)) != base


# --- too few rows / singular design ---------------------------------------


def test_empty_input_fails_closed() -> None:
    _assert_fails((), _TOO_FEW_ROWS_MESSAGE)


def test_one_row_fails_closed() -> None:
    _assert_fails((_row(day=1),), _TOO_FEW_ROWS_MESSAGE)


def test_two_rows_fail_closed() -> None:
    rows = (
        _row(day=1, lag_24h="1", lag_168h="0", target="3"),
        _row(day=2, lag_24h="0", lag_168h="1", target="5"),
    )
    _assert_fails(rows, _TOO_FEW_ROWS_MESSAGE)


def test_zero_variance_in_lag_24h_fails_closed() -> None:
    rows = (
        _row(day=1, lag_24h="5", lag_168h="1", target="1"),
        _row(day=2, lag_24h="5", lag_168h="2", target="4"),
        _row(day=3, lag_24h="5", lag_168h="4", target="9"),
    )
    _assert_fails(rows, _SINGULAR_DESIGN_MESSAGE)


def test_zero_variance_in_lag_168h_fails_closed() -> None:
    rows = (
        _row(day=1, lag_24h="1", lag_168h="7", target="1"),
        _row(day=2, lag_24h="2", lag_168h="7", target="4"),
        _row(day=3, lag_24h="4", lag_168h="7", target="9"),
    )
    _assert_fails(rows, _SINGULAR_DESIGN_MESSAGE)


def test_perfect_feature_collinearity_fails_closed() -> None:
    rows = (
        _row(day=1, lag_24h="1", lag_168h="2", target="3"),
        _row(day=2, lag_24h="2", lag_168h="4", target="1"),
        _row(day=3, lag_24h="3", lag_168h="6", target="8"),
        _row(day=4, lag_24h="4", lag_168h="8", target="2"),
    )
    _assert_fails(rows, _SINGULAR_DESIGN_MESSAGE)


def test_singular_design_does_not_fall_back_to_a_one_feature_fit() -> None:
    # The target is an exact line in lag-24h alone, so a one-feature fallback
    # would succeed. The two-feature fitter must still fail closed.
    rows = (
        _row(day=1, lag_24h="1", lag_168h="3", target="3"),
        _row(day=2, lag_24h="2", lag_168h="6", target="5"),
        _row(day=3, lag_24h="3", lag_168h="9", target="7"),
    )
    _assert_fails(rows, _SINGULAR_DESIGN_MESSAGE)
    assert not hasattr(fit_module, "fit_dam_price_lag_24h_linear_regression")
    assert not hasattr(fit_module, "DAMPriceLag24hLinearRegressionFit")


def test_partially_repeated_lag_24h_values_succeed_when_full_rank() -> None:
    rows = _linear_rows(
        lag_24h_coefficient="2",
        lag_168h_coefficient="3",
        intercept="5",
        design=(("1", "0"), ("1", "2"), ("3", "1"), ("3", "3")),
    )
    fit = _fit(rows)
    assert fit.lag_24h_coefficient == Decimal("2")
    assert fit.lag_168h_coefficient == Decimal("3")
    assert fit.intercept_amount_per_mwh == Decimal("5")


def test_partially_repeated_lag_168h_values_succeed_when_full_rank() -> None:
    rows = _linear_rows(
        lag_24h_coefficient="2",
        lag_168h_coefficient="3",
        intercept="5",
        design=(("0", "1"), ("2", "1"), ("1", "3"), ("3", "3")),
    )
    fit = _fit(rows)
    assert fit.lag_24h_coefficient == Decimal("2")
    assert fit.lag_168h_coefficient == Decimal("3")
    assert fit.intercept_amount_per_mwh == Decimal("5")


# --- market / currency coherence ------------------------------------------


def test_mixed_markets_fail_closed() -> None:
    rows = (
        _row(day=1, lag_24h="1", lag_168h="0", market_id="market-alpha"),
        _row(day=2, lag_24h="0", lag_168h="1", market_id="market-alpha"),
        _row(day=3, lag_24h="2", lag_168h="3", market_id="market-beta"),
    )
    _assert_fails(rows, _MIXED_MARKET_MESSAGE)


def test_mixed_market_message_leaks_no_raw_identifier() -> None:
    rows = (
        _row(day=1, lag_24h="1", lag_168h="0", market_id="market-alpha"),
        _row(day=2, lag_24h="0", lag_168h="1", market_id="market-beta"),
        _row(day=3, lag_24h="2", lag_168h="3", market_id="market-alpha"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _fit(rows)
    assert "market-alpha" not in captured.value.message
    assert "market-beta" not in captured.value.message
    assert "market-alpha" not in str(captured.value)
    assert "market-beta" not in str(captured.value)


def test_mixed_currencies_fail_closed() -> None:
    rows = (
        _row(day=1, lag_24h="1", lag_168h="0", currency="AMD"),
        _row(day=2, lag_24h="0", lag_168h="1", currency="AMD"),
        _row(day=3, lag_24h="2", lag_168h="3", currency="EUR"),
    )
    _assert_fails(rows, _MIXED_CURRENCY_MESSAGE)


def test_mixed_currency_message_leaks_no_raw_code() -> None:
    rows = (
        _row(day=1, lag_24h="1", lag_168h="0", currency="AMD"),
        _row(day=2, lag_24h="0", lag_168h="1", currency="EUR"),
        _row(day=3, lag_24h="2", lag_168h="3", currency="AMD"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _fit(rows)
    assert "AMD" not in captured.value.message
    assert "EUR" not in captured.value.message
    assert "AMD" not in str(captured.value)
    assert "EUR" not in str(captured.value)


# --- chronology -----------------------------------------------------------


def test_duplicate_timestamps_fail_closed() -> None:
    rows = (
        _row(day=1, lag_24h="1", lag_168h="0"),
        _row(day=2, lag_24h="0", lag_168h="1"),
        _row(day=2, lag_24h="2", lag_168h="3"),
    )
    _assert_fails(rows, _DUPLICATE_TIMESTAMP_MESSAGE)


def test_out_of_order_timestamps_fail_closed() -> None:
    rows = (
        _row(day=1, lag_24h="1", lag_168h="0"),
        _row(day=3, lag_24h="0", lag_168h="1"),
        _row(day=2, lag_24h="2", lag_168h="3"),
    )
    _assert_fails(rows, _OUT_OF_ORDER_MESSAGE)


def test_correct_chronological_order_succeeds() -> None:
    rows = _linear_rows(lag_24h_coefficient="2", lag_168h_coefficient="3", intercept="5")
    assert all(
        earlier.target_timestamp < later.target_timestamp
        for earlier, later in zip(rows, rows[1:], strict=False)
    )
    assert _fit(rows).lag_24h_coefficient == Decimal("2")


def test_rows_are_not_silently_sorted() -> None:
    rows = _linear_rows(lag_24h_coefficient="2", lag_168h_coefficient="3", intercept="5")
    reversed_rows = tuple(reversed(rows))
    _assert_fails(reversed_rows, _OUT_OF_ORDER_MESSAGE)
    assert _fit(rows).lag_168h_coefficient == Decimal("3")


def test_row_position_does_not_participate_numerically() -> None:
    dense = _linear_rows(lag_24h_coefficient="2", lag_168h_coefficient="3", intercept="5")
    sparse = tuple(
        _row(
            day=day,
            lag_24h=str(row.lag_24h_amount_per_mwh),
            lag_168h=str(row.lag_168h_amount_per_mwh),
            target=str(row.target_amount_per_mwh),
        )
        for day, row in zip((2, 9, 17, 28), dense, strict=True)
    )
    assert _fit(dense) == _fit(sparse)


# --- finite inputs / Decimal signals --------------------------------------


def _valid_prefix() -> tuple[DAMPriceLag24h168hFeatureRow, ...]:
    return (
        _row(day=1, lag_24h="1", lag_168h="0", target="7"),
        _row(day=2, lag_24h="0", lag_168h="1", target="8"),
    )


def test_forged_nan_lag_24h_fails_closed() -> None:
    rows = (*_valid_prefix(), _poisoned(day=3, lag_24h=Decimal("NaN")))
    _assert_fails(rows, _NON_FINITE_INPUT_MESSAGE)


def test_forged_infinity_lag_24h_fails_closed() -> None:
    rows = (*_valid_prefix(), _poisoned(day=3, lag_24h=Decimal("Infinity")))
    _assert_fails(rows, _NON_FINITE_INPUT_MESSAGE)


def test_forged_nan_lag_168h_fails_closed() -> None:
    rows = (*_valid_prefix(), _poisoned(day=3, lag_168h=Decimal("NaN")))
    _assert_fails(rows, _NON_FINITE_INPUT_MESSAGE)


def test_forged_infinity_lag_168h_fails_closed() -> None:
    rows = (_poisoned(day=1, lag_168h=Decimal("-Infinity")), *_valid_prefix()[1:], _row(day=3))
    _assert_fails(rows, _NON_FINITE_INPUT_MESSAGE)


def test_forged_non_finite_target_fails_closed() -> None:
    rows = (*_valid_prefix(), _poisoned(day=3, target=Decimal("Infinity")))
    _assert_fails(rows, _NON_FINITE_INPUT_MESSAGE)


def test_decimal_arithmetic_signal_is_converted_to_invalid_request() -> None:
    # Squared deviations of this magnitude exceed the context exponent range,
    # so the fitter must translate the Decimal Overflow signal into the
    # sanitized failure family rather than leaking a raw Decimal exception.
    rows = (
        _row(day=1, lag_24h="1E+600000", lag_168h="0", target="1"),
        _row(day=2, lag_24h="5E+600000", lag_168h="1", target="2"),
        _row(day=3, lag_24h="2E+600000", lag_168h="3", target="3"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _fit(rows)
    assert captured.value.message == _NON_FINITE_FIT_MESSAGE
    assert "E+600000" not in str(captured.value)


def test_non_finite_computed_value_fails_closed_when_signals_are_untrapped() -> None:
    # With Decimal traps disabled the same cohort silently yields non-finite
    # intermediate values; the fitter must still refuse to return them.
    rows = (
        _row(day=1, lag_24h="1E+600000", lag_168h="0", target="1"),
        _row(day=2, lag_24h="5E+600000", lag_168h="1", target="2"),
        _row(day=3, lag_24h="2E+600000", lag_168h="3", target="3"),
    )
    with localcontext() as context:
        context.traps[Overflow] = False
        context.traps[InvalidOperation] = False
        with pytest.raises(InvalidRequestError) as captured:
            _fit(rows)
    assert captured.value.message == _NON_FINITE_FIT_MESSAGE


def test_result_is_not_rounded_or_quantized() -> None:
    # x1 = 0, 3, 0 ; x2 = 0, 0, 3 ; y = 0, 1, 0
    # means 1, 1, 1/3 ; b1 = 1/3 (non-terminating) ; b2 = 0
    rows = (
        _row(day=1, lag_24h="0", lag_168h="0", target="0"),
        _row(day=2, lag_24h="3", lag_168h="0", target="1"),
        _row(day=3, lag_24h="0", lag_168h="3", target="0"),
    )
    fit = _fit(rows)
    assert fit.lag_24h_coefficient != Decimal("0.33")
    assert fit.lag_24h_coefficient != Decimal("0.333")
    assert len(fit.lag_24h_coefficient.as_tuple().digits) > 6


# --- purity / contract ----------------------------------------------------


def test_input_tuple_is_unchanged() -> None:
    rows = _linear_rows(lag_24h_coefficient="2", lag_168h_coefficient="3", intercept="5")
    snapshot = tuple(rows)
    _fit(rows)
    assert rows == snapshot
    assert all(left is right for left, right in zip(rows, snapshot, strict=True))


def test_input_rows_are_unchanged() -> None:
    rows = _linear_rows(lag_24h_coefficient="2", lag_168h_coefficient="3", intercept="5")
    values = tuple(
        (
            row.lag_24h_amount_per_mwh,
            row.lag_168h_amount_per_mwh,
            row.target_amount_per_mwh,
            row.target_timestamp,
        )
        for row in rows
    )
    _fit(rows)
    assert values == tuple(
        (
            row.lag_24h_amount_per_mwh,
            row.lag_168h_amount_per_mwh,
            row.target_amount_per_mwh,
            row.target_timestamp,
        )
        for row in rows
    )


def test_repeated_equal_calls_return_value_equal_fit() -> None:
    rows = _linear_rows(lag_24h_coefficient="2", lag_168h_coefficient="3", intercept="5")
    assert _fit(rows) == _fit(rows)


def test_result_dataclass_is_frozen() -> None:
    fit = _fit(_linear_rows(lag_24h_coefficient="2", lag_168h_coefficient="3", intercept="5"))
    with pytest.raises(FrozenInstanceError):
        fit.lag_24h_coefficient = Decimal("0")  # type: ignore[misc]


def test_result_dataclass_is_slotted() -> None:
    names = tuple(item.name for item in fields(DAMPriceLag24h168hLinearRegressionFit))
    assert DAMPriceLag24h168hLinearRegressionFit.__slots__ == names
    fit = _fit(_linear_rows(lag_24h_coefficient="2", lag_168h_coefficient="3", intercept="5"))
    assert not hasattr(fit, "__dict__")


def test_result_has_exactly_three_fields() -> None:
    names = tuple(item.name for item in fields(DAMPriceLag24h168hLinearRegressionFit))
    assert names == (
        "lag_24h_coefficient",
        "lag_168h_coefficient",
        "intercept_amount_per_mwh",
    )


def test_result_fields_have_no_defaults() -> None:
    for item in fields(DAMPriceLag24h168hLinearRegressionFit):
        assert item.default is MISSING
        assert item.default_factory is MISSING


def test_returned_numeric_fields_are_decimal_never_float() -> None:
    fit = _fit(_linear_rows(lag_24h_coefficient="2", lag_168h_coefficient="3", intercept="5"))
    for value in (
        fit.lag_24h_coefficient,
        fit.lag_168h_coefficient,
        fit.intercept_amount_per_mwh,
    ):
        assert isinstance(value, Decimal)
        assert not isinstance(value, float)
        assert value.is_finite()


def test_fitter_is_synchronous() -> None:
    assert not inspect.iscoroutinefunction(fit_dam_price_lag_24h_168h_linear_regression)
    result = _fit(_linear_rows(lag_24h_coefficient="2", lag_168h_coefficient="3", intercept="5"))
    assert isinstance(result, DAMPriceLag24h168hLinearRegressionFit)


def test_fitter_is_keyword_only_without_defaults() -> None:
    parameters = inspect.signature(fit_dam_price_lag_24h_168h_linear_regression).parameters
    assert tuple(parameters) == ("training_rows",)
    assert parameters["training_rows"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["training_rows"].default is inspect.Parameter.empty
    rows = _linear_rows(lag_24h_coefficient="2", lag_168h_coefficient="3", intercept="5")
    with pytest.raises(TypeError):
        fit_dam_price_lag_24h_168h_linear_regression(rows)  # type: ignore[misc]


def test_result_exposes_no_prediction_metric_or_comparison_output() -> None:
    names = {item.name for item in fields(DAMPriceLag24h168hLinearRegressionFit)}
    forbidden = {
        "market_id",
        "currency",
        "case_count",
        "row_count",
        "predictions",
        "predicted_amount_per_mwh",
        "mae",
        "mae_amount_per_mwh",
        "mse",
        "rmse",
        "r2",
        "residuals",
        "winner",
        "champion",
        "model_name",
        "model_version",
        "timestamp",
        "cutoff",
    }
    assert forbidden.isdisjoint(names)
    public = {
        name for name in dir(DAMPriceLag24h168hLinearRegressionFit) if not name.startswith("_")
    }
    assert public == names
