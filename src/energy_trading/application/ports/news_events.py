"""Application-owned canonical news event source boundary.

Future infrastructure adapters acquire RSS, API, or scraped news payloads,
normalize them through the Anti-Corruption Layer, and return already-canonical
``NewsEvent`` values. This module is the only application-facing seam the
News Intelligence Agent may call.

Ownership:

* Application: owns ``NewsEventSourcePort``.
* Future infrastructure adapter: structurally implements the protocol.
  Provider identity, credentials, HTTP clients, file paths, HTML, RSS, and
  raw schemas remain infrastructure concerns. There is no infrastructure
  base class.
* Persistence, cache, retry, graph wiring, scraping, summarization,
  sentiment/relevance/impact inference, embeddings, Qdrant, ML, and LLM
  remain deferred.

Returned tuples are already canonical. This port does not scrape, parse
HTML or feeds, sort, filter, deduplicate, summarize, classify, infer
sentiment, relevance, or market impact, fabricate missing events, or assume
an Armenian DAM interval. An empty tuple is a valid successful result.
Tuple order is the order returned by the future implementation.

Expected unavailable backends use existing application errors such as
``DependencyUnavailableError``. There is no News-specific error hierarchy.
"""

from typing import Protocol

from energy_trading.domain.models.observations import NewsEvent
from energy_trading.domain.value_objects.time import UtcDateTime


class NewsEventSourcePort(Protocol):
    """Application-owned source of canonical news events for one horizon.

    Implementations satisfy this protocol structurally. The application
    depends on the protocol, never on a concrete news provider, HTTP
    client, scraper, or feed parser.

    ``fetch`` accepts only explicit UTC horizon bounds. It must not accept
    provider names, credentials, URLs, keywords, prompts, raw payloads,
    retry parameters, cache keys, or persistence handles. Canonical
    ``NewsEvent`` is not entity-scoped, so this port has no location,
    resource, or asset identifier.
    """

    async def fetch(
        self,
        *,
        horizon_start: UtcDateTime,
        horizon_end: UtcDateTime,
    ) -> tuple[NewsEvent, ...]:
        """Return canonical news events for one horizon.

        An empty tuple is a valid successful result. Implementations must
        not raise merely because the source contained no events.
        """
        ...
