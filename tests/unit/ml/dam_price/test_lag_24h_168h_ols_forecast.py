"""Lag-24h plus lag-168h OLS DAM Price Forecast candidate adapter."""

from __future__ import annotations

import copy
import inspect
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, Overflow, localcontext

import pytest
from tests.unit.domain._factories import utc

import energy_trading.ml.dam_price.lag_24h_168h_ols_forecast as forecast_module
from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.ports.dam_price_forecast_model import (
    DAMPriceForecastModelPort,
    DAMPriceForecastModelRequest,
)
from energy_trading.domain.models.forecasting import PriceForecastPoint
from energy_trading.domain.models.observations import MarketPriceRecord
from energy_trading.domain.value_objects.money import EnergyPrice
from energy_trading.ml.dam_price.lag_24h_168h_linear_regression import (
    DAMPriceLag24h168hLinearRegressionFit,
)
from energy_trading.ml.dam_price.lag_24h_168h_ols_forecast import (
    Lag24h168hOLSDAMPriceForecastModel,
)

_MISSING_LAG_24H_MESSAGE = (
    "DAM Price trained OLS live inference requires exactly one history "
    "observation at the 24-hour lag."
)
_MISSING_LAG_168H_MESSAGE = (
    "DAM Price trained OLS live inference requires exactly one history "
    "observation at the 168-hour lag."
)
_DUPLICATE_LAG_24H_MESSAGE = (
    "DAM Price trained OLS live inference requires a unique 24-hour lag observation."
)
_DUPLICATE_LAG_168H_MESSAGE = (
    "DAM Price trained OLS live inference requires a unique 168-hour lag observation."
)
_NON_FINITE_FIT_MESSAGE = (
    "DAM Price trained OLS live inference requires finite fitted coefficients and intercept."
)
_NON_FINITE_PREDICTION_MESSAGE = (
    "DAM Price trained OLS live inference requires a finite forecast price."
)
_LAG_24H = timedelta(hours=24)
_LAG_168H = timedelta(hours=168)
_TARGET = utc(day=10, hour=16)
NON_FINITE_VALUES = ("NaN", "Infinity", "-Infinity")
FIT_FIELDS = ("lag_24h_coefficient", "lag_168h_coefficient", "intercept_amount_per_mwh")


def _fit(
    *,
    lag_24h_coefficient: str = "0.5",
    lag_168h_coefficient: str = "0.25",
    intercept: str = "10",
) -> DAMPriceLag24h168hLinearRegressionFit:
    return DAMPriceLag24h168hLinearRegressionFit(
        lag_24h_coefficient=Decimal(lag_24h_coefficient),
        lag_168h_coefficient=Decimal(lag_168h_coefficient),
        intercept_amount_per_mwh=Decimal(intercept),
    )


def _market(
    *,
    timestamp: datetime,
    amount: str,
    currency: str = "AMD",
    market_id: str = "market-1",
) -> MarketPriceRecord:
    return MarketPriceRecord(
        market_id=market_id,
        timestamp=timestamp,
        price=EnergyPrice(amount_per_mwh=Decimal(amount), currency=currency),
    )


def _lags(
    target: datetime,
    *,
    lag_24h: str = "40",
    lag_168h: str = "80",
    currency: str = "AMD",
) -> tuple[MarketPriceRecord, ...]:
    return (
        _market(timestamp=target - _LAG_168H, amount=lag_168h, currency=currency),
        _market(timestamp=target - _LAG_24H, amount=lag_24h, currency=currency),
    )


def _request(**overrides: object) -> DAMPriceForecastModelRequest:
    values: dict[str, object] = {
        "forecast_run_id": "run-1",
        "generated_at": utc(day=10, hour=9),
        "market_id": "market-1",
        "currency": "AMD",
        "history": _lags(_TARGET),
        "target_timestamps": (_TARGET,),
    }
    values.update(overrides)
    return DAMPriceForecastModelRequest(**values)  # type: ignore[arg-type]


def _model(**fit_overrides: str) -> Lag24h168hOLSDAMPriceForecastModel:
    return Lag24h168hOLSDAMPriceForecastModel(fit=_fit(**fit_overrides))


def _as_model_port(model: Lag24h168hOLSDAMPriceForecastModel) -> DAMPriceForecastModelPort:
    return model


async def _single_amount(
    model: Lag24h168hOLSDAMPriceForecastModel,
    *,
    lag_24h: str,
    lag_168h: str,
) -> Decimal:
    result = await model.forecast(
        request=_request(history=_lags(_TARGET, lag_24h=lag_24h, lag_168h=lag_168h))
    )
    assert len(result) == 1
    return result[0].price.amount_per_mwh


# --- structural / live success -------------------------------------------------


def test_structural_port_conformance_without_inheritance() -> None:
    model = _model()
    port = _as_model_port(model)
    assert port is model
    assert DAMPriceForecastModelPort not in Lag24h168hOLSDAMPriceForecastModel.__mro__
    assert Lag24h168hOLSDAMPriceForecastModel.__bases__ == (object,)
    assert inspect.iscoroutinefunction(port.forecast)


def test_constructor_is_keyword_only_and_requires_fit() -> None:
    with pytest.raises(TypeError):
        Lag24h168hOLSDAMPriceForecastModel(_fit())  # type: ignore[misc]
    with pytest.raises(TypeError):
        Lag24h168hOLSDAMPriceForecastModel()  # type: ignore[call-arg]


async def test_exact_two_feature_arithmetic() -> None:
    # 0.5 * 40 + 0.25 * 80 + 10 = 50
    amount = await _single_amount(_model(), lag_24h="40", lag_168h="80")
    assert amount == Decimal("50")
    assert isinstance(amount, Decimal)


async def test_both_coefficients_and_intercept_participate() -> None:
    base = await _single_amount(
        _model(lag_24h_coefficient="2", lag_168h_coefficient="3", intercept="5"),
        lag_24h="7",
        lag_168h="11",
    )
    assert base == Decimal("2") * 7 + Decimal("3") * 11 + 5
    no_24h = await _single_amount(
        _model(lag_24h_coefficient="0", lag_168h_coefficient="3", intercept="5"),
        lag_24h="7",
        lag_168h="11",
    )
    assert no_24h == Decimal("38")
    no_168h = await _single_amount(
        _model(lag_24h_coefficient="2", lag_168h_coefficient="0", intercept="5"),
        lag_24h="7",
        lag_168h="11",
    )
    assert no_168h == Decimal("19")
    no_intercept = await _single_amount(
        _model(lag_24h_coefficient="2", lag_168h_coefficient="3", intercept="0"),
        lag_24h="7",
        lag_168h="11",
    )
    assert no_intercept == Decimal("47")


async def test_changing_only_lag_24h_moves_result_by_lag_24h_coefficient() -> None:
    model = _model(lag_24h_coefficient="2", lag_168h_coefficient="3", intercept="5")
    first = await _single_amount(model, lag_24h="7", lag_168h="11")
    second = await _single_amount(model, lag_24h="8", lag_168h="11")
    assert second - first == Decimal("2")


async def test_changing_only_lag_168h_moves_result_by_lag_168h_coefficient() -> None:
    model = _model(lag_24h_coefficient="2", lag_168h_coefficient="3", intercept="5")
    first = await _single_amount(model, lag_24h="7", lag_168h="11")
    second = await _single_amount(model, lag_24h="7", lag_168h="12")
    assert second - first == Decimal("3")


async def test_lag_roles_are_not_swapped() -> None:
    model = _model(lag_24h_coefficient="2", lag_168h_coefficient="3", intercept="0")
    amount = await _single_amount(model, lag_24h="100", lag_168h="1")
    assert amount == Decimal("203")
    assert amount != Decimal("302")


async def test_exact_canonical_decimal_precision_is_preserved() -> None:
    model = _model(
        lag_24h_coefficient="0.123456789",
        lag_168h_coefficient="0.000000001",
        intercept="0.000000003",
    )
    amount = await _single_amount(model, lag_24h="10.5", lag_168h="3")
    # 0.123456789 * 10.5 + 0.000000001 * 3 + 0.000000003, exactly in Decimal.
    assert str(amount) == "1.2962962905"


async def test_positive_prediction() -> None:
    amount = await _single_amount(_model(), lag_24h="40", lag_168h="80")
    assert amount > 0


async def test_zero_prediction_is_valid() -> None:
    model = _model(lag_24h_coefficient="1", lag_168h_coefficient="1", intercept="-120")
    amount = await _single_amount(model, lag_24h="40", lag_168h="80")
    assert amount == Decimal("0")


async def test_negative_finite_prediction_is_preserved_not_clamped() -> None:
    model = _model(lag_24h_coefficient="1", lag_168h_coefficient="1", intercept="-200")
    amount = await _single_amount(model, lag_24h="40", lag_168h="80")
    assert amount == Decimal("-80")


async def test_negative_lag_prices_participate_signed() -> None:
    model = _model(lag_24h_coefficient="2", lag_168h_coefficient="3", intercept="1")
    amount = await _single_amount(model, lag_24h="-10", lag_168h="-5")
    assert amount == Decimal("-34")


# --- canonical output ----------------------------------------------------------


async def test_identity_fields_pass_through_unchanged() -> None:
    generated_at = utc(day=9, hour=7)
    request = _request(
        forecast_run_id="run-xyz",
        generated_at=generated_at,
        market_id="market-1",
    )
    result = await _model().forecast(request=request)
    assert len(result) == 1
    point = result[0]
    assert isinstance(point, PriceForecastPoint)
    assert point.forecast_run_id == "run-xyz"
    assert point.generated_at == generated_at
    assert point.market_id == "market-1"
    assert point.target_timestamp == _TARGET
    assert isinstance(point.price, EnergyPrice)


async def test_output_currency_is_request_currency() -> None:
    request = _request(currency="EUR", history=_lags(_TARGET, currency="EUR"))
    result = await _model().forecast(request=request)
    assert result[0].price.currency == "EUR"
    assert result[0].price == EnergyPrice(amount_per_mwh=Decimal("50"), currency="EUR")


async def test_output_timestamp_is_target_not_lag_timestamp() -> None:
    result = await _model().forecast(request=_request())
    assert result[0].target_timestamp == _TARGET
    assert result[0].target_timestamp not in {_TARGET - _LAG_24H, _TARGET - _LAG_168H}


async def test_multiple_targets_preserve_request_order() -> None:
    first = utc(day=10, hour=10)
    second = utc(day=10, hour=11)
    third = utc(day=10, hour=12)
    history = (
        *_lags(first, lag_24h="1", lag_168h="2"),
        *_lags(second, lag_24h="3", lag_168h="4"),
        *_lags(third, lag_24h="5", lag_168h="6"),
    )
    model = _model(lag_24h_coefficient="1", lag_168h_coefficient="10", intercept="0")
    result = await model.forecast(
        request=_request(history=history, target_timestamps=(first, second, third))
    )
    assert tuple(point.target_timestamp for point in result) == (first, second, third)
    assert tuple(point.price.amount_per_mwh for point in result) == (
        Decimal("21"),
        Decimal("43"),
        Decimal("65"),
    )


async def test_out_of_order_targets_remain_in_request_order() -> None:
    early = utc(day=10, hour=10)
    late = utc(day=10, hour=12)
    history = (*_lags(late, lag_24h="5"), *_lags(early, lag_24h="1"))
    result = await _model().forecast(
        request=_request(history=history, target_timestamps=(late, early))
    )
    assert tuple(point.target_timestamp for point in result) == (late, early)


async def test_duplicate_requested_targets_are_not_deduplicated() -> None:
    result = await _model().forecast(request=_request(target_timestamps=(_TARGET, _TARGET)))
    assert len(result) == 2
    assert result[0] == result[1]
    assert result[0].target_timestamp == _TARGET


def test_empty_targets_are_rejected_by_existing_request_contract() -> None:
    # The published DAMPriceForecastModelRequest requires at least one target,
    # so the adapter never receives an empty target tuple.
    with pytest.raises(ValueError, match="target_timestamps"):
        _request(target_timestamps=())


# --- exact lag rules -----------------------------------------------------------


async def test_missing_lag_24h_fails_closed() -> None:
    history = (_market(timestamp=_TARGET - _LAG_168H, amount="80"),)
    with pytest.raises(InvalidRequestError) as captured:
        await _model().forecast(request=_request(history=history))
    assert captured.value.message == _MISSING_LAG_24H_MESSAGE


async def test_missing_lag_168h_fails_closed() -> None:
    history = (_market(timestamp=_TARGET - _LAG_24H, amount="40"),)
    with pytest.raises(InvalidRequestError) as captured:
        await _model().forecast(request=_request(history=history))
    assert captured.value.message == _MISSING_LAG_168H_MESSAGE


async def test_both_lags_missing_fails_closed() -> None:
    history = (_market(timestamp=_TARGET - timedelta(hours=1), amount="40"),)
    with pytest.raises(InvalidRequestError):
        await _model().forecast(request=_request(history=history))


async def test_empty_history_with_requested_target_fails_closed() -> None:
    with pytest.raises(InvalidRequestError) as captured:
        await _model().forecast(request=_request(history=()))
    assert captured.value.message == _MISSING_LAG_24H_MESSAGE


@pytest.mark.parametrize("offset", [timedelta(minutes=1), timedelta(minutes=-1)])
async def test_near_but_not_exact_lag_24h_is_rejected(offset: timedelta) -> None:
    history = (
        _market(timestamp=_TARGET - _LAG_168H, amount="80"),
        _market(timestamp=_TARGET - _LAG_24H + offset, amount="40"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        await _model().forecast(request=_request(history=history))
    assert captured.value.message == _MISSING_LAG_24H_MESSAGE


@pytest.mark.parametrize("offset", [timedelta(minutes=1), timedelta(minutes=-1)])
async def test_near_but_not_exact_lag_168h_is_rejected(offset: timedelta) -> None:
    history = (
        _market(timestamp=_TARGET - _LAG_168H + offset, amount="80"),
        _market(timestamp=_TARGET - _LAG_24H, amount="40"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        await _model().forecast(request=_request(history=history))
    assert captured.value.message == _MISSING_LAG_168H_MESSAGE


@pytest.mark.parametrize("hours", [167, 169])
async def test_adjacent_hours_are_not_substituted_for_lag_168h(hours: int) -> None:
    history = (
        _market(timestamp=_TARGET - timedelta(hours=hours), amount="80"),
        _market(timestamp=_TARGET - _LAG_24H, amount="40"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        await _model().forecast(request=_request(history=history))
    assert captured.value.message == _MISSING_LAG_168H_MESSAGE


@pytest.mark.parametrize("hours", [23, 25, 48])
async def test_adjacent_hours_are_not_substituted_for_lag_24h(hours: int) -> None:
    history = (
        _market(timestamp=_TARGET - _LAG_168H, amount="80"),
        _market(timestamp=_TARGET - timedelta(hours=hours), amount="40"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        await _model().forecast(request=_request(history=history))
    assert captured.value.message == _MISSING_LAG_24H_MESSAGE


async def test_weekly_calendar_lag_is_not_substituted_beyond_exact_elapsed_hours() -> None:
    # Two-week and calendar-day neighbours are not a substitute for exactly
    # 168 elapsed hours.
    history = (
        _market(timestamp=_TARGET - timedelta(hours=336), amount="80"),
        _market(timestamp=_TARGET - timedelta(days=7, hours=1), amount="80"),
        _market(timestamp=_TARGET - _LAG_24H, amount="40"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        await _model().forecast(request=_request(history=history))
    assert captured.value.message == _MISSING_LAG_168H_MESSAGE


async def test_duplicate_exact_lag_24h_fails_closed() -> None:
    history = (*_lags(_TARGET), _market(timestamp=_TARGET - _LAG_24H, amount="41"))
    with pytest.raises(InvalidRequestError) as captured:
        await _model().forecast(request=_request(history=history))
    assert captured.value.message == _DUPLICATE_LAG_24H_MESSAGE


async def test_duplicate_exact_lag_168h_fails_closed() -> None:
    history = (*_lags(_TARGET), _market(timestamp=_TARGET - _LAG_168H, amount="81"))
    with pytest.raises(InvalidRequestError) as captured:
        await _model().forecast(request=_request(history=history))
    assert captured.value.message == _DUPLICATE_LAG_168H_MESSAGE


async def test_later_target_failure_returns_no_partial_tuple() -> None:
    good = utc(day=10, hour=10)
    bad = utc(day=10, hour=11)
    result: tuple[PriceForecastPoint, ...] | None = None
    with pytest.raises(InvalidRequestError):
        result = await _model().forecast(
            request=_request(history=_lags(good), target_timestamps=(good, bad))
        )
    assert result is None


async def test_irrelevant_and_intervening_history_is_ignored() -> None:
    history = (
        _market(timestamp=_TARGET - timedelta(hours=1), amount="999"),
        _market(timestamp=_TARGET - timedelta(hours=100), amount="-999"),
        *_lags(_TARGET),
        _market(timestamp=_TARGET + timedelta(hours=24), amount="777"),
        _market(timestamp=_TARGET, amount="555"),
    )
    amount = (await _model().forecast(request=_request(history=history)))[0].price.amount_per_mwh
    assert amount == Decimal("50")


async def test_unsorted_history_is_accepted() -> None:
    history = tuple(reversed(_lags(_TARGET)))
    amount = (await _model().forecast(request=_request(history=history)))[0].price.amount_per_mwh
    assert amount == Decimal("50")


# --- numerical failure ---------------------------------------------------------


@pytest.mark.parametrize("field", FIT_FIELDS)
@pytest.mark.parametrize("value", NON_FINITE_VALUES)
def test_forged_non_finite_fit_parameter_is_rejected_at_construction(
    field: str, value: str
) -> None:
    fit = _fit()
    forged = copy.copy(fit)
    object.__setattr__(forged, field, Decimal(value))
    with pytest.raises(InvalidRequestError) as captured:
        Lag24h168hOLSDAMPriceForecastModel(fit=forged)
    assert captured.value.message == _NON_FINITE_FIT_MESSAGE
    assert value not in str(captured.value)


async def test_decimal_overflow_is_translated_not_leaked() -> None:
    model = _model(lag_24h_coefficient="1", lag_168h_coefficient="1E+600000", intercept="0")
    with pytest.raises(InvalidRequestError) as captured:
        await model.forecast(
            request=_request(history=_lags(_TARGET, lag_24h="1", lag_168h="1E+600000"))
        )
    assert captured.value.message == _NON_FINITE_PREDICTION_MESSAGE
    assert isinstance(captured.value.__cause__, Overflow)
    assert "E+600000" not in str(captured.value)


async def test_non_finite_raw_prediction_is_rejected_when_signals_are_untrapped() -> None:
    with localcontext() as context:
        context.traps[Overflow] = False
        context.traps[InvalidOperation] = False
        model = _model(lag_24h_coefficient="1E+600000", lag_168h_coefficient="0", intercept="0")
        request = _request(history=_lags(_TARGET, lag_24h="1E+600000", lag_168h="0"))
        with pytest.raises(InvalidRequestError) as captured:
            await model.forecast(request=request)
    assert captured.value.message == _NON_FINITE_PREDICTION_MESSAGE


def test_error_messages_do_not_leak_identity_or_values() -> None:
    messages = (
        _MISSING_LAG_24H_MESSAGE,
        _MISSING_LAG_168H_MESSAGE,
        _DUPLICATE_LAG_24H_MESSAGE,
        _DUPLICATE_LAG_168H_MESSAGE,
        _NON_FINITE_FIT_MESSAGE,
        _NON_FINITE_PREDICTION_MESSAGE,
    )
    for message in messages:
        for leaked in ("market-1", "run-1", "AMD", "2026", "{", "%"):
            assert leaked not in message


# --- determinism ---------------------------------------------------------------


async def test_request_history_and_fit_are_not_mutated() -> None:
    fit = _fit()
    fit_before = copy.deepcopy(fit)
    request = _request()
    request_before = copy.deepcopy(request)
    history_before = tuple(record.model_copy(deep=True) for record in request.history)
    model = Lag24h168hOLSDAMPriceForecastModel(fit=fit)
    await model.forecast(request=request)
    assert request == request_before
    assert request.history == history_before
    assert fit == fit_before


async def test_repeated_equivalent_calls_are_value_equal() -> None:
    model = _model()
    first = await model.forecast(request=_request())
    second = await model.forecast(request=_request())
    assert first == second


async def test_offline_artifacts_are_not_invoked(monkeypatch: pytest.MonkeyPatch) -> None:
    import energy_trading.ml.dam_price.lag_24h_168h_chronological_feature_split as split_module
    import energy_trading.ml.dam_price.lag_24h_168h_features as features_module
    import energy_trading.ml.dam_price.lag_24h_168h_linear_regression as fit_module
    import energy_trading.ml.dam_price.lag_24h_168h_linear_regression_evaluation as eval_module
    import energy_trading.ml.dam_price.lag_24h_168h_linear_regression_prediction as predict_module

    def _forbidden(*_args: object, **_kwargs: object) -> None:
        pytest.fail("offline artifact must not be invoked by the live adapter")

    monkeypatch.setattr(features_module, "build_dam_price_lag_24h_168h_feature_rows", _forbidden)
    monkeypatch.setattr(
        split_module,
        "split_dam_price_lag_24h_168h_feature_rows_chronologically",
        _forbidden,
    )
    monkeypatch.setattr(fit_module, "fit_dam_price_lag_24h_168h_linear_regression", _forbidden)
    monkeypatch.setattr(
        predict_module, "predict_dam_price_lag_24h_168h_linear_regression", _forbidden
    )
    monkeypatch.setattr(
        eval_module, "evaluate_dam_price_lag_24h_168h_linear_regression_mae", _forbidden
    )
    result = await _model().forecast(request=_request())
    assert result[0].price.amount_per_mwh == Decimal("50")
    module_names = set(vars(forecast_module))
    assert "fit_dam_price_lag_24h_168h_linear_regression" not in module_names
    assert "predict_dam_price_lag_24h_168h_linear_regression" not in module_names
    assert "PreviousDayPersistenceDAMPriceForecastModel" not in module_names
