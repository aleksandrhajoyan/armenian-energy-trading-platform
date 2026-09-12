"""Consumer Load Forecast model-port contract without a production model."""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone

import pytest

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.ports import (
    ConsumerLoadForecastModelPort,
    ConsumerLoadForecastModelRequest,
)
from energy_trading.domain.models.forecasting import LoadForecastPoint
from energy_trading.domain.models.observations import ConsumptionRecord
from energy_trading.domain.value_objects.quantities import EntityId
from energy_trading.domain.value_objects.time import UtcDateTime
from tests.unit.domain._factories import consumption, utc


class _FakeConsumerLoadForecastModel:
    """Test-only fake that structurally satisfies the model port.

    Not a production adapter. Does not inherit a production, ML, or
    infrastructure base class.
    """

    def __init__(
        self,
        points: tuple[LoadForecastPoint, ...] = (),
        *,
        unavailable: bool = False,
    ) -> None:
        self.points = points
        self.unavailable = unavailable
        self.calls: list[ConsumerLoadForecastModelRequest] = []

    async def forecast(
        self,
        *,
        request: ConsumerLoadForecastModelRequest,
    ) -> tuple[LoadForecastPoint, ...]:
        self.calls.append(request)
        if self.unavailable:
            msg = "consumer load forecast model unavailable"
            raise DependencyUnavailableError(msg)
        return self.points


def _as_model_port(
    model: _FakeConsumerLoadForecastModel,
) -> ConsumerLoadForecastModelPort:
    return model


def _point(**overrides: object) -> LoadForecastPoint:
    values: dict[str, object] = {
        "forecast_run_id": "run-1",
        "consumer_id": "consumer-1",
        "generated_at": utc(),
        "target_timestamp": utc(hour=16),
        "value_mw": 3.25,
    }
    values.update(overrides)
    return LoadForecastPoint.model_validate(values)


def _request(**overrides: object) -> ConsumerLoadForecastModelRequest:
    values: dict[str, object] = {
        "consumer_id": "consumer-1",
        "history": (consumption(),),
        "target_timestamps": (utc(hour=16),),
    }
    values.update(overrides)
    return ConsumerLoadForecastModelRequest(**values)  # type: ignore[arg-type]


def test_structural_fake_does_not_inherit_production_base() -> None:
    assert ConsumerLoadForecastModelPort not in _FakeConsumerLoadForecastModel.__mro__
    assert not any(
        base.__name__
        in {
            "ConsumerLoadForecastModelPort",
            "Protocol",
            "ABC",
        }
        for base in _FakeConsumerLoadForecastModel.__bases__
    )


def test_fake_provides_async_keyword_only_forecast() -> None:
    fake = _FakeConsumerLoadForecastModel()
    port = _as_model_port(fake)
    assert inspect.iscoroutinefunction(port.forecast)
    parameters = inspect.signature(_FakeConsumerLoadForecastModel.forecast).parameters
    assert tuple(parameters) == ("self", "request")
    assert parameters["request"].kind is inspect.Parameter.KEYWORD_ONLY
    annotation = inspect.signature(ConsumerLoadForecastModelPort.forecast).return_annotation
    assert annotation == tuple[LoadForecastPoint, ...]


def test_request_is_frozen_and_slots_based() -> None:
    request = _request()
    assert request.__slots__ == ("consumer_id", "history", "target_timestamps")
    with pytest.raises(FrozenInstanceError):
        request.history = ()  # type: ignore[misc]


def test_request_history_is_immutable_consumption_records() -> None:
    record = consumption()
    request = _request(history=(record,))
    assert request.history == (record,)
    assert isinstance(request.history, tuple)
    assert all(isinstance(item, ConsumptionRecord) for item in request.history)
    assert record.value_mw == 1.5
    with pytest.raises(AttributeError, match="has no attribute"):
        request.history.append(record)  # type: ignore[attr-defined]


def test_request_rejects_mutable_history_collection() -> None:
    with pytest.raises(TypeError, match="history must be an immutable tuple"):
        _request(history=[consumption()])  # type: ignore[arg-type]


def test_request_rejects_non_consumption_history_member() -> None:
    with pytest.raises(TypeError, match="history must contain ConsumptionRecord values"):
        _request(history=("not-a-record",))  # type: ignore[arg-type]


def test_request_allows_empty_history_when_consumer_id_is_explicit() -> None:
    request = _request(history=())
    assert request.consumer_id == "consumer-1"
    assert request.history == ()


def test_request_does_not_infer_consumer_id_from_history() -> None:
    record = consumption(consumer_id="consumer-1")
    with pytest.raises(TypeError, match="consumer_id"):
        ConsumerLoadForecastModelRequest(
            history=(record,),
            target_timestamps=(utc(hour=16),),
        )  # type: ignore[call-arg]


def test_request_same_consumer_history_succeeds() -> None:
    first = consumption(consumer_id="consumer-1", timestamp=utc(hour=10))
    second = consumption(consumer_id="consumer-1", timestamp=utc(hour=11), value_mw=2.0)
    request = _request(consumer_id="consumer-1", history=(first, second))
    assert request.consumer_id == "consumer-1"
    assert request.history == (first, second)


def test_request_rejects_one_mismatched_historical_consumer() -> None:
    other = consumption(consumer_id="consumer-b")
    with pytest.raises(ValueError, match="history consumer_id must match request consumer_id"):
        _request(consumer_id="consumer-a", history=(other,))


def test_request_rejects_mixed_consumer_history() -> None:
    matching = consumption(consumer_id="consumer-a")
    other = consumption(consumer_id="consumer-b", timestamp=utc(hour=11))
    with pytest.raises(ValueError, match="history consumer_id must match request consumer_id"):
        _request(consumer_id="consumer-a", history=(matching, other))


def test_request_target_timestamps_are_explicit_and_typed() -> None:
    target = utc(hour=16)
    request = _request(target_timestamps=(target,))
    assert request.target_timestamps == (target,)
    assert isinstance(request.target_timestamps, tuple)
    assert all(isinstance(item, datetime) for item in request.target_timestamps)
    assert "horizon" not in request.__slots__


def test_request_rejects_mutable_target_timestamps() -> None:
    with pytest.raises(TypeError, match="target_timestamps must be an immutable tuple"):
        _request(target_timestamps=[utc(hour=16)])  # type: ignore[arg-type]


def test_request_rejects_empty_target_timestamps() -> None:
    with pytest.raises(ValueError, match="target_timestamps must contain at least one timestamp"):
        _request(target_timestamps=())


def test_request_rejects_naive_target_timestamps() -> None:
    naive = datetime(2026, 10, 1, 16, 0, 0)
    with pytest.raises(ValueError, match="target_timestamps must be timezone-aware"):
        _request(target_timestamps=(naive,))


def test_request_normalizes_aware_non_utc_target_timestamps() -> None:
    yerevan = timezone(timedelta(hours=4))
    request = _request(
        target_timestamps=(datetime(2026, 10, 1, 20, 0, 0, tzinfo=yerevan),),
    )
    assert request.target_timestamps == (datetime(2026, 10, 1, 16, 0, 0, tzinfo=UTC),)


def test_request_rejects_non_datetime_target_timestamp() -> None:
    with pytest.raises(TypeError, match="target_timestamps must be a datetime"):
        _request(target_timestamps=("2026-10-01T16:00:00+00:00",))  # type: ignore[arg-type]


def test_request_public_contract_has_no_dict_or_any_payload() -> None:
    annotations = ConsumerLoadForecastModelRequest.__annotations__
    assert annotations == {
        "consumer_id": EntityId,
        "history": tuple[ConsumptionRecord, ...],
        "target_timestamps": tuple[UtcDateTime, ...],
    }
    assert "Any" not in {str(item) for item in annotations.values()}
    assert dict not in annotations.values()


async def test_empty_forecast_tuple_is_valid() -> None:
    port = _as_model_port(_FakeConsumerLoadForecastModel())
    result = await port.forecast(request=_request())
    assert result == ()
    assert isinstance(result, tuple)


async def test_forecast_returns_load_forecast_point_tuple() -> None:
    point = _point()
    port = _as_model_port(_FakeConsumerLoadForecastModel((point,)))
    result = await port.forecast(request=_request())
    assert result == (point,)
    assert all(isinstance(item, LoadForecastPoint) for item in result)
    assert point.value_mw == 3.25


async def test_fake_can_represent_dependency_unavailable() -> None:
    fake = _FakeConsumerLoadForecastModel(unavailable=True)
    port = _as_model_port(fake)
    with pytest.raises(
        DependencyUnavailableError, match="consumer load forecast model unavailable"
    ):
        await port.forecast(request=_request())
    assert len(fake.calls) == 1
