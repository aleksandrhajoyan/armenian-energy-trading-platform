"""Lag-24h plus lag-168h ordinary-least-squares DAM Price evaluation prediction."""

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
# models package explicitly keeps that pre-existing order; the predictor itself
# does not consume ``MarketPriceRecord``.
from energy_trading.domain.models.observations import MarketPriceRecord  # noqa: F401
from energy_trading.ml.dam_price.lag_24h_168h_features import DAMPriceLag24h168hFeatureRow
from energy_trading.ml.dam_price.lag_24h_168h_linear_regression import (
    DAMPriceLag24h168hLinearRegressionFit,
    fit_dam_price_lag_24h_168h_linear_regression,
)
from energy_trading.ml.dam_price.lag_24h_168h_linear_regression_prediction import (
    DAMPriceLag24h168hLinearRegressionPrediction,
    predict_dam_price_lag_24h_168h_linear_regression,
)

_PREFIX = "DAM Price 24h+168h linear regression prediction requires"
_EMPTY_ROWS_MESSAGE = f"{_PREFIX} at least one evaluation row."
_MIXED_MARKET_MESSAGE = f"{_PREFIX} rows from exactly one market."
_MIXED_CURRENCY_MESSAGE = f"{_PREFIX} rows in exactly one currency."
_DUPLICATE_TIMESTAMP_MESSAGE = f"{_PREFIX} unique target timestamps."
_OUT_OF_ORDER_MESSAGE = f"{_PREFIX} strictly increasing target timestamps."
_NON_FINITE_FIT_MESSAGE = f"{_PREFIX} finite fitted coefficients and intercept."
_NON_FINITE_INPUT_MESSAGE = f"{_PREFIX} finite feature and target values."
_NON_FINITE_PREDICTION_MESSAGE = f"{_PREFIX} finite predicted values."

FIVE_FIELDS = (
    "market_id",
    "currency",
    "target_timestamp",
    "predicted_amount_per_mwh",
    "actual_amount_per_mwh",
)

NON_FINITE_VALUES = ("NaN", "Infinity", "-Infinity")


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


def _fit(
    *,
    lag_24h_coefficient: str = "2",
    lag_168h_coefficient: str = "3",
    intercept: str = "1",
) -> DAMPriceLag24h168hLinearRegressionFit:
    return DAMPriceLag24h168hLinearRegressionFit(
        lag_24h_coefficient=Decimal(lag_24h_coefficient),
        lag_168h_coefficient=Decimal(lag_168h_coefficient),
        intercept_amount_per_mwh=Decimal(intercept),
    )


def _predict(
    *,
    fit: DAMPriceLag24h168hLinearRegressionFit | None = None,
    rows: tuple[DAMPriceLag24h168hFeatureRow, ...],
) -> tuple[DAMPriceLag24h168hLinearRegressionPrediction, ...]:
    return predict_dam_price_lag_24h_168h_linear_regression(
        fit=_fit() if fit is None else fit,
        evaluation_rows=rows,
    )


def test_exact_two_feature_decimal_prediction_formula() -> None:
    predictions = _predict(
        fit=_fit(lag_24h_coefficient="2", lag_168h_coefficient="3", intercept="1"),
        rows=(_row(day=1, lag_24h="5", lag_168h="7", target="32"),),
    )
    expected = Decimal("2") * Decimal("5") + Decimal("3") * Decimal("7") + Decimal("1")
    assert predictions[0].predicted_amount_per_mwh == expected
    assert predictions[0].predicted_amount_per_mwh == Decimal("32")


def test_lag_24h_coefficient_participates() -> None:
    base = _predict(
        fit=_fit(lag_24h_coefficient="2", lag_168h_coefficient="0", intercept="0"),
        rows=(_row(day=1, lag_24h="5", lag_168h="7"),),
    )[0]
    changed = _predict(
        fit=_fit(lag_24h_coefficient="4", lag_168h_coefficient="0", intercept="0"),
        rows=(_row(day=1, lag_24h="5", lag_168h="7"),),
    )[0]
    assert base.predicted_amount_per_mwh == Decimal("10")
    assert changed.predicted_amount_per_mwh == Decimal("20")


def test_lag_168h_coefficient_participates() -> None:
    base = _predict(
        fit=_fit(lag_24h_coefficient="0", lag_168h_coefficient="2", intercept="0"),
        rows=(_row(day=1, lag_24h="5", lag_168h="7"),),
    )[0]
    changed = _predict(
        fit=_fit(lag_24h_coefficient="0", lag_168h_coefficient="4", intercept="0"),
        rows=(_row(day=1, lag_24h="5", lag_168h="7"),),
    )[0]
    assert base.predicted_amount_per_mwh == Decimal("14")
    assert changed.predicted_amount_per_mwh == Decimal("28")


def test_intercept_participates() -> None:
    prediction = _predict(
        fit=_fit(lag_24h_coefficient="0", lag_168h_coefficient="0", intercept="12.5"),
        rows=(_row(day=1, lag_24h="5", lag_168h="7"),),
    )[0]
    assert prediction.predicted_amount_per_mwh == Decimal("12.5")


def test_feature_roles_are_not_swapped() -> None:
    # Correct: 10 * 1 + 1000 * 2 + 0 = 2010. Swapped: 10 * 2 + 1000 * 1 = 1020.
    prediction = _predict(
        fit=_fit(lag_24h_coefficient="10", lag_168h_coefficient="1000", intercept="0"),
        rows=(_row(day=1, lag_24h="1", lag_168h="2"),),
    )[0]
    assert prediction.predicted_amount_per_mwh == Decimal("2010")
    assert prediction.predicted_amount_per_mwh != Decimal("1020")


def test_parameters_from_the_published_fitter_drive_the_prediction() -> None:
    # y = 2 * x1 + 3 * x2 + 1 exactly over a full-rank design.
    training_rows = (
        _row(day=1, lag_24h="1", lag_168h="0", target="3"),
        _row(day=2, lag_24h="0", lag_168h="1", target="4"),
        _row(day=3, lag_24h="1", lag_168h="1", target="6"),
        _row(day=4, lag_24h="2", lag_168h="1", target="8"),
    )
    fit = fit_dam_price_lag_24h_168h_linear_regression(training_rows=training_rows)
    predictions = predict_dam_price_lag_24h_168h_linear_regression(
        fit=fit,
        evaluation_rows=(_row(day=5, lag_24h="4", lag_168h="5", target="24"),),
    )
    assert fit.lag_24h_coefficient == Decimal("2")
    assert fit.lag_168h_coefficient == Decimal("3")
    assert fit.intercept_amount_per_mwh == Decimal("1")
    assert predictions[0].predicted_amount_per_mwh == Decimal("24")


def test_one_valid_row_produces_one_prediction() -> None:
    predictions = _predict(rows=(_row(day=1),))
    assert isinstance(predictions, tuple)
    assert len(predictions) == 1
    assert isinstance(predictions[0], DAMPriceLag24h168hLinearRegressionPrediction)


def test_multiple_rows_produce_predictions_in_supplied_order() -> None:
    rows = (
        _row(day=1, lag_24h="1", lag_168h="1", target="6"),
        _row(day=2, lag_24h="2", lag_168h="1", target="8"),
        _row(day=3, lag_24h="3", lag_168h="2", target="13"),
    )
    predictions = _predict(rows=rows)
    assert len(predictions) == 3
    assert tuple(item.target_timestamp for item in predictions) == (_ts(1), _ts(2), _ts(3))
    assert tuple(item.predicted_amount_per_mwh for item in predictions) == (
        Decimal("6"),
        Decimal("8"),
        Decimal("13"),
    )


def test_identity_and_actual_values_are_preserved_exactly() -> None:
    row = _row(day=4, lag_24h="5", lag_168h="6", target="11", market_id="market-1")
    prediction = _predict(rows=(row,))[0]
    assert prediction.market_id == row.market_id
    assert prediction.currency == row.currency
    assert prediction.target_timestamp == row.target_timestamp
    assert prediction.actual_amount_per_mwh == row.target_amount_per_mwh
    assert prediction.target_timestamp is row.target_timestamp
    assert prediction.actual_amount_per_mwh is row.target_amount_per_mwh


def test_positive_prediction_is_valid() -> None:
    prediction = _predict(rows=(_row(day=1, lag_24h="5", lag_168h="1"),))[0]
    assert prediction.predicted_amount_per_mwh == Decimal("14")
    assert prediction.predicted_amount_per_mwh > 0


def test_exact_zero_prediction_is_valid() -> None:
    # 2 * 3 + 3 * (-2) + 0 = 0
    prediction = _predict(
        fit=_fit(intercept="0"),
        rows=(_row(day=1, lag_24h="3", lag_168h="-2", target="0"),),
    )[0]
    assert prediction.predicted_amount_per_mwh == Decimal("0")


def test_negative_prediction_is_preserved_and_not_clamped() -> None:
    prediction = _predict(
        fit=_fit(lag_24h_coefficient="-2", lag_168h_coefficient="-1", intercept="1"),
        rows=(_row(day=1, lag_24h="3", lag_168h="4", target="-9"),),
    )[0]
    assert prediction.predicted_amount_per_mwh == Decimal("-9")
    assert prediction.predicted_amount_per_mwh < 0


def test_negative_actual_price_remains_valid() -> None:
    prediction = _predict(rows=(_row(day=1, target="-17"),))[0]
    assert prediction.actual_amount_per_mwh == Decimal("-17")


def test_negative_lag_24h_feature_remains_valid() -> None:
    prediction = _predict(
        fit=_fit(intercept="0"),
        rows=(_row(day=1, lag_24h="-4", lag_168h="0"),),
    )[0]
    assert prediction.predicted_amount_per_mwh == Decimal("-8")


def test_negative_lag_168h_feature_remains_valid() -> None:
    prediction = _predict(
        fit=_fit(intercept="0"),
        rows=(_row(day=1, lag_24h="0", lag_168h="-4"),),
    )[0]
    assert prediction.predicted_amount_per_mwh == Decimal("-12")


def test_negative_lag_24h_coefficient_is_valid() -> None:
    prediction = _predict(
        fit=_fit(lag_24h_coefficient="-1.5", lag_168h_coefficient="0", intercept="0"),
        rows=(_row(day=1, lag_24h="2", lag_168h="9"),),
    )[0]
    assert prediction.predicted_amount_per_mwh == Decimal("-3.0")


def test_negative_lag_168h_coefficient_is_valid() -> None:
    prediction = _predict(
        fit=_fit(lag_24h_coefficient="0", lag_168h_coefficient="-2.5", intercept="0"),
        rows=(_row(day=1, lag_24h="9", lag_168h="2"),),
    )[0]
    assert prediction.predicted_amount_per_mwh == Decimal("-5.0")


def test_negative_intercept_is_valid() -> None:
    prediction = _predict(
        fit=_fit(lag_24h_coefficient="1", lag_168h_coefficient="1", intercept="-12.5"),
        rows=(_row(day=1, lag_24h="2", lag_168h="3"),),
    )[0]
    assert prediction.predicted_amount_per_mwh == Decimal("-7.5")


def test_empty_evaluation_rows_fail_closed() -> None:
    with pytest.raises(InvalidRequestError) as captured:
        _predict(rows=())
    assert captured.value.message == _EMPTY_ROWS_MESSAGE


def test_mixed_markets_fail_closed_without_leaking_ids() -> None:
    rows = (
        _row(day=1, market_id="market-alpha"),
        _row(day=2, market_id="market-beta"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _predict(rows=rows)
    assert captured.value.message == _MIXED_MARKET_MESSAGE
    assert "market-alpha" not in str(captured.value)
    assert "market-beta" not in str(captured.value)


def test_mixed_currencies_fail_closed_without_leaking_codes() -> None:
    rows = (_row(day=1, currency="AMD"), _row(day=2, currency="EUR"))
    with pytest.raises(InvalidRequestError) as captured:
        _predict(rows=rows)
    assert captured.value.message == _MIXED_CURRENCY_MESSAGE
    assert "AMD" not in str(captured.value)
    assert "EUR" not in str(captured.value)


def test_duplicate_target_timestamps_fail_closed() -> None:
    rows = (_row(day=2, lag_24h="1"), _row(day=2, lag_24h="2"))
    with pytest.raises(InvalidRequestError) as captured:
        _predict(rows=rows)
    assert captured.value.message == _DUPLICATE_TIMESTAMP_MESSAGE


def test_out_of_order_target_timestamps_fail_closed() -> None:
    rows = (_row(day=3), _row(day=1, lag_24h="2"))
    with pytest.raises(InvalidRequestError) as captured:
        _predict(rows=rows)
    assert captured.value.message == _OUT_OF_ORDER_MESSAGE


def test_out_of_order_input_is_not_silently_sorted() -> None:
    late = _row(day=3, lag_24h="1", target="1")
    early = _row(day=1, lag_24h="2", target="2")
    with pytest.raises(InvalidRequestError) as captured:
        _predict(rows=(late, early))
    assert captured.value.message == _OUT_OF_ORDER_MESSAGE
    predictions = _predict(rows=(early, late))
    assert tuple(item.target_timestamp for item in predictions) == (_ts(1), _ts(3))


@pytest.mark.parametrize("value", NON_FINITE_VALUES)
def test_non_finite_lag_24h_coefficient_fails_closed(value: str) -> None:
    with pytest.raises(InvalidRequestError) as captured:
        _predict(fit=_fit(lag_24h_coefficient=value), rows=(_row(day=1),))
    assert captured.value.message == _NON_FINITE_FIT_MESSAGE


@pytest.mark.parametrize("value", NON_FINITE_VALUES)
def test_non_finite_lag_168h_coefficient_fails_closed(value: str) -> None:
    with pytest.raises(InvalidRequestError) as captured:
        _predict(fit=_fit(lag_168h_coefficient=value), rows=(_row(day=1),))
    assert captured.value.message == _NON_FINITE_FIT_MESSAGE


@pytest.mark.parametrize("value", NON_FINITE_VALUES)
def test_non_finite_intercept_fails_closed(value: str) -> None:
    with pytest.raises(InvalidRequestError) as captured:
        _predict(fit=_fit(intercept=value), rows=(_row(day=1),))
    assert captured.value.message == _NON_FINITE_FIT_MESSAGE


@pytest.mark.parametrize("value", NON_FINITE_VALUES)
def test_non_finite_lag_24h_feature_fails_closed(value: str) -> None:
    with pytest.raises(InvalidRequestError) as captured:
        _predict(rows=(_row(day=1, lag_24h=value),))
    assert captured.value.message == _NON_FINITE_INPUT_MESSAGE


@pytest.mark.parametrize("value", NON_FINITE_VALUES)
def test_non_finite_lag_168h_feature_fails_closed(value: str) -> None:
    with pytest.raises(InvalidRequestError) as captured:
        _predict(rows=(_row(day=1, lag_168h=value),))
    assert captured.value.message == _NON_FINITE_INPUT_MESSAGE


@pytest.mark.parametrize("value", NON_FINITE_VALUES)
def test_non_finite_actual_target_fails_closed(value: str) -> None:
    with pytest.raises(InvalidRequestError) as captured:
        _predict(rows=(_row(day=1, target=value),))
    assert captured.value.message == _NON_FINITE_INPUT_MESSAGE


def test_decimal_overflow_is_translated_not_leaked() -> None:
    # The lag-168h product leaves the default Decimal exponent range, so the
    # Decimal Overflow signal must become the sanitized failure family.
    with pytest.raises(InvalidRequestError) as captured:
        _predict(
            fit=_fit(lag_24h_coefficient="1", lag_168h_coefficient="1E+600000", intercept="0"),
            rows=(_row(day=1, lag_24h="1", lag_168h="1E+600000"),),
        )
    assert captured.value.message == _NON_FINITE_PREDICTION_MESSAGE
    assert isinstance(captured.value.__cause__, Overflow)
    assert "E+600000" not in str(captured.value)


def test_non_finite_computed_prediction_fails_closed_when_signals_are_untrapped() -> None:
    # With Decimal traps disabled the overflowing product silently becomes
    # Infinity; the predictor must still refuse to return it.
    with localcontext() as context:
        context.traps[Overflow] = False
        context.traps[InvalidOperation] = False
        with pytest.raises(InvalidRequestError) as captured:
            _predict(
                fit=_fit(lag_24h_coefficient="1E+600000", lag_168h_coefficient="0"),
                rows=(_row(day=1, lag_24h="1E+600000", lag_168h="0"),),
            )
    assert captured.value.message == _NON_FINITE_PREDICTION_MESSAGE


def test_later_invalid_row_returns_no_partial_predictions() -> None:
    rows = (
        _row(day=1, lag_24h="1"),
        _row(day=2, lag_24h="2"),
        _row(day=3, lag_168h="NaN"),
    )
    result: tuple[DAMPriceLag24h168hLinearRegressionPrediction, ...] | None = None
    with pytest.raises(InvalidRequestError) as captured:
        result = _predict(rows=rows)
    assert captured.value.message == _NON_FINITE_INPUT_MESSAGE
    assert result is None


def test_later_overflowing_row_returns_no_partial_predictions() -> None:
    rows = (
        _row(day=1, lag_24h="1"),
        _row(day=2, lag_24h="1E+600000"),
    )
    result: tuple[DAMPriceLag24h168hLinearRegressionPrediction, ...] | None = None
    with pytest.raises(InvalidRequestError) as captured:
        result = _predict(fit=_fit(lag_24h_coefficient="1E+600000"), rows=rows)
    assert captured.value.message == _NON_FINITE_PREDICTION_MESSAGE
    assert result is None


def test_currency_only_qualifies_identity_not_arithmetic() -> None:
    amd_rows = (_row(day=1, lag_24h="3", lag_168h="4", target="19", currency="AMD"),)
    eur_rows = (_row(day=1, lag_24h="3", lag_168h="4", target="19", currency="EUR"),)
    amd_prediction = _predict(rows=amd_rows)[0]
    eur_prediction = _predict(rows=eur_rows)[0]
    assert amd_prediction.predicted_amount_per_mwh == eur_prediction.predicted_amount_per_mwh
    assert amd_prediction.predicted_amount_per_mwh == Decimal("19")
    assert amd_prediction.currency == "AMD"
    assert eur_prediction.currency == "EUR"
    assert amd_prediction.actual_amount_per_mwh == eur_prediction.actual_amount_per_mwh


def test_prediction_is_not_rounded_or_quantized() -> None:
    third = "0.3333333333333333333333333333"
    prediction = _predict(
        fit=_fit(lag_24h_coefficient=third, lag_168h_coefficient=third, intercept="0"),
        rows=(_row(day=1, lag_24h="3", lag_168h="1"),),
    )[0]
    expected = Decimal(third) * Decimal("3") + Decimal(third) * Decimal("1") + Decimal("0")
    assert prediction.predicted_amount_per_mwh == expected
    assert prediction.predicted_amount_per_mwh != Decimal("1.33")
    assert len(prediction.predicted_amount_per_mwh.as_tuple().digits) > 6


def test_input_fit_is_not_mutated() -> None:
    fit = _fit(lag_24h_coefficient="2", lag_168h_coefficient="3", intercept="1")
    _predict(fit=fit, rows=(_row(day=1, lag_24h="3"),))
    assert fit == _fit(lag_24h_coefficient="2", lag_168h_coefficient="3", intercept="1")


def test_input_rows_are_not_mutated() -> None:
    first = _row(day=1, lag_24h="1", lag_168h="2", target="3")
    second = _row(day=2, lag_24h="2", lag_168h="3", target="5")
    rows = (first, second)
    _predict(rows=rows)
    assert rows == (first, second)
    assert rows[0] is first
    assert rows[1] is second
    assert first == _row(day=1, lag_24h="1", lag_168h="2", target="3")
    assert second == _row(day=2, lag_24h="2", lag_168h="3", target="5")


def test_repeated_equal_input_is_value_equivalent() -> None:
    rows = (_row(day=1, lag_24h="1"), _row(day=2, lag_24h="2"))
    assert _predict(rows=rows) == _predict(rows=rows)
    assert _predict(fit=_fit(), rows=rows) == _predict(fit=_fit(), rows=tuple(rows))


def test_result_contract_is_frozen_slotted_and_exactly_five_fields() -> None:
    result_fields = fields(DAMPriceLag24h168hLinearRegressionPrediction)
    names = tuple(item.name for item in result_fields)
    assert names == FIVE_FIELDS
    assert DAMPriceLag24h168hLinearRegressionPrediction.__slots__ == names
    for item in result_fields:
        assert item.default is MISSING
        assert item.default_factory is MISSING
    prediction = _predict(rows=(_row(day=1),))[0]
    with pytest.raises(FrozenInstanceError):
        prediction.predicted_amount_per_mwh = Decimal("0")  # type: ignore[misc]


def test_result_exposes_no_extra_identity_metric_or_model_metadata() -> None:
    names = {item.name for item in fields(DAMPriceLag24h168hLinearRegressionPrediction)}
    forbidden = {
        "forecast_run_id",
        "generated_at",
        "model_name",
        "provider",
        "residual",
        "error",
        "row_index",
        "confidence_interval",
        "metadata",
        "lag_24h_amount_per_mwh",
        "lag_168h_amount_per_mwh",
        "lag_24h_coefficient",
        "lag_168h_coefficient",
        "intercept_amount_per_mwh",
        "mae",
        "mae_amount_per_mwh",
        "case_count",
    }
    assert forbidden.isdisjoint(names)
    prediction = _predict(rows=(_row(day=1),))[0]
    assert not hasattr(prediction, "__dict__")


def test_prediction_values_are_decimal_not_float() -> None:
    prediction = _predict(rows=(_row(day=1, lag_24h="3", lag_168h="4"),))[0]
    assert type(prediction.predicted_amount_per_mwh) is Decimal
    assert type(prediction.actual_amount_per_mwh) is Decimal


def test_predictor_is_synchronous_keyword_only_without_defaults() -> None:
    assert not inspect.iscoroutinefunction(predict_dam_price_lag_24h_168h_linear_regression)
    parameters = inspect.signature(predict_dam_price_lag_24h_168h_linear_regression).parameters
    assert tuple(parameters) == ("fit", "evaluation_rows")
    for parameter in parameters.values():
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty
    with pytest.raises(TypeError):
        predict_dam_price_lag_24h_168h_linear_regression(  # type: ignore[misc]
            _fit(),
            (_row(day=1),),
        )


def test_result_is_a_plain_prediction_tuple_without_metric_or_live_forecast() -> None:
    predictions = _predict(rows=(_row(day=1), _row(day=2)))
    assert type(predictions) is tuple
    for prediction in predictions:
        assert type(prediction) is DAMPriceLag24h168hLinearRegressionPrediction
        assert type(prediction).__name__ != "PriceForecastPoint"
        assert not hasattr(prediction, "price")
        assert not hasattr(prediction, "forecast_run_id")
        assert not hasattr(prediction, "mae_amount_per_mwh")
