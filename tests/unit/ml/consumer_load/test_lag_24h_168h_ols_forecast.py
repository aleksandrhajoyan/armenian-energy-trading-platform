"""Lag-24h plus lag-168h OLS Consumer Load Forecast candidate adapter."""

from __future__ import annotations

import inspect
from datetime import timedelta
from math import isfinite, nan

import pytest

from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.ports.consumer_load_forecast_model import (
    ConsumerLoadForecastModelPort,
    ConsumerLoadForecastModelRequest,
)
from energy_trading.domain.models.forecasting import LoadForecastPoint
from energy_trading.ml.consumer_load.lag_24h_168h_linear_regression import (
    ConsumerLoadLag24h168hLinearRegressionFit,
)
from energy_trading.ml.consumer_load.lag_24h_168h_ols_forecast import (
    Lag24h168hOLSConsumerLoadForecastModel,
)
from tests.unit.domain._factories import consumption, utc

_MISSING_LAG_24H_MESSAGE = (
    "Consumer Load trained OLS live inference requires exactly one history "
    "observation at the 24-hour lag."
)
_MISSING_LAG_168H_MESSAGE = (
    "Consumer Load trained OLS live inference requires exactly one history "
    "observation at the 168-hour lag."
)
_DUPLICATE_LAG_24H_MESSAGE = (
    "Consumer Load trained OLS live inference requires a unique 24-hour lag observation."
)
_DUPLICATE_LAG_168H_MESSAGE = (
    "Consumer Load trained OLS live inference requires a unique 168-hour lag observation."
)
_NON_FINITE_FIT_MESSAGE = (
    "Consumer Load trained OLS live inference requires finite fitted coefficients and intercept."
)
_NON_FINITE_PREDICTION_MESSAGE = (
    "Consumer Load trained OLS live inference requires a finite forecast value."
)
_NEGATIVE_PREDICTION_MESSAGE = (
    "Consumer Load trained OLS live inference requires a non-negative forecast value."
)
_LAG_24H = timedelta(hours=24)
_LAG_168H = timedelta(hours=168)


def _as_model_port(
    model: Lag24h168hOLSConsumerLoadForecastModel,
) -> ConsumerLoadForecastModelPort:
    return model


def _fit(**overrides: float) -> ConsumerLoadLag24h168hLinearRegressionFit:
    values: dict[str, float] = {
        "lag_24h_coefficient": 3.0,
        "lag_168h_coefficient": 5.0,
        "intercept_mw": 2.0,
    }
    values.update(overrides)
    return ConsumerLoadLag24h168hLinearRegressionFit(**values)


def _model(
    fit: ConsumerLoadLag24h168hLinearRegressionFit | None = None,
) -> Lag24h168hOLSConsumerLoadForecastModel:
    return Lag24h168hOLSConsumerLoadForecastModel(fit=_fit() if fit is None else fit)


def _history_for(
    target: object,
    *,
    lag_24h_mw: float = 1.0,
    lag_168h_mw: float = 2.0,
    consumer_id: str = "consumer-1",
) -> tuple[object, ...]:
    return (
        consumption(consumer_id=consumer_id, timestamp=target - _LAG_24H, value_mw=lag_24h_mw),
        consumption(consumer_id=consumer_id, timestamp=target - _LAG_168H, value_mw=lag_168h_mw),
    )


def _request(**overrides: object) -> ConsumerLoadForecastModelRequest:
    target = utc(hour=16)
    values: dict[str, object] = {
        "forecast_run_id": "run-1",
        "generated_at": utc(hour=9),
        "consumer_id": "consumer-1",
        "history": _history_for(target),
        "target_timestamps": (target,),
    }
    values.update(overrides)
    return ConsumerLoadForecastModelRequest(**values)  # type: ignore[arg-type]


def test_structural_port_conformance_without_inheritance() -> None:
    model = _model()
    port = _as_model_port(model)
    assert port is model
    assert ConsumerLoadForecastModelPort not in Lag24h168hOLSConsumerLoadForecastModel.__mro__
    assert not any(
        base.__name__
        in {
            "ConsumerLoadForecastModelPort",
            "Protocol",
            "ABC",
            "ModelPort",
            "ForecastPort",
        }
        for base in Lag24h168hOLSConsumerLoadForecastModel.__bases__
    )
    assert inspect.iscoroutinefunction(port.forecast)
    parameters = inspect.signature(Lag24h168hOLSConsumerLoadForecastModel.forecast).parameters
    assert tuple(parameters) == ("self", "request")
    assert parameters["request"].kind is inspect.Parameter.KEYWORD_ONLY
    init_parameters = inspect.signature(Lag24h168hOLSConsumerLoadForecastModel.__init__).parameters
    assert tuple(init_parameters) == ("self", "fit")
    assert init_parameters["fit"].kind is inspect.Parameter.KEYWORD_ONLY


async def test_known_parameters_and_lags_produce_exact_prediction() -> None:
    target = utc(hour=16)
    request = _request(
        history=_history_for(target, lag_24h_mw=1.0, lag_168h_mw=2.0),
        target_timestamps=(target,),
    )
    result = await _model().forecast(request=request)
    assert len(result) == 1
    point = result[0]
    assert isinstance(point, LoadForecastPoint)
    assert point.target_timestamp == target
    assert point.value_mw == 2.0 + 3.0 * 1.0 + 5.0 * 2.0
    assert point.value_mw == 15.0


async def test_nonzero_intercept_participates() -> None:
    target = utc(hour=16)
    request = _request(history=_history_for(target), target_timestamps=(target,))
    with_intercept = await _model(_fit(intercept_mw=2.0)).forecast(request=request)
    without_intercept = await _model(_fit(intercept_mw=0.0)).forecast(request=request)
    assert with_intercept[0].value_mw == 15.0
    assert without_intercept[0].value_mw == 13.0
    assert with_intercept[0].value_mw != without_intercept[0].value_mw


async def test_lag_24h_coefficient_participates() -> None:
    target = utc(hour=16)
    request = _request(
        history=_history_for(target, lag_24h_mw=4.0, lag_168h_mw=2.0),
        target_timestamps=(target,),
    )
    model_with = _model(_fit(lag_24h_coefficient=3.0, lag_168h_coefficient=0.0, intercept_mw=0.0))
    model_without = _model(
        _fit(lag_24h_coefficient=0.0, lag_168h_coefficient=0.0, intercept_mw=0.0)
    )
    with_24h = await model_with.forecast(request=request)
    without_24h = await model_without.forecast(request=request)
    assert with_24h[0].value_mw == 12.0
    assert without_24h[0].value_mw == 0.0
    assert with_24h[0].value_mw != without_24h[0].value_mw


async def test_lag_168h_coefficient_participates() -> None:
    target = utc(hour=16)
    request = _request(
        history=_history_for(target, lag_24h_mw=1.0, lag_168h_mw=2.0),
        target_timestamps=(target,),
    )
    model_with = _model(_fit(lag_24h_coefficient=0.0, lag_168h_coefficient=5.0, intercept_mw=0.0))
    model_without = _model(
        _fit(lag_24h_coefficient=0.0, lag_168h_coefficient=0.0, intercept_mw=0.0)
    )
    with_168h = await model_with.forecast(request=request)
    without_168h = await model_without.forecast(request=request)
    assert with_168h[0].value_mw == 10.0
    assert without_168h[0].value_mw == 0.0
    assert with_168h[0].value_mw != without_168h[0].value_mw


async def test_changing_lag_24h_changes_output_when_lag_168h_is_fixed() -> None:
    target = utc(hour=16)
    low = _request(history=_history_for(target, lag_24h_mw=1.0, lag_168h_mw=2.0))
    high = _request(history=_history_for(target, lag_24h_mw=4.0, lag_168h_mw=2.0))
    model = _model(_fit(lag_24h_coefficient=3.0, lag_168h_coefficient=5.0, intercept_mw=2.0))
    low_result = await model.forecast(request=low)
    high_result = await model.forecast(request=high)
    assert low_result[0].value_mw == 15.0
    assert high_result[0].value_mw == 24.0
    assert high_result[0].value_mw != low_result[0].value_mw


async def test_changing_lag_168h_changes_output_when_lag_24h_is_fixed() -> None:
    target = utc(hour=16)
    low = _request(history=_history_for(target, lag_24h_mw=1.0, lag_168h_mw=2.0))
    high = _request(history=_history_for(target, lag_24h_mw=1.0, lag_168h_mw=4.0))
    model = _model(_fit(lag_24h_coefficient=3.0, lag_168h_coefficient=5.0, intercept_mw=2.0))
    low_result = await model.forecast(request=low)
    high_result = await model.forecast(request=high)
    assert low_result[0].value_mw == 15.0
    assert high_result[0].value_mw == 25.0
    assert high_result[0].value_mw != low_result[0].value_mw


async def test_explicit_inference_identity_passthrough() -> None:
    generated_at = utc(hour=11)
    target = utc(hour=16)
    request = _request(
        forecast_run_id="run-explicit",
        generated_at=generated_at,
        consumer_id="consumer-42",
        history=_history_for(target, consumer_id="consumer-42"),
    )
    result = await _model().forecast(request=request)
    point = result[0]
    assert point.forecast_run_id == "run-explicit"
    assert point.forecast_run_id == request.forecast_run_id
    assert point.generated_at == generated_at
    assert point.generated_at == request.generated_at
    assert point.consumer_id == "consumer-42"
    assert point.consumer_id == request.consumer_id


async def test_multiple_targets_preserve_requested_order() -> None:
    later = utc(hour=18)
    earlier = utc(hour=12)
    request = _request(
        history=(
            *_history_for(later, lag_24h_mw=1.0, lag_168h_mw=1.0),
            *_history_for(earlier, lag_24h_mw=2.0, lag_168h_mw=2.0),
        ),
        target_timestamps=(later, earlier),
    )
    model = _model(_fit(lag_24h_coefficient=1.0, lag_168h_coefficient=1.0, intercept_mw=0.0))
    result = await model.forecast(request=request)
    assert tuple(point.target_timestamp for point in result) == (later, earlier)
    assert result[0].value_mw == 2.0
    assert result[1].value_mw == 4.0


async def test_duplicate_requested_targets_are_not_deduplicated() -> None:
    target = utc(hour=16)
    request = _request(target_timestamps=(target, target))
    result = await _model().forecast(request=request)
    assert len(result) == 2
    assert result[0].target_timestamp == target
    assert result[1].target_timestamp == target
    assert result[0].value_mw == 15.0
    assert result[1].value_mw == 15.0


async def test_zero_raw_prediction_is_admitted() -> None:
    target = utc(hour=16)
    request = _request(history=_history_for(target, lag_24h_mw=2.0, lag_168h_mw=3.0))
    model = _model(_fit(lag_24h_coefficient=-1.0, lag_168h_coefficient=-1.0, intercept_mw=5.0))
    result = await model.forecast(request=request)
    assert result[0].value_mw == 0.0
    assert isfinite(result[0].value_mw)


async def test_negative_finite_raw_prediction_fails_closed_without_clamp_or_value_leak() -> None:
    target = utc(hour=16)
    request = _request(history=_history_for(target, lag_24h_mw=1.0, lag_168h_mw=1.0))
    model = _model(_fit(lag_24h_coefficient=1.0, lag_168h_coefficient=1.0, intercept_mw=-10.0))
    with pytest.raises(InvalidRequestError, match=_NEGATIVE_PREDICTION_MESSAGE) as caught:
        await model.forecast(request=request)
    assert caught.value.code == "invalid_request"
    assert "-8" not in caught.value.message
    assert "-10" not in caught.value.message
    assert "0.0" not in caught.value.message
    assert "consumer-1" not in caught.value.message


async def test_missing_exact_24h_lag_raises_invalid_request() -> None:
    target = utc(hour=16)
    request = _request(
        history=(consumption(timestamp=target - _LAG_168H, value_mw=2.0),),
        target_timestamps=(target,),
    )
    with pytest.raises(InvalidRequestError, match=_MISSING_LAG_24H_MESSAGE) as caught:
        await _model().forecast(request=request)
    assert caught.value.code == "invalid_request"
    assert "consumer-1" not in caught.value.message
    assert "2.0" not in caught.value.message


async def test_missing_exact_168h_lag_raises_invalid_request() -> None:
    target = utc(hour=16)
    request = _request(
        history=(consumption(timestamp=target - _LAG_24H, value_mw=1.0),),
        target_timestamps=(target,),
    )
    with pytest.raises(InvalidRequestError, match=_MISSING_LAG_168H_MESSAGE) as caught:
        await _model().forecast(request=request)
    assert caught.value.code == "invalid_request"
    assert "1.0" not in caught.value.message


async def test_near_but_not_exact_24h_observation_is_rejected() -> None:
    target = utc(hour=16)
    request = _request(
        history=(
            consumption(timestamp=(target - _LAG_24H) - timedelta(minutes=1), value_mw=1.0),
            consumption(timestamp=(target - _LAG_24H) + timedelta(minutes=1), value_mw=2.0),
            consumption(timestamp=target - _LAG_168H, value_mw=3.0),
        ),
        target_timestamps=(target,),
    )
    with pytest.raises(InvalidRequestError, match=_MISSING_LAG_24H_MESSAGE):
        await _model().forecast(request=request)


async def test_near_but_not_exact_168h_observation_is_rejected() -> None:
    target = utc(hour=16)
    request = _request(
        history=(
            consumption(timestamp=target - _LAG_24H, value_mw=1.0),
            consumption(timestamp=(target - _LAG_168H) - timedelta(minutes=1), value_mw=2.0),
            consumption(timestamp=(target - _LAG_168H) + timedelta(minutes=1), value_mw=3.0),
        ),
        target_timestamps=(target,),
    )
    with pytest.raises(InvalidRequestError, match=_MISSING_LAG_168H_MESSAGE):
        await _model().forecast(request=request)


async def test_empty_history_fails_closed() -> None:
    request = _request(history=())
    assert request.history == ()
    with pytest.raises(InvalidRequestError, match=_MISSING_LAG_24H_MESSAGE):
        await _model().forecast(request=request)


async def test_duplicate_exact_24h_observations_fail_closed() -> None:
    target = utc(hour=16)
    reference = target - _LAG_24H
    request = _request(
        history=(
            consumption(timestamp=reference, value_mw=1.0),
            consumption(timestamp=reference, value_mw=9.0),
            consumption(timestamp=target - _LAG_168H, value_mw=2.0),
        ),
        target_timestamps=(target,),
    )
    with pytest.raises(InvalidRequestError, match=_DUPLICATE_LAG_24H_MESSAGE) as caught:
        await _model().forecast(request=request)
    assert caught.value.code == "invalid_request"
    assert "1.0" not in caught.value.message
    assert "9.0" not in caught.value.message


async def test_duplicate_exact_168h_observations_fail_closed() -> None:
    target = utc(hour=16)
    reference = target - _LAG_168H
    request = _request(
        history=(
            consumption(timestamp=target - _LAG_24H, value_mw=1.0),
            consumption(timestamp=reference, value_mw=2.0),
            consumption(timestamp=reference, value_mw=8.0),
        ),
        target_timestamps=(target,),
    )
    with pytest.raises(InvalidRequestError, match=_DUPLICATE_LAG_168H_MESSAGE) as caught:
        await _model().forecast(request=request)
    assert "2.0" not in caught.value.message
    assert "8.0" not in caught.value.message


async def test_no_partial_output_when_a_later_target_is_unresolvable() -> None:
    valid_target = utc(hour=12)
    missing_target = utc(hour=18)
    request = _request(
        history=_history_for(valid_target, lag_24h_mw=1.0, lag_168h_mw=1.0),
        target_timestamps=(valid_target, missing_target),
    )
    with pytest.raises(InvalidRequestError, match=_MISSING_LAG_24H_MESSAGE):
        await _model().forecast(request=request)


async def test_no_partial_output_when_a_later_target_is_negative() -> None:
    valid_target = utc(hour=12)
    negative_target = utc(hour=18)
    request = _request(
        history=(
            *_history_for(valid_target, lag_24h_mw=1.0, lag_168h_mw=1.0),
            *_history_for(negative_target, lag_24h_mw=10.0, lag_168h_mw=10.0),
        ),
        target_timestamps=(valid_target, negative_target),
    )
    model = _model(_fit(lag_24h_coefficient=-1.0, lag_168h_coefficient=-1.0, intercept_mw=5.0))
    with pytest.raises(InvalidRequestError, match=_NEGATIVE_PREDICTION_MESSAGE):
        await model.forecast(request=request)


async def test_mixed_consumer_request_cannot_be_constructed() -> None:
    target = utc(hour=16)
    with pytest.raises(ValueError, match="history consumer_id must match request consumer_id"):
        _request(
            history=(
                consumption(consumer_id="consumer-1", timestamp=target - _LAG_24H, value_mw=1.0),
                consumption(consumer_id="consumer-2", timestamp=target - _LAG_168H, value_mw=2.0),
            )
        )


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("lag_24h_coefficient", nan),
        ("lag_168h_coefficient", nan),
        ("intercept_mw", nan),
        ("lag_24h_coefficient", float("inf")),
        ("lag_168h_coefficient", float("-inf")),
        ("intercept_mw", float("inf")),
    ],
)
def test_non_finite_fitted_parameters_fail_at_construction(
    field_name: str,
    invalid_value: float,
) -> None:
    with pytest.raises(InvalidRequestError, match=_NON_FINITE_FIT_MESSAGE) as caught:
        Lag24h168hOLSConsumerLoadForecastModel(fit=_fit(**{field_name: invalid_value}))
    assert caught.value.code == "invalid_request"
    assert "nan" not in caught.value.message.lower()
    assert "float('inf')" not in caught.value.message.lower()
    assert 'float("-inf")' not in caught.value.message.lower()


async def test_non_finite_raw_prediction_fails_closed() -> None:
    target = utc(hour=16)
    request = _request(history=_history_for(target, lag_24h_mw=1e308, lag_168h_mw=1e308))
    model = _model(_fit(lag_24h_coefficient=1e308, lag_168h_coefficient=1e308, intercept_mw=0.0))
    with pytest.raises(InvalidRequestError, match=_NON_FINITE_PREDICTION_MESSAGE) as caught:
        await model.forecast(request=request)
    assert caught.value.code == "invalid_request"
    assert "1e308" not in caught.value.message


async def test_forecast_does_not_mutate_request_history_or_fit() -> None:
    target = utc(hour=16)
    history_24h = consumption(timestamp=target - _LAG_24H, value_mw=1.0)
    history_168h = consumption(timestamp=target - _LAG_168H, value_mw=2.0)
    history = (history_24h, history_168h)
    request = _request(history=history, target_timestamps=(target,))
    fit = _fit()
    model = Lag24h168hOLSConsumerLoadForecastModel(fit=fit)
    original_history_id = id(request.history)
    original_targets = request.target_timestamps
    first = await model.forecast(request=request)
    second = await model.forecast(request=request)
    assert first[0].value_mw == 15.0
    assert second[0].value_mw == 15.0
    assert first[0] == second[0]
    assert request.history is history
    assert id(request.history) == original_history_id
    assert request.history[0] is history_24h
    assert request.target_timestamps is original_targets
    assert fit.lag_24h_coefficient == 3.0
    assert fit.lag_168h_coefficient == 5.0
    assert fit.intercept_mw == 2.0
    assert history_24h.value_mw == 1.0
    assert history_168h.value_mw == 2.0
    assert request.forecast_run_id == "run-1"


def test_forecast_does_not_call_offline_fitter() -> None:
    source = inspect.getsource(Lag24h168hOLSConsumerLoadForecastModel)
    assert "fit_consumer_load_lag_24h_168h_linear_regression" not in source
    assert "predict_consumer_load_lag_24h_168h_linear_regression" not in source
    assert "PreviousDayPersistenceConsumerLoadForecastModel" not in source
