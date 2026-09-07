"""Canonical news event source application-port contract."""

from __future__ import annotations

import inspect
from datetime import UTC, datetime

import pytest

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.ports import NewsEventSourcePort
from energy_trading.domain.models.observations import NewsEvent, NewsSeverity


class _FakeNewsEventSource:
    """Test-only fake that structurally satisfies ``NewsEventSourcePort``.

    Not a production adapter. Does not inherit a production or infrastructure
    base class.
    """

    def __init__(
        self,
        records: tuple[NewsEvent, ...] = (),
        *,
        unavailable: bool = False,
    ) -> None:
        self.records = records
        self.unavailable = unavailable
        self.calls: list[tuple[datetime, datetime]] = []

    async def fetch(
        self,
        *,
        horizon_start: datetime,
        horizon_end: datetime,
    ) -> tuple[NewsEvent, ...]:
        self.calls.append((horizon_start, horizon_end))
        if self.unavailable:
            msg = "news source unavailable"
            raise DependencyUnavailableError(msg)
        return self.records


def _as_news_source(source: _FakeNewsEventSource) -> NewsEventSourcePort:
    return source


def _news(**overrides: object) -> NewsEvent:
    values: dict[str, object] = {
        "event_id": "evt-1",
        "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
        "headline": "Unit outage announced",
        "summary": "A generating unit is scheduled offline.",
    }
    values.update(overrides)
    return NewsEvent.model_validate(values)


def test_structural_fake_does_not_inherit_production_base() -> None:
    assert NewsEventSourcePort not in _FakeNewsEventSource.__mro__
    assert not any(
        base.__name__ in {"NewsEventSourcePort", "Protocol"}
        for base in _FakeNewsEventSource.__bases__
    )


def test_fake_provides_async_fetch() -> None:
    fake = _FakeNewsEventSource()
    port = _as_news_source(fake)
    assert inspect.iscoroutinefunction(port.fetch)
    parameters = inspect.signature(_FakeNewsEventSource.fetch).parameters
    assert tuple(parameters) == ("self", "horizon_start", "horizon_end")
    assert parameters["horizon_start"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["horizon_end"].kind is inspect.Parameter.KEYWORD_ONLY


async def test_canonical_horizons_are_accepted() -> None:
    fake = _FakeNewsEventSource()
    port = _as_news_source(fake)
    start = datetime(2026, 10, 1, 0, tzinfo=UTC)
    end = datetime(2026, 10, 2, 0, tzinfo=UTC)
    result = await port.fetch(horizon_start=start, horizon_end=end)
    assert result == ()
    assert fake.calls == [(start, end)]


async def test_empty_tuple_is_valid() -> None:
    port = _as_news_source(_FakeNewsEventSource())
    result = await port.fetch(
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )
    assert result == ()
    assert isinstance(result, tuple)


async def test_one_canonical_record_is_valid() -> None:
    record = _news()
    port = _as_news_source(_FakeNewsEventSource((record,)))
    result = await port.fetch(
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )
    assert result == (record,)
    assert all(isinstance(item, NewsEvent) for item in result)


async def test_multiple_canonical_records_preserve_order() -> None:
    first = _news(timestamp=datetime(2026, 10, 1, 10, tzinfo=UTC))
    second = _news(
        event_id="evt-2",
        timestamp=datetime(2026, 10, 1, 11, tzinfo=UTC),
        headline="Load advisory issued",
        summary="Operators published a qualitative load advisory.",
    )
    port = _as_news_source(_FakeNewsEventSource((first, second)))
    result = await port.fetch(
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )
    assert result == (first, second)


async def test_canonical_text_and_optional_fields_pass_through_unchanged() -> None:
    record = _news(
        headline="Maintenance window published",
        summary="An operator described a planned maintenance window.",
        category="outage",
        severity=NewsSeverity.HIGH,
    )
    port = _as_news_source(_FakeNewsEventSource((record,)))
    result = await port.fetch(
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )
    assert result == (record,)
    passed = result[0]
    assert passed.headline == "Maintenance window published"
    assert passed.summary == "An operator described a planned maintenance window."
    assert passed.category == "outage"
    assert passed.severity is NewsSeverity.HIGH


async def test_fake_can_represent_dependency_unavailable() -> None:
    fake = _FakeNewsEventSource(unavailable=True)
    port = _as_news_source(fake)
    with pytest.raises(DependencyUnavailableError, match="news source unavailable"):
        await port.fetch(
            horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
            horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
        )
    assert len(fake.calls) == 1
