"""Market Monitoring Agent application contract."""

from __future__ import annotations

import sys
from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from energy_trading.application.agents.base import AgentName, AgentPort
from energy_trading.application.agents.market_monitoring import (
    MarketMonitoringAgent,
    MarketMonitoringRequest,
    MarketMonitoringResult,
)
from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.domain.models.forecasting import PriceForecastPoint
from energy_trading.domain.models.observations import MarketPriceRecord
from energy_trading.domain.value_objects.money import EnergyPrice


class _FakeMarketPriceRecordSource:
    """Test-only source fake. Not a production adapter."""

    def __init__(
        self,
        records: tuple[MarketPriceRecord, ...] = (),
        *,
        error: Exception | None = None,
    ) -> None:
        self.records = records
        self.error = error
        self.calls: list[tuple[str, datetime, datetime]] = []

    async def fetch(
        self,
        *,
        market_id: str,
        horizon_start: datetime,
        horizon_end: datetime,
    ) -> tuple[MarketPriceRecord, ...]:
        self.calls.append((market_id, horizon_start, horizon_end))
        if self.error is not None:
            raise self.error
        return self.records


def _as_agent_port(
    agent: MarketMonitoringAgent,
) -> AgentPort[MarketMonitoringRequest, MarketMonitoringResult]:
    """Mypy-visible structural assignment to the shared agent port."""

    return agent


def _price(amount: str = "45.00", currency: str = "EUR") -> EnergyPrice:
    return EnergyPrice(amount_per_mwh=Decimal(amount), currency=currency)


def _market(**overrides: object) -> MarketPriceRecord:
    values: dict[str, object] = {
        "market_id": "market-1",
        "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
        "price": _price(),
    }
    values.update(overrides)
    return MarketPriceRecord.model_validate(values)


def _request(**overrides: object) -> MarketMonitoringRequest:
    values: dict[str, object] = {
        "market_id": "market-1",
        "horizon_start": datetime(2026, 10, 1, 0, tzinfo=UTC),
        "horizon_end": datetime(2026, 10, 2, 0, tzinfo=UTC),
    }
    values.update(overrides)
    return MarketMonitoringRequest(**values)  # type: ignore[arg-type]


def test_request_accepts_market_and_utc_horizon() -> None:
    request = _request()
    assert request.market_id == "market-1"
    assert request.horizon_start == datetime(2026, 10, 1, 0, tzinfo=UTC)
    assert request.horizon_end == datetime(2026, 10, 2, 0, tzinfo=UTC)
    assert request.horizon_start.tzinfo is UTC
    assert request.horizon_end.tzinfo is UTC


def test_request_strips_market_id_whitespace() -> None:
    request = _request(market_id="  market-1  ")
    assert request.market_id == "market-1"


def test_request_normalizes_aware_non_utc_horizons_to_utc() -> None:
    offset = timezone(timedelta(hours=4))
    request = _request(
        horizon_start=datetime(2026, 10, 1, 4, tzinfo=offset),
        horizon_end=datetime(2026, 10, 1, 8, tzinfo=offset),
    )
    assert request.horizon_start == datetime(2026, 10, 1, 0, tzinfo=UTC)
    assert request.horizon_end == datetime(2026, 10, 1, 4, tzinfo=UTC)
    assert request.horizon_start.tzinfo is UTC
    assert request.horizon_end.tzinfo is UTC


def test_request_rejects_naive_horizon_start() -> None:
    with pytest.raises(ValueError, match="horizon_start must be timezone-aware"):
        _request(horizon_start=datetime(2026, 10, 1, 0))


def test_request_rejects_naive_horizon_end() -> None:
    with pytest.raises(ValueError, match="horizon_end must be timezone-aware"):
        _request(horizon_end=datetime(2026, 10, 2, 0))


def test_request_rejects_blank_market_id() -> None:
    with pytest.raises(ValueError, match="market_id must be a non-empty string"):
        _request(market_id="")
    with pytest.raises(ValueError, match="market_id must be a non-empty string"):
        _request(market_id="   ")


def test_request_rejects_equal_horizon_bounds() -> None:
    instant = datetime(2026, 10, 1, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="horizon_end must be later than horizon_start"):
        _request(horizon_start=instant, horizon_end=instant)


def test_request_rejects_reversed_horizon() -> None:
    with pytest.raises(ValueError, match="horizon_end must be later than horizon_start"):
        _request(
            horizon_start=datetime(2026, 10, 2, 0, tzinfo=UTC),
            horizon_end=datetime(2026, 10, 1, 0, tzinfo=UTC),
        )


def test_request_is_frozen_and_slotted() -> None:
    request = _request()
    assert hasattr(MarketMonitoringRequest, "__slots__")
    with pytest.raises(FrozenInstanceError):
        request.market_id = "mutated"  # type: ignore[misc]
    field_names = tuple(item.name for item in fields(MarketMonitoringRequest))
    assert field_names == ("market_id", "horizon_start", "horizon_end")


def test_request_rejects_unrequested_fields() -> None:
    with pytest.raises(TypeError):
        MarketMonitoringRequest(
            market_id="market-1",
            horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
            horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
            currency="EUR",  # type: ignore[call-arg]
        )


def test_result_empty_tuple_is_valid() -> None:
    result = MarketMonitoringResult(records=())
    assert result.records == ()
    assert isinstance(result.records, tuple)


def test_result_accepts_one_market_price_record() -> None:
    record = _market()
    result = MarketMonitoringResult(records=(record,))
    assert result.records == (record,)


def test_result_preserves_multiple_record_order() -> None:
    first = _market(timestamp=datetime(2026, 10, 1, 11, tzinfo=UTC))
    second = _market(
        timestamp=datetime(2026, 10, 1, 10, tzinfo=UTC),
        price=_price("30.00", "USD"),
        volume_mwh=4.0,
    )
    result = MarketMonitoringResult(records=(first, second))
    assert result.records == (first, second)


def test_result_energy_price_and_currency_remain_unchanged() -> None:
    price = _price("77.10", "USD")
    record = _market(price=price, volume_mwh=9.25)
    result = MarketMonitoringResult(records=(record,))
    passed = result.records[0]
    assert passed is record
    assert passed.price is price
    assert passed.price.amount_per_mwh == Decimal("77.10")
    assert passed.price.currency == "USD"
    assert passed.volume_mwh == 9.25


def test_result_missing_volume_remains_none() -> None:
    record = _market()
    result = MarketMonitoringResult(records=(record,))
    assert result.records[0].volume_mwh is None


def test_result_rejects_mutable_records_collection() -> None:
    with pytest.raises(TypeError, match="records must be an immutable tuple"):
        MarketMonitoringResult(records=[_market()])  # type: ignore[arg-type]


def test_result_rejects_non_market_price_record_values() -> None:
    with pytest.raises(TypeError, match="records must contain MarketPriceRecord values"):
        MarketMonitoringResult(records=("not-market",))  # type: ignore[arg-type]


def test_result_is_frozen() -> None:
    result = MarketMonitoringResult(records=())
    assert hasattr(MarketMonitoringResult, "__slots__")
    with pytest.raises(FrozenInstanceError):
        result.records = ()  # type: ignore[misc]


def test_agent_does_not_inherit_agent_port() -> None:
    assert AgentPort not in MarketMonitoringAgent.__mro__
    assert not any(base.__name__ == "AgentPort" for base in MarketMonitoringAgent.__bases__)


def test_agent_name_is_canonical_market_identity() -> None:
    agent = MarketMonitoringAgent(_FakeMarketPriceRecordSource())
    port = _as_agent_port(agent)
    assert port.name is AgentName.MARKET_MONITORING
    assert port.name.value == "Market Monitoring Agent"


def test_agent_module_has_no_forecast_coupling() -> None:
    names = set(vars(sys.modules[MarketMonitoringAgent.__module__]))
    assert "PriceForecastPoint" not in names
    assert PriceForecastPoint.__name__ not in names


async def test_run_invokes_source_once_with_normalized_values() -> None:
    source = _FakeMarketPriceRecordSource()
    agent = MarketMonitoringAgent(source)
    offset = timezone(timedelta(hours=4))
    result = await _as_agent_port(agent).run(
        MarketMonitoringRequest(
            market_id="  market-1  ",
            horizon_start=datetime(2026, 10, 1, 4, tzinfo=offset),
            horizon_end=datetime(2026, 10, 1, 8, tzinfo=offset),
        )
    )
    assert result.records == ()
    assert len(source.calls) == 1
    market_id, horizon_start, horizon_end = source.calls[0]
    assert market_id == "market-1"
    assert horizon_start == datetime(2026, 10, 1, 0, tzinfo=UTC)
    assert horizon_end == datetime(2026, 10, 1, 4, tzinfo=UTC)


async def test_run_wraps_source_tuple_without_reordering() -> None:
    first = _market(timestamp=datetime(2026, 10, 1, 12, tzinfo=UTC))
    second = _market(
        timestamp=datetime(2026, 10, 1, 8, tzinfo=UTC),
        price=_price("18.00", "USD"),
        volume_mwh=3.5,
    )
    source = _FakeMarketPriceRecordSource((first, second))
    result = await MarketMonitoringAgent(source).run(_request())
    assert result.records == (first, second)
    assert result.records is source.records or result.records == source.records
    assert len(source.calls) == 1
    assert result.records[1].price.currency == "USD"
    assert result.records[1].volume_mwh == 3.5


async def test_run_empty_source_result_is_valid() -> None:
    result = await MarketMonitoringAgent(_FakeMarketPriceRecordSource()).run(_request())
    assert result == MarketMonitoringResult(records=())


async def test_run_does_not_generate_price_forecasts() -> None:
    record = _market()
    result = await MarketMonitoringAgent(_FakeMarketPriceRecordSource((record,))).run(_request())
    assert result.records == (record,)
    assert all(isinstance(item, MarketPriceRecord) for item in result.records)
    assert not any(isinstance(item, PriceForecastPoint) for item in result.records)


async def test_run_propagates_dependency_unavailable_without_retry() -> None:
    error = DependencyUnavailableError("market price source unavailable")
    source = _FakeMarketPriceRecordSource(error=error)
    agent = MarketMonitoringAgent(source)
    with pytest.raises(
        DependencyUnavailableError, match="market price source unavailable"
    ) as caught:
        await agent.run(_request())
    assert caught.value is error
    assert len(source.calls) == 1
