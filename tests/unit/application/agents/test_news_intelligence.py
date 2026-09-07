"""News Intelligence Agent application contract."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime, timedelta, timezone

import pytest

from energy_trading.application.agents.base import AgentName, AgentPort
from energy_trading.application.agents.news_intelligence import (
    NewsIntelligenceAgent,
    NewsIntelligenceRequest,
    NewsIntelligenceResult,
)
from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.domain.models.observations import NewsEvent, NewsSeverity


class _FakeNewsEventSource:
    """Test-only source fake. Not a production adapter."""

    def __init__(
        self,
        records: tuple[NewsEvent, ...] = (),
        *,
        error: Exception | None = None,
    ) -> None:
        self.records = records
        self.error = error
        self.calls: list[tuple[datetime, datetime]] = []

    async def fetch(
        self,
        *,
        horizon_start: datetime,
        horizon_end: datetime,
    ) -> tuple[NewsEvent, ...]:
        self.calls.append((horizon_start, horizon_end))
        if self.error is not None:
            raise self.error
        return self.records


def _as_agent_port(
    agent: NewsIntelligenceAgent,
) -> AgentPort[NewsIntelligenceRequest, NewsIntelligenceResult]:
    """Mypy-visible structural assignment to the shared agent port."""

    return agent


def _news(**overrides: object) -> NewsEvent:
    values: dict[str, object] = {
        "event_id": "evt-1",
        "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
        "headline": "Unit outage announced",
        "summary": "A generating unit is scheduled offline.",
    }
    values.update(overrides)
    return NewsEvent.model_validate(values)


def _request(**overrides: object) -> NewsIntelligenceRequest:
    values: dict[str, object] = {
        "horizon_start": datetime(2026, 10, 1, 0, tzinfo=UTC),
        "horizon_end": datetime(2026, 10, 2, 0, tzinfo=UTC),
    }
    values.update(overrides)
    return NewsIntelligenceRequest(**values)  # type: ignore[arg-type]


def test_request_accepts_utc_horizon() -> None:
    request = _request()
    assert request.horizon_start == datetime(2026, 10, 1, 0, tzinfo=UTC)
    assert request.horizon_end == datetime(2026, 10, 2, 0, tzinfo=UTC)
    assert request.horizon_start.tzinfo is UTC
    assert request.horizon_end.tzinfo is UTC


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
    assert hasattr(NewsIntelligenceRequest, "__slots__")
    with pytest.raises(FrozenInstanceError):
        request.horizon_start = datetime(2026, 10, 1, 1, tzinfo=UTC)  # type: ignore[misc]
    field_names = tuple(item.name for item in fields(NewsIntelligenceRequest))
    assert field_names == ("horizon_start", "horizon_end")


def test_request_rejects_unrequested_fields() -> None:
    with pytest.raises(TypeError):
        NewsIntelligenceRequest(
            horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
            horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
            provider="newsapi",  # type: ignore[call-arg]
        )


def test_result_empty_tuple_is_valid() -> None:
    result = NewsIntelligenceResult(records=())
    assert result.records == ()
    assert isinstance(result.records, tuple)


def test_result_accepts_one_news_event() -> None:
    record = _news()
    result = NewsIntelligenceResult(records=(record,))
    assert result.records == (record,)


def test_result_preserves_multiple_record_order() -> None:
    first = _news(timestamp=datetime(2026, 10, 1, 11, tzinfo=UTC))
    second = _news(
        event_id="evt-2",
        timestamp=datetime(2026, 10, 1, 10, tzinfo=UTC),
        headline="Advisory published",
        summary="A qualitative market advisory was published.",
    )
    result = NewsIntelligenceResult(records=(first, second))
    assert result.records == (first, second)


def test_result_canonical_fields_remain_unchanged() -> None:
    record = _news(
        headline="Maintenance window published",
        summary="An operator described a planned maintenance window.",
        category="outage",
        severity=NewsSeverity.MEDIUM,
    )
    result = NewsIntelligenceResult(records=(record,))
    passed = result.records[0]
    assert passed is record
    assert passed.headline == "Maintenance window published"
    assert passed.summary == "An operator described a planned maintenance window."
    assert passed.category == "outage"
    assert passed.severity is NewsSeverity.MEDIUM


def test_result_rejects_mutable_records_collection() -> None:
    with pytest.raises(TypeError, match="records must be an immutable tuple"):
        NewsIntelligenceResult(records=[_news()])  # type: ignore[arg-type]


def test_result_rejects_non_news_event_values() -> None:
    with pytest.raises(TypeError, match="records must contain NewsEvent values"):
        NewsIntelligenceResult(records=("not-news",))  # type: ignore[arg-type]


def test_result_is_frozen() -> None:
    result = NewsIntelligenceResult(records=())
    assert hasattr(NewsIntelligenceResult, "__slots__")
    with pytest.raises(FrozenInstanceError):
        result.records = ()  # type: ignore[misc]


def test_agent_does_not_inherit_agent_port() -> None:
    assert AgentPort not in NewsIntelligenceAgent.__mro__
    assert not any(base.__name__ == "AgentPort" for base in NewsIntelligenceAgent.__bases__)


def test_agent_name_is_canonical_news_identity() -> None:
    agent = NewsIntelligenceAgent(_FakeNewsEventSource())
    port = _as_agent_port(agent)
    assert port.name is AgentName.NEWS_INTELLIGENCE
    assert port.name.value == "News Intelligence Agent"


async def test_run_invokes_source_once_with_normalized_values() -> None:
    source = _FakeNewsEventSource()
    agent = NewsIntelligenceAgent(source)
    offset = timezone(timedelta(hours=4))
    result = await _as_agent_port(agent).run(
        NewsIntelligenceRequest(
            horizon_start=datetime(2026, 10, 1, 4, tzinfo=offset),
            horizon_end=datetime(2026, 10, 1, 8, tzinfo=offset),
        )
    )
    assert result.records == ()
    assert len(source.calls) == 1
    horizon_start, horizon_end = source.calls[0]
    assert horizon_start == datetime(2026, 10, 1, 0, tzinfo=UTC)
    assert horizon_end == datetime(2026, 10, 1, 4, tzinfo=UTC)


async def test_run_wraps_source_tuple_without_reordering() -> None:
    first = _news(timestamp=datetime(2026, 10, 1, 12, tzinfo=UTC))
    second = _news(
        event_id="evt-2",
        timestamp=datetime(2026, 10, 1, 8, tzinfo=UTC),
        headline="Advisory published",
        summary="A qualitative market advisory was published.",
        category="market",
        severity=NewsSeverity.LOW,
    )
    source = _FakeNewsEventSource((first, second))
    result = await NewsIntelligenceAgent(source).run(_request())
    assert result.records == (first, second)
    assert result.records is source.records or result.records == source.records
    assert len(source.calls) == 1


async def test_run_empty_source_result_is_valid() -> None:
    result = await NewsIntelligenceAgent(_FakeNewsEventSource()).run(_request())
    assert result == NewsIntelligenceResult(records=())


async def test_run_propagates_dependency_unavailable_without_retry() -> None:
    error = DependencyUnavailableError("news source unavailable")
    source = _FakeNewsEventSource(error=error)
    agent = NewsIntelligenceAgent(source)
    with pytest.raises(DependencyUnavailableError, match="news source unavailable") as caught:
        await agent.run(_request())
    assert caught.value is error
    assert len(source.calls) == 1
