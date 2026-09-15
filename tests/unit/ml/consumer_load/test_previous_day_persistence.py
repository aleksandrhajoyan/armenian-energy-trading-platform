"""Exact previous-day persistence Consumer Load Forecast baseline."""

from __future__ import annotations

import inspect
from datetime import timedelta

import pytest

from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.ports.consumer_load_forecast_model import (
    ConsumerLoadForecastModelPort,
    ConsumerLoadForecastModelRequest,
)
from energy_trading.domain.models.forecasting import LoadForecastPoint
from energy_trading.ml.consumer_load.previous_day_persistence import (
    PreviousDayPersistenceConsumerLoadForecastModel,
)
from tests.unit.domain._factories import consumption, utc

_MISSING_LAG_MESSAGE = (
    "Previous-day persistence requires exactly one history observation at the 24-hour lag."
)
_DUPLICATE_LAG_MESSAGE = "Previous-day persistence requires a unique 24-hour lag observation."
_LAG = timedelta(hours=24)


def _as_model_port(
    model: PreviousDayPersistenceConsumerLoadForecastModel,
) -> ConsumerLoadForecastModelPort:
    return model


def _request(**overrides: object) -> ConsumerLoadForecastModelRequest:
    target = utc(hour=16)
    values: dict[str, object] = {
        "forecast_run_id": "run-1",
        "generated_at": utc(hour=9),
        "consumer_id": "consumer-1",
        "history": (consumption(timestamp=target - _LAG, value_mw=7.25),),
        "target_timestamps": (target,),
    }
    values.update(overrides)
    return ConsumerLoadForecastModelRequest(**values)  # type: ignore[arg-type]


def test_structural_port_conformance_without_inheritance() -> None:
    model = PreviousDayPersistenceConsumerLoadForecastModel()
    port = _as_model_port(model)
    assert port is model
    assert (
        ConsumerLoadForecastModelPort not in PreviousDayPersistenceConsumerLoadForecastModel.__mro__
    )
    assert not any(
        base.__name__
        in {
            "ConsumerLoadForecastModelPort",
            "Protocol",
            "ABC",
            "ModelPort",
            "ForecastPort",
        }
        for base in PreviousDayPersistenceConsumerLoadForecastModel.__bases__
    )
    assert inspect.iscoroutinefunction(port.forecast)
    parameters = inspect.signature(
        PreviousDayPersistenceConsumerLoadForecastModel.forecast
    ).parameters
    assert tuple(parameters) == ("self", "request")
    assert parameters["request"].kind is inspect.Parameter.KEYWORD_ONLY


async def test_single_exact_previous_day_observation_copies_mw_unchanged() -> None:
    target = utc(hour=16)
    history_record = consumption(timestamp=target - _LAG, value_mw=7.25)
    request = _request(history=(history_record,), target_timestamps=(target,))
    result = await PreviousDayPersistenceConsumerLoadForecastModel().forecast(request=request)
    assert len(result) == 1
    point = result[0]
    assert isinstance(point, LoadForecastPoint)
    assert point.target_timestamp == target
    assert point.value_mw == 7.25
    assert point.value_mw == history_record.value_mw
    assert point.value_mw is history_record.value_mw


async def test_explicit_inference_identity_passthrough() -> None:
    generated_at = utc(hour=11)
    request = _request(
        forecast_run_id="run-explicit",
        generated_at=generated_at,
        consumer_id="consumer-42",
        history=(
            consumption(consumer_id="consumer-42", timestamp=utc(hour=16) - _LAG, value_mw=3.5),
        ),
    )
    result = await PreviousDayPersistenceConsumerLoadForecastModel().forecast(request=request)
    assert len(result) == 1
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
    later_history = consumption(timestamp=later - _LAG, value_mw=4.0)
    earlier_history = consumption(timestamp=earlier - _LAG, value_mw=9.5)
    request = _request(
        history=(later_history, earlier_history),
        target_timestamps=(later, earlier),
    )
    result = await PreviousDayPersistenceConsumerLoadForecastModel().forecast(request=request)
    assert tuple(point.target_timestamp for point in result) == (later, earlier)
    assert result[0].value_mw == 4.0
    assert result[1].value_mw == 9.5


async def test_duplicate_requested_targets_are_not_deduplicated() -> None:
    target = utc(hour=16)
    history_record = consumption(timestamp=target - _LAG, value_mw=6.125)
    request = _request(
        history=(history_record,),
        target_timestamps=(target, target),
    )
    result = await PreviousDayPersistenceConsumerLoadForecastModel().forecast(request=request)
    assert len(result) == 2
    assert result[0].target_timestamp == target
    assert result[1].target_timestamp == target
    assert result[0].value_mw == 6.125
    assert result[1].value_mw == 6.125
    assert result[0].value_mw is history_record.value_mw
    assert result[1].value_mw is history_record.value_mw


async def test_missing_exact_reference_raises_invalid_request() -> None:
    with pytest.raises(InvalidRequestError, match=_MISSING_LAG_MESSAGE) as caught:
        await PreviousDayPersistenceConsumerLoadForecastModel().forecast(
            request=_request(history=(consumption(timestamp=utc(hour=10), value_mw=2.0),))
        )
    assert caught.value.code == "invalid_request"
    assert "consumer-1" not in caught.value.message
    assert "2.0" not in caught.value.message


async def test_near_but_not_exact_observation_is_rejected() -> None:
    target = utc(hour=16)
    too_early = (target - _LAG) - timedelta(minutes=1)
    too_late = (target - _LAG) + timedelta(minutes=1)
    request = _request(
        history=(
            consumption(timestamp=too_early, value_mw=1.0),
            consumption(timestamp=too_late, value_mw=2.0),
        ),
        target_timestamps=(target,),
    )
    with pytest.raises(InvalidRequestError, match=_MISSING_LAG_MESSAGE):
        await PreviousDayPersistenceConsumerLoadForecastModel().forecast(request=request)


async def test_weekly_observation_is_not_a_fallback() -> None:
    target = utc(hour=16)
    weekly = target - timedelta(days=7)
    request = _request(
        history=(consumption(timestamp=weekly, value_mw=8.0),),
        target_timestamps=(target,),
    )
    with pytest.raises(InvalidRequestError, match=_MISSING_LAG_MESSAGE):
        await PreviousDayPersistenceConsumerLoadForecastModel().forecast(request=request)


async def test_empty_history_fails_closed() -> None:
    request = _request(history=())
    assert request.history == ()
    with pytest.raises(InvalidRequestError, match=_MISSING_LAG_MESSAGE):
        await PreviousDayPersistenceConsumerLoadForecastModel().forecast(request=request)


async def test_duplicate_exact_reference_observations_fail_closed() -> None:
    target = utc(hour=16)
    reference = target - _LAG
    request = _request(
        history=(
            consumption(timestamp=reference, value_mw=1.0),
            consumption(timestamp=reference, value_mw=9.0),
        ),
        target_timestamps=(target,),
    )
    with pytest.raises(InvalidRequestError, match=_DUPLICATE_LAG_MESSAGE) as caught:
        await PreviousDayPersistenceConsumerLoadForecastModel().forecast(request=request)
    assert caught.value.code == "invalid_request"
    assert "1.0" not in caught.value.message
    assert "9.0" not in caught.value.message


async def test_no_partial_output_when_a_later_target_is_unresolvable() -> None:
    valid_target = utc(hour=12)
    missing_target = utc(hour=18)
    request = _request(
        history=(consumption(timestamp=valid_target - _LAG, value_mw=5.0),),
        target_timestamps=(valid_target, missing_target),
    )
    with pytest.raises(InvalidRequestError, match=_MISSING_LAG_MESSAGE):
        await PreviousDayPersistenceConsumerLoadForecastModel().forecast(request=request)


async def test_no_partial_output_when_a_later_target_is_ambiguous() -> None:
    valid_target = utc(hour=12)
    ambiguous_target = utc(hour=18)
    ambiguous_reference = ambiguous_target - _LAG
    request = _request(
        history=(
            consumption(timestamp=valid_target - _LAG, value_mw=5.0),
            consumption(timestamp=ambiguous_reference, value_mw=1.0),
            consumption(timestamp=ambiguous_reference, value_mw=2.0),
        ),
        target_timestamps=(valid_target, ambiguous_target),
    )
    with pytest.raises(InvalidRequestError, match=_DUPLICATE_LAG_MESSAGE):
        await PreviousDayPersistenceConsumerLoadForecastModel().forecast(request=request)


async def test_canonical_mw_is_not_converted_or_altered() -> None:
    target = utc(hour=16)
    history_record = consumption(timestamp=target - _LAG, value_mw=12.375)
    request = _request(history=(history_record,), target_timestamps=(target,))
    result = await PreviousDayPersistenceConsumerLoadForecastModel().forecast(request=request)
    assert result[0].value_mw == 12.375
    assert result[0].value_mw is history_record.value_mw
    assert not hasattr(result[0], "value_mwh")


async def test_forecast_does_not_mutate_request_or_history() -> None:
    target = utc(hour=16)
    history_record = consumption(timestamp=target - _LAG, value_mw=3.25)
    history = (history_record, consumption(timestamp=utc(hour=8), value_mw=1.0))
    request = _request(history=history, target_timestamps=(target,))
    original_history_id = id(request.history)
    original_record_id = id(history_record)
    original_targets = request.target_timestamps
    result = await PreviousDayPersistenceConsumerLoadForecastModel().forecast(request=request)
    assert result[0].value_mw == 3.25
    assert request.history is history
    assert id(request.history) == original_history_id
    assert request.history[0] is history_record
    assert id(request.history[0]) == original_record_id
    assert request.target_timestamps is original_targets
    assert history_record.value_mw == 3.25
    assert request.forecast_run_id == "run-1"
    assert request.consumer_id == "consumer-1"
