"""Canonical market price record source application-port contract."""

from __future__ import annotations

import inspect
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.ports import MarketPriceRecordSourcePort
from energy_trading.domain.models.observations import MarketPriceRecord
from energy_trading.domain.value_objects.money import EnergyPrice


class _FakeMarketPriceRecordSource:
    """Test-only fake that structurally satisfies ``MarketPriceRecordSourcePort``.

    Not a production adapter. Does not inherit a production or infrastructure
    base class.
    """

    def __init__(
        self,
        records: tuple[MarketPriceRecord, ...] = (),
        *,
        unavailable: bool = False,
    ) -> None:
        self.records = records
        self.unavailable = unavailable
        self.calls: list[tuple[str, datetime, datetime]] = []

    async def fetch(
        self,
        *,
        market_id: str,
        horizon_start: datetime,
        horizon_end: datetime,
    ) -> tuple[MarketPriceRecord, ...]:
        self.calls.append((market_id, horizon_start, horizon_end))
        if self.unavailable:
            msg = "market price source unavailable"
            raise DependencyUnavailableError(msg)
        return self.records


def _as_market_source(source: _FakeMarketPriceRecordSource) -> MarketPriceRecordSourcePort:
    return source


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


def test_structural_fake_does_not_inherit_production_base() -> None:
    assert MarketPriceRecordSourcePort not in _FakeMarketPriceRecordSource.__mro__
    assert not any(
        base.__name__ in {"MarketPriceRecordSourcePort", "Protocol"}
        for base in _FakeMarketPriceRecordSource.__bases__
    )


def test_fake_provides_async_keyword_only_fetch() -> None:
    fake = _FakeMarketPriceRecordSource()
    port = _as_market_source(fake)
    assert inspect.iscoroutinefunction(port.fetch)
    parameters = inspect.signature(_FakeMarketPriceRecordSource.fetch).parameters
    assert tuple(parameters) == ("self", "market_id", "horizon_start", "horizon_end")
    assert parameters["market_id"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["horizon_start"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["horizon_end"].kind is inspect.Parameter.KEYWORD_ONLY


async def test_canonical_market_id_and_horizons_are_accepted() -> None:
    fake = _FakeMarketPriceRecordSource()
    port = _as_market_source(fake)
    start = datetime(2026, 10, 1, 0, tzinfo=UTC)
    end = datetime(2026, 10, 2, 0, tzinfo=UTC)
    result = await port.fetch(
        market_id="market-1",
        horizon_start=start,
        horizon_end=end,
    )
    assert result == ()
    assert fake.calls == [("market-1", start, end)]


async def test_empty_tuple_is_valid() -> None:
    port = _as_market_source(_FakeMarketPriceRecordSource())
    result = await port.fetch(
        market_id="market-1",
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )
    assert result == ()
    assert isinstance(result, tuple)


async def test_one_canonical_record_is_valid() -> None:
    record = _market()
    port = _as_market_source(_FakeMarketPriceRecordSource((record,)))
    result = await port.fetch(
        market_id="market-1",
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )
    assert result == (record,)
    assert all(isinstance(item, MarketPriceRecord) for item in result)


async def test_multiple_canonical_records_preserve_order() -> None:
    first = _market(timestamp=datetime(2026, 10, 1, 10, tzinfo=UTC))
    second = _market(
        timestamp=datetime(2026, 10, 1, 11, tzinfo=UTC),
        price=_price("51.25", "USD"),
        volume_mwh=8.0,
    )
    port = _as_market_source(_FakeMarketPriceRecordSource((first, second)))
    result = await port.fetch(
        market_id="market-1",
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )
    assert result == (first, second)


async def test_energy_price_and_explicit_currency_pass_through_unchanged() -> None:
    price = _price("62.50", "USD")
    record = _market(price=price)
    port = _as_market_source(_FakeMarketPriceRecordSource((record,)))
    result = await port.fetch(
        market_id="market-1",
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )
    assert result == (record,)
    passed = result[0]
    assert passed.price is price
    assert passed.price.amount_per_mwh == Decimal("62.50")
    assert passed.price.currency == "USD"


async def test_optional_volume_passes_through_unchanged() -> None:
    record = _market(volume_mwh=12.5)
    port = _as_market_source(_FakeMarketPriceRecordSource((record,)))
    result = await port.fetch(
        market_id="market-1",
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )
    assert result == (record,)
    assert result[0].volume_mwh == 12.5


async def test_missing_optional_volume_stays_none() -> None:
    record = _market()
    port = _as_market_source(_FakeMarketPriceRecordSource((record,)))
    result = await port.fetch(
        market_id="market-1",
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )
    assert result == (record,)
    assert result[0].volume_mwh is None


async def test_fake_can_represent_dependency_unavailable() -> None:
    fake = _FakeMarketPriceRecordSource(unavailable=True)
    port = _as_market_source(fake)
    with pytest.raises(DependencyUnavailableError, match="market price source unavailable"):
        await port.fetch(
            market_id="market-1",
            horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
            horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
        )
    assert len(fake.calls) == 1
