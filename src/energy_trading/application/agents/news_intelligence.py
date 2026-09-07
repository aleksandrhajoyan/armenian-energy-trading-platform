"""News Intelligence Agent application boundary.

This module is the fourth concrete application agent. It consumes a typed
request, calls an injected canonical news source port once, and returns
canonical ``NewsEvent`` values. Raw articles, feeds, and vendor payloads
never enter here.

Ownership:

* Application: owns the request/result DTOs and the concrete agent.
* Injected ``NewsEventSourcePort``: supplies already-canonical records.
* Future infrastructure adapter: implements that port. Provider acquisition
  remains outside this module.
* LangGraph, failure-policy execution, persistence, retry, fallback,
  scraping, summarization, sentiment/relevance/impact inference,
  embeddings, Qdrant, ML, and LLM remain deferred.

The agent satisfies ``AgentPort`` structurally. It does not inherit a base
class and is not registered in a factory.
"""

from dataclasses import dataclass
from datetime import datetime

from energy_trading.application.agents.base import AgentName
from energy_trading.application.ports.news_events import NewsEventSourcePort
from energy_trading.domain.models.observations import NewsEvent
from energy_trading.domain.value_objects.time import to_utc


@dataclass(frozen=True, slots=True)
class NewsIntelligenceRequest:
    """Immutable agent request: an explicit UTC horizon.

    This is an application DTO, not a domain entity and not a workflow
    snapshot. Canonical ``NewsEvent`` is temporal and not entity-scoped, so
    the request carries no location, resource, asset, provider, keyword, or
    payload fields.
    """

    horizon_start: datetime
    horizon_end: datetime

    def __post_init__(self) -> None:
        start = _require_aware_utc("horizon_start", self.horizon_start)
        end = _require_aware_utc("horizon_end", self.horizon_end)
        if end <= start:
            msg = "horizon_end must be later than horizon_start"
            raise ValueError(msg)
        object.__setattr__(self, "horizon_start", start)
        object.__setattr__(self, "horizon_end", end)


@dataclass(frozen=True, slots=True)
class NewsIntelligenceResult:
    """Immutable agent result wrapping canonical news events.

    An empty tuple is valid. Ordering is the source tuple order. This DTO
    carries no diagnostics, provider metadata, sentiment, relevance, or
    degraded flags. Canonical headline, summary, optional category, and
    optional severity are passed through unchanged; they are not inferred
    here.
    """

    records: tuple[NewsEvent, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "records", _require_news_events(self.records))


class NewsIntelligenceAgent:
    """Thin application agent over a canonical news event source port.

    ``run`` calls ``NewsEventSourcePort.fetch`` exactly once and wraps the
    returned tuple. It does not sort, filter, summarize, classify, score,
    embed, persist, retry, or call an LLM.
    """

    def __init__(self, source: NewsEventSourcePort) -> None:
        self._source = source

    @property
    def name(self) -> AgentName:
        return AgentName.NEWS_INTELLIGENCE

    async def run(self, request: NewsIntelligenceRequest) -> NewsIntelligenceResult:
        records = await self._source.fetch(
            horizon_start=request.horizon_start,
            horizon_end=request.horizon_end,
        )
        return NewsIntelligenceResult(records=records)


def _require_aware_utc(field_name: str, value: object) -> datetime:
    if not isinstance(value, datetime):
        msg = f"{field_name} must be a datetime"
        raise TypeError(msg)
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        msg = f"{field_name} must be timezone-aware"
        raise ValueError(msg)
    return to_utc(value)


def _require_news_events(value: object) -> tuple[NewsEvent, ...]:
    if not isinstance(value, tuple):
        msg = "records must be an immutable tuple"
        raise TypeError(msg)
    if not all(isinstance(item, NewsEvent) for item in value):
        msg = "records must contain NewsEvent values"
        raise TypeError(msg)
    return value
