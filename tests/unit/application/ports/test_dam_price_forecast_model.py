"""DAM Price Forecast model-port contract without a production model."""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.ports import (
    DAMPriceForecastModelPort,
    DAMPriceForecastModelRequest,
)
from energy_trading.domain.models.forecasting import PriceForecastPoint
from energy_trading.domain.models.observations import MarketPriceRecord
from energy_trading.domain.value_objects.money import EnergyPrice
from energy_trading.domain.value_objects.quantities import CurrencyCode, EntityId
from energy_trading.domain.value_objects.time import UtcDateTime
from tests.unit.domain._factories import amd_price, utc


class _FakeDAMPriceForecastModel:
    """Test-only fake that structurally satisfies the model port.

    Not a production adapter. Does not inherit a production, ML, or
    infrastructure base class.
    """

    def __init__(
        self,
        points: tuple[PriceForecastPoint, ...] = (),
        *,
        unavailable: bool = False,
    ) -> None:
        self.points = points
        self.unavailable = unavailable
        self.calls: list[DAMPriceForecastModelRequest] = []

    async def forecast(
        self,
        *,
        request: DAMPriceForecastModelRequest,
    ) -> tuple[PriceForecastPoint, ...]:
        self.calls.append(request)
        if self.unavailable:
            msg = "dam price forecast model unavailable"
            raise DependencyUnavailableError(msg)
        return self.points


def _as_model_port(model: _FakeDAMPriceForecastModel) -> DAMPriceForecastModelPort:
    return model


def _price(amount: str = "45.00", currency: str = "AMD") -> EnergyPrice:
    return EnergyPrice(amount_per_mwh=Decimal(amount), currency=currency)


def _market(**overrides: object) -> MarketPriceRecord:
    values: dict[str, object] = {
        "market_id": "market-1",
        "timestamp": utc(),
        "price": amd_price(),
    }
    values.update(overrides)
    return MarketPriceRecord.model_validate(values)


def _point(**overrides: object) -> PriceForecastPoint:
    values: dict[str, object] = {
        "forecast_run_id": "run-1",
        "market_id": "market-1",
        "generated_at": utc(),
        "target_timestamp": utc(hour=16),
        "price": amd_price("45.00"),
    }
    values.update(overrides)
    return PriceForecastPoint.model_validate(values)


def _request(**overrides: object) -> DAMPriceForecastModelRequest:
    values: dict[str, object] = {
        "market_id": "market-1",
        "currency": "AMD",
        "history": (_market(),),
        "target_timestamps": (utc(hour=16),),
    }
    values.update(overrides)
    return DAMPriceForecastModelRequest(**values)  # type: ignore[arg-type]


def test_structural_fake_does_not_inherit_production_base() -> None:
    assert DAMPriceForecastModelPort not in _FakeDAMPriceForecastModel.__mro__
    assert not any(
        base.__name__
        in {
            "DAMPriceForecastModelPort",
            "Protocol",
            "ABC",
        }
        for base in _FakeDAMPriceForecastModel.__bases__
    )


def test_fake_provides_async_keyword_only_forecast() -> None:
    fake = _FakeDAMPriceForecastModel()
    port = _as_model_port(fake)
    assert inspect.iscoroutinefunction(port.forecast)
    parameters = inspect.signature(_FakeDAMPriceForecastModel.forecast).parameters
    assert tuple(parameters) == ("self", "request")
    assert parameters["request"].kind is inspect.Parameter.KEYWORD_ONLY
    annotation = inspect.signature(DAMPriceForecastModelPort.forecast).return_annotation
    assert annotation == tuple[PriceForecastPoint, ...]


def test_request_is_frozen_and_slots_based() -> None:
    request = _request()
    assert request.__slots__ == ("market_id", "currency", "history", "target_timestamps")
    with pytest.raises(FrozenInstanceError):
        request.history = ()  # type: ignore[misc]


def test_request_history_is_immutable_market_price_records() -> None:
    record = _market()
    request = _request(history=(record,))
    assert request.history == (record,)
    assert isinstance(request.history, tuple)
    assert all(isinstance(item, MarketPriceRecord) for item in request.history)
    assert record.price.currency == "AMD"
    with pytest.raises(AttributeError, match="has no attribute"):
        request.history.append(record)  # type: ignore[attr-defined]


def test_request_rejects_mutable_history_collection() -> None:
    with pytest.raises(TypeError, match="history must be an immutable tuple"):
        _request(history=[_market()])  # type: ignore[arg-type]


def test_request_rejects_non_market_price_history_member() -> None:
    with pytest.raises(TypeError, match="history must contain MarketPriceRecord values"):
        _request(history=("not-a-record",))  # type: ignore[arg-type]


def test_request_allows_empty_history_when_market_and_currency_are_explicit() -> None:
    request = _request(history=())
    assert request.market_id == "market-1"
    assert request.currency == "AMD"
    assert request.history == ()


def test_request_does_not_infer_market_id_from_history() -> None:
    record = _market(market_id="market-1")
    with pytest.raises(TypeError, match="market_id"):
        DAMPriceForecastModelRequest(
            currency="AMD",
            history=(record,),
            target_timestamps=(utc(hour=16),),
        )  # type: ignore[call-arg]


def test_request_does_not_infer_currency_from_history() -> None:
    record = _market()
    with pytest.raises(TypeError, match="currency"):
        DAMPriceForecastModelRequest(
            market_id="market-1",
            history=(record,),
            target_timestamps=(utc(hour=16),),
        )  # type: ignore[call-arg]


def test_request_same_market_and_currency_history_succeeds() -> None:
    first = _market(timestamp=utc(hour=10))
    second = _market(timestamp=utc(hour=11), price=amd_price("13.00"))
    request = _request(market_id="market-1", currency="AMD", history=(first, second))
    assert request.market_id == "market-1"
    assert request.currency == "AMD"
    assert request.history == (first, second)


def test_request_rejects_one_mismatched_historical_market() -> None:
    other = _market(market_id="market-b")
    with pytest.raises(ValueError, match="history market_id must match request market_id"):
        _request(market_id="market-a", history=(other,))


def test_request_rejects_mixed_market_history() -> None:
    matching = _market(market_id="market-a")
    other = _market(market_id="market-b", timestamp=utc(hour=11))
    with pytest.raises(ValueError, match="history market_id must match request market_id"):
        _request(market_id="market-a", history=(matching, other))


def test_request_rejects_one_mismatched_historical_currency() -> None:
    other = _market(price=_price(currency="EUR"))
    with pytest.raises(ValueError, match="history currency must match request currency"):
        _request(currency="AMD", history=(other,))


def test_request_rejects_mixed_currency_history() -> None:
    matching = _market(price=_price(currency="AMD"))
    other = _market(timestamp=utc(hour=11), price=_price(currency="EUR"))
    with pytest.raises(ValueError, match="history currency must match request currency"):
        _request(currency="AMD", history=(matching, other))


def test_request_rejects_lowercase_currency_without_converting() -> None:
    with pytest.raises(ValueError, match="currency must be a three-letter uppercase currency code"):
        _request(currency="amd", history=())


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
    annotations = DAMPriceForecastModelRequest.__annotations__
    assert annotations == {
        "market_id": EntityId,
        "currency": CurrencyCode,
        "history": tuple[MarketPriceRecord, ...],
        "target_timestamps": tuple[UtcDateTime, ...],
    }
    assert "Any" not in {str(item) for item in annotations.values()}
    assert dict not in annotations.values()


async def test_empty_forecast_tuple_is_valid() -> None:
    port = _as_model_port(_FakeDAMPriceForecastModel())
    result = await port.forecast(request=_request())
    assert result == ()
    assert isinstance(result, tuple)


async def test_forecast_returns_price_forecast_point_tuple_with_explicit_currency() -> None:
    point = _point()
    port = _as_model_port(_FakeDAMPriceForecastModel((point,)))
    result = await port.forecast(request=_request())
    assert result == (point,)
    assert all(isinstance(item, PriceForecastPoint) for item in result)
    assert point.price.currency == "AMD"
    assert point.price.amount_per_mwh == Decimal("45.00")


async def test_fake_can_represent_dependency_unavailable() -> None:
    fake = _FakeDAMPriceForecastModel(unavailable=True)
    port = _as_model_port(fake)
    with pytest.raises(DependencyUnavailableError, match="dam price forecast model unavailable"):
        await port.forecast(request=_request())
    assert len(fake.calls) == 1
