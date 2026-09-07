"""Application-owned canonical market price record source boundary.

Future infrastructure adapters acquire official or operator-published market
reports, files, or APIs, normalize them through the Anti-Corruption Layer,
and return already-canonical ``MarketPriceRecord`` values. This module is
the only application-facing seam the Market Monitoring Agent may call.

Ownership:

* Application: owns ``MarketPriceRecordSourcePort``.
* Future infrastructure adapter: structurally implements the protocol.
  Provider identity, credentials, HTTP clients, file paths, and raw schemas
  remain infrastructure concerns. There is no infrastructure base class.
* Persistence, cache, retry, graph wiring, market-status objects, currency
  conversion, interval/cadence inference, market clearing, and price
  forecasting remain deferred.

Returned tuples are already canonical. This port does not sort,
interpolate, resample, resolve duplicates, fill missing hours, infer
cadence or interval duration, convert currency, default a currency,
forecast prices, clear the market, infer market status, or fabricate
missing prices. An empty tuple is a valid successful result. Tuple order
is the order returned by the future implementation.

Expected unavailable backends use existing application errors such as
``DependencyUnavailableError``. There is no Market-specific error hierarchy.
"""

from typing import Protocol

from energy_trading.domain.models.observations import MarketPriceRecord
from energy_trading.domain.value_objects.quantities import EntityId
from energy_trading.domain.value_objects.time import UtcDateTime


class MarketPriceRecordSourcePort(Protocol):
    """Application-owned source of canonical observed market prices.

    Implementations satisfy this protocol structurally. The application
    depends on the protocol, never on a concrete market operator, HTTP
    client, or file adapter.

    ``fetch`` accepts only an opaque market identifier and explicit UTC
    horizon bounds. It must not accept provider names, credentials, URLs,
    raw payloads, currency overrides, interval/cadence, retry parameters,
    cache keys, or persistence handles.
    """

    async def fetch(
        self,
        *,
        market_id: EntityId,
        horizon_start: UtcDateTime,
        horizon_end: UtcDateTime,
    ) -> tuple[MarketPriceRecord, ...]:
        """Return canonical observed market prices for one market and horizon.

        An empty tuple is a valid successful result. Implementations must
        not raise merely because the source contained no points.
        """
        ...
