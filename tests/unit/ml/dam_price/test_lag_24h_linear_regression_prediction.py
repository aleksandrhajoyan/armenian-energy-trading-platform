"""Lag-24h ordinary-least-squares DAM Price evaluation prediction."""

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
from energy_trading.ml.dam_price.lag_24h_linear_regression_prediction import (
    DAMPriceLag24hLinearRegressionPrediction,
    predict_dam_price_lag_24h_linear_regression,
)

_EMPTY_ROWS_MESSAGE = (
    "DAM Price lag-24h linear regression prediction requires at least one evaluation row."
)
_MIXED_MARKET_MESSAGE = (
    "DAM Price lag-24h linear regression prediction requires rows from exactly one market."
)
_MIXED_CURRENCY_MESSAGE = (
    "DAM Price lag-24h linear regression prediction requires rows in exactly one currency."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "DAM Price lag-24h linear regression prediction requires unique target timestamps."
)
_OUT_OF_ORDER_MESSAGE = (
    "DAM Price lag-24h linear regression prediction requires strictly increasing target timestamps."
)
_NON_FINITE_FIT_MESSAGE = (
    "DAM Price lag-24h linear regression prediction requires finite fitted parameters."
)
_NON_FINITE_INPUT_MESSAGE = (
    "DAM Price lag-24h linear regression prediction requires finite feature and target values."
)
_NON_FINITE_PREDICTION_MESSAGE = (
    "DAM Price lag-24h linear regression prediction requires finite predicted values."
)

FIVE_FIELDS = (
    "market_id",
    "currency",
    "target_timestamp",
    "predicted_amount_per_mwh",
    "actual_amount_per_mwh",
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


def _fit(*, slope: str = "2", intercept: str = "1") -> DAMPriceLag24hLinearRegressionFit:
    return DAMPriceLag24hLinearRegressionFit(
        slope=Decimal(slope),
        intercept_amount_per_mwh=Decimal(intercept),
    )


def _predict(
    *,
    fit: DAMPriceLag24hLinearRegressionFit | None = None,
    rows: tuple[DAMPriceLag24hFeatureRow, ...],
) -> tuple[DAMPriceLag24hLinearRegressionPrediction, ...]:
    return predict_dam_price_lag_24h_linear_regression(
        fit=_fit() if fit is None else fit,
        evaluation_rows=rows,
    )


def test_exact_decimal_prediction_formula() -> None:
    predictions = _predict(
        fit=_fit(slope="2", intercept="1"),
        rows=(_row(day=1, lag="3", target="7"),),
    )
    assert predictions[0].predicted_amount_per_mwh == Decimal("2") * Decimal("3") + Decimal("1")
    assert predictions[0].predicted_amount_per_mwh == Decimal("7")


def test_parameters_from_the_published_fitter_drive_the_prediction() -> None:
    training_rows = (_row(day=1, lag="1", target="3"), _row(day=2, lag="2", target="5"))
    fit = fit_dam_price_lag_24h_linear_regression(training_rows=training_rows)
    predictions = predict_dam_price_lag_24h_linear_regression(
        fit=fit,
        evaluation_rows=(_row(day=3, lag="4", target="9"),),
    )
    assert fit.slope == Decimal("2")
    assert fit.intercept_amount_per_mwh == Decimal("1")
    assert predictions[0].predicted_amount_per_mwh == Decimal("9")


def test_multiple_rows_produce_predictions_in_supplied_order() -> None:
    rows = (
        _row(day=1, lag="1", target="3"),
        _row(day=2, lag="2", target="5"),
        _row(day=3, lag="3", target="7"),
    )
    predictions = _predict(rows=rows)
    assert isinstance(predictions, tuple)
    assert len(predictions) == 3
    assert tuple(item.target_timestamp for item in predictions) == (
        _ts(1),
        _ts(2),
        _ts(3),
    )
    assert tuple(item.predicted_amount_per_mwh for item in predictions) == (
        Decimal("3"),
        Decimal("5"),
        Decimal("7"),
    )


def test_identity_and_actual_values_are_preserved_exactly() -> None:
    row = _row(day=4, lag="5", target="11", market_id="market-1", currency="AMD")
    prediction = _predict(rows=(row,))[0]
    assert prediction.market_id == row.market_id
    assert prediction.currency == row.currency
    assert prediction.target_timestamp == row.target_timestamp
    assert prediction.actual_amount_per_mwh == row.target_amount_per_mwh
    assert prediction.target_timestamp is row.target_timestamp
    assert prediction.actual_amount_per_mwh is row.target_amount_per_mwh


def test_positive_prediction_is_valid() -> None:
    prediction = _predict(fit=_fit(slope="3", intercept="4"), rows=(_row(day=1, lag="5"),))[0]
    assert prediction.predicted_amount_per_mwh == Decimal("19")
    assert prediction.predicted_amount_per_mwh > 0


def test_negative_prediction_is_preserved_and_not_clamped() -> None:
    prediction = _predict(
        fit=_fit(slope="-2", intercept="1"),
        rows=(_row(day=1, lag="3", target="-5"),),
    )[0]
    assert prediction.predicted_amount_per_mwh == Decimal("-5")
    assert prediction.predicted_amount_per_mwh < 0
    assert prediction.predicted_amount_per_mwh != Decimal("0")


def test_zero_prediction_is_valid() -> None:
    prediction = _predict(
        fit=_fit(slope="0", intercept="0"),
        rows=(_row(day=1, lag="9", target="0"),),
    )[0]
    assert prediction.predicted_amount_per_mwh == Decimal("0")


def test_negative_actual_price_remains_valid() -> None:
    prediction = _predict(rows=(_row(day=1, lag="2", target="-17"),))[0]
    assert prediction.actual_amount_per_mwh == Decimal("-17")


def test_negative_lag_feature_remains_valid() -> None:
    prediction = _predict(fit=_fit(slope="2", intercept="0"), rows=(_row(day=1, lag="-4"),))[0]
    assert prediction.predicted_amount_per_mwh == Decimal("-8")
    assert prediction.predicted_amount_per_mwh < 0


def test_negative_fitted_slope_is_valid() -> None:
    prediction = _predict(fit=_fit(slope="-1.5", intercept="0"), rows=(_row(day=1, lag="2"),))[0]
    assert prediction.predicted_amount_per_mwh == Decimal("-3.0")


def test_negative_fitted_intercept_is_valid() -> None:
    prediction = _predict(
        fit=_fit(slope="1", intercept="-12.5"),
        rows=(_row(day=1, lag="-2"),),
    )[0]
    assert prediction.predicted_amount_per_mwh == Decimal("-14.5")
    assert prediction.predicted_amount_per_mwh < 0


def test_empty_evaluation_rows_fail_closed() -> None:
    with pytest.raises(InvalidRequestError) as captured:
        _predict(rows=())
    assert captured.value.message == _EMPTY_ROWS_MESSAGE


def test_mixed_markets_fail_closed_without_leaking_ids() -> None:
    rows = (
        _row(day=1, market_id="market-alpha"),
        _row(day=2, lag="2", market_id="market-beta"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _predict(rows=rows)
    assert captured.value.message == _MIXED_MARKET_MESSAGE
    assert "market-alpha" not in captured.value.message
    assert "market-beta" not in captured.value.message


def test_mixed_currencies_fail_closed_without_leaking_codes() -> None:
    rows = (
        _row(day=1, currency="AMD"),
        _row(day=2, lag="2", currency="EUR"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _predict(rows=rows)
    assert captured.value.message == _MIXED_CURRENCY_MESSAGE
    assert "AMD" not in captured.value.message
    assert "EUR" not in captured.value.message


def test_duplicate_target_timestamps_fail_closed() -> None:
    rows = (_row(day=2, lag="1"), _row(day=2, lag="2"))
    with pytest.raises(InvalidRequestError) as captured:
        _predict(rows=rows)
    assert captured.value.message == _DUPLICATE_TIMESTAMP_MESSAGE


def test_out_of_order_target_timestamps_fail_closed() -> None:
    rows = (_row(day=3), _row(day=1, lag="2"))
    with pytest.raises(InvalidRequestError) as captured:
        _predict(rows=rows)
    assert captured.value.message == _OUT_OF_ORDER_MESSAGE


def test_out_of_order_input_is_not_silently_sorted() -> None:
    late = _row(day=3, lag="1", target="1")
    early = _row(day=1, lag="2", target="2")
    with pytest.raises(InvalidRequestError) as captured:
        _predict(rows=(late, early))
    assert captured.value.message == _OUT_OF_ORDER_MESSAGE
    predictions = _predict(rows=(early, late))
    assert tuple(item.target_timestamp for item in predictions) == (_ts(1), _ts(3))


def test_correct_chronological_order_succeeds() -> None:
    rows = (_row(day=1), _row(day=2, lag="2"), _row(day=4, lag="3"))
    predictions = _predict(rows=rows)
    assert len(predictions) == 3


@pytest.mark.parametrize("slope", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_slope_fails_closed(slope: str) -> None:
    with pytest.raises(InvalidRequestError) as captured:
        _predict(fit=_fit(slope=slope), rows=(_row(day=1),))
    assert captured.value.message == _NON_FINITE_FIT_MESSAGE


@pytest.mark.parametrize("intercept", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_intercept_fails_closed(intercept: str) -> None:
    with pytest.raises(InvalidRequestError) as captured:
        _predict(fit=_fit(intercept=intercept), rows=(_row(day=1),))
    assert captured.value.message == _NON_FINITE_FIT_MESSAGE


@pytest.mark.parametrize("lag", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_lag_feature_fails_closed(lag: str) -> None:
    row = DAMPriceLag24hFeatureRow(
        market_id="market-1",
        currency="AMD",
        target_timestamp=_ts(1),
        lag_24h_amount_per_mwh=Decimal(lag),
        target_amount_per_mwh=Decimal("1"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _predict(rows=(row,))
    assert captured.value.message == _NON_FINITE_INPUT_MESSAGE


@pytest.mark.parametrize("target", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_actual_target_fails_closed(target: str) -> None:
    row = DAMPriceLag24hFeatureRow(
        market_id="market-1",
        currency="AMD",
        target_timestamp=_ts(1),
        lag_24h_amount_per_mwh=Decimal("1"),
        target_amount_per_mwh=Decimal(target),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _predict(rows=(row,))
    assert captured.value.message == _NON_FINITE_INPUT_MESSAGE


def test_extreme_decimal_arithmetic_is_translated_not_leaked() -> None:
    # Multiplying this magnitude leaves the default Decimal exponent range, so
    # the prediction cannot be finite. The predictor must translate the Decimal
    # arithmetic signal into the sanitized failure family rather than leaking a
    # raw Decimal exception or returning a non-finite value.
    with pytest.raises(InvalidRequestError) as captured:
        _predict(
            fit=_fit(slope="1E+600000", intercept="0"),
            rows=(_row(day=1, lag="1E+600000"),),
        )
    assert captured.value.message == _NON_FINITE_PREDICTION_MESSAGE


def test_currency_only_qualifies_identity_not_arithmetic() -> None:
    # The numeric calculation must not inspect currency: equivalent cohorts in
    # different valid currencies yield equivalent numeric predictions while
    # each output preserves its own supplied currency.
    amd_rows = (_row(day=1, lag="3", target="7", currency="AMD"),)
    eur_rows = (_row(day=1, lag="3", target="7", currency="EUR"),)
    amd_prediction = _predict(fit=_fit(slope="2", intercept="1"), rows=amd_rows)[0]
    eur_prediction = _predict(fit=_fit(slope="2", intercept="1"), rows=eur_rows)[0]
    assert amd_prediction.predicted_amount_per_mwh == eur_prediction.predicted_amount_per_mwh
    assert amd_prediction.currency == "AMD"
    assert eur_prediction.currency == "EUR"
    assert amd_prediction.actual_amount_per_mwh == eur_prediction.actual_amount_per_mwh


def test_input_fit_is_not_mutated() -> None:
    fit = _fit(slope="2", intercept="1")
    _predict(fit=fit, rows=(_row(day=1, lag="3"),))
    assert fit.slope == Decimal("2")
    assert fit.intercept_amount_per_mwh == Decimal("1")


def test_input_rows_are_not_mutated() -> None:
    first = _row(day=1, lag="1", target="3")
    second = _row(day=2, lag="2", target="5")
    rows = (first, second)
    _predict(rows=rows)
    assert rows == (first, second)
    assert first.lag_24h_amount_per_mwh == Decimal("1")
    assert second.target_amount_per_mwh == Decimal("5")


def test_repeated_equal_input_is_value_equivalent() -> None:
    rows = (_row(day=1, lag="1", target="3"), _row(day=2, lag="2", target="5"))
    fit = _fit()
    assert _predict(fit=fit, rows=rows) == _predict(fit=fit, rows=rows)


def test_result_contract_is_frozen_slotted_and_exactly_five_fields() -> None:
    names = tuple(item.name for item in fields(DAMPriceLag24hLinearRegressionPrediction))
    assert names == FIVE_FIELDS
    assert DAMPriceLag24hLinearRegressionPrediction.__slots__ == names
    prediction = _predict(rows=(_row(day=1),))[0]
    with pytest.raises(FrozenInstanceError):
        prediction.predicted_amount_per_mwh = Decimal("0")  # type: ignore[misc]


def test_result_exposes_no_extra_identity_metric_or_model_metadata() -> None:
    names = {item.name for item in fields(DAMPriceLag24hLinearRegressionPrediction)}
    assert names == set(FIVE_FIELDS)
    forbidden = {
        "forecast_run_id",
        "generated_at",
        "model_name",
        "model_version",
        "provider",
        "residual",
        "error",
        "row_index",
        "confidence_interval",
        "metadata",
        "feature_vector",
        "prediction_timestamp",
        "mae",
        "mse",
        "rmse",
        "r2",
    }
    assert forbidden.isdisjoint(names)


def test_prediction_values_are_decimal_not_float() -> None:
    prediction = _predict(rows=(_row(day=1, lag="3", target="7"),))[0]
    assert isinstance(prediction.predicted_amount_per_mwh, Decimal)
    assert isinstance(prediction.actual_amount_per_mwh, Decimal)
    assert not isinstance(prediction.predicted_amount_per_mwh, float)
    assert not isinstance(prediction.actual_amount_per_mwh, float)


def test_predictor_is_synchronous_and_keyword_only() -> None:
    assert not inspect.iscoroutinefunction(predict_dam_price_lag_24h_linear_regression)
    parameters = inspect.signature(predict_dam_price_lag_24h_linear_regression).parameters
    assert tuple(parameters) == ("fit", "evaluation_rows")
    assert parameters["fit"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["evaluation_rows"].kind is inspect.Parameter.KEYWORD_ONLY


def test_prediction_is_not_rounded_or_quantized() -> None:
    # 1/3 does not terminate under the default context; the predictor must use
    # the raw Decimal product without rounding or quantization.
    prediction = _predict(
        fit=_fit(slope="0.3333333333333333333333333333", intercept="0"),
        rows=(_row(day=1, lag="3"),),
    )[0]
    assert prediction.predicted_amount_per_mwh == Decimal(
        "0.3333333333333333333333333333"
    ) * Decimal("3")
