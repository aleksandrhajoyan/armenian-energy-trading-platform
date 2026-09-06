"""Application-owned canonical weather record source boundary.

Future infrastructure adapters acquire provider weather/renewable payloads,
normalize them through the Anti-Corruption Layer, and return already-canonical
``WeatherRecord`` values. This module is the only application-facing seam
the Weather & Renewable Forecast Agent may call.

Ownership:

* Application: owns ``WeatherRecordSourcePort``.
* Future infrastructure adapter: structurally implements the protocol.
  Provider identity, credentials, HTTP clients, file paths, and raw schemas
  remain infrastructure concerns. There is no infrastructure base class.
* Persistence, cache, retry, and graph wiring remain deferred.

Returned tuples are already canonical. This port does not sort, interpolate,
resample, infer cadence, fabricate missing points, or assume an Armenian DAM
interval. An empty tuple is a valid successful result. Tuple order is the
order returned by the future implementation.

Expected unavailable backends use existing application errors such as
``DependencyUnavailableError``. There is no Weather-specific error hierarchy.
"""

from typing import Protocol

from energy_trading.domain.models.observations import WeatherRecord
from energy_trading.domain.value_objects.quantities import EntityId
from energy_trading.domain.value_objects.time import UtcDateTime


class WeatherRecordSourcePort(Protocol):
    """Application-owned source of canonical weather records for one horizon.

    Implementations satisfy this protocol structurally. The application
    depends on the protocol, never on a concrete weather provider, HTTP
    client, or file adapter.

    ``fetch`` accepts only an opaque location identifier and explicit UTC
    horizon bounds. It must not accept provider names, credentials, URLs,
    raw payloads, retry parameters, cache keys, or persistence handles.
    """

    async def fetch(
        self,
        *,
        location_id: EntityId,
        horizon_start: UtcDateTime,
        horizon_end: UtcDateTime,
    ) -> tuple[WeatherRecord, ...]:
        """Return canonical weather records for one location and horizon.

        An empty tuple is a valid successful result. Implementations must
        not raise merely because the source contained no points.
        """
        ...
