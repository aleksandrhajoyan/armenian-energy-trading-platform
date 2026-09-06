"""Application-owned canonical hydro record source boundary.

Future infrastructure adapters acquire hydro telemetry or operator files,
normalize them through the Anti-Corruption Layer, and return already-canonical
``HydroRecord`` values. This module is the only application-facing seam
the Hydro Resources Agent may call.

Ownership:

* Application: owns ``HydroRecordSourcePort``.
* Future infrastructure adapter: structurally implements the protocol.
  Provider identity, credentials, HTTP clients, file paths, and raw schemas
  remain infrastructure concerns. There is no infrastructure base class.
* Persistence, cache, retry, graph wiring, hydrological calculation, and
  Generation Availability coupling remain deferred.

Returned tuples are already canonical. This port does not sort, interpolate,
resample, infer cadence, fabricate missing points, calculate reservoir
behavior or available generation, infer reservoir operating policy, or
assume an Armenian DAM interval. An empty tuple is a valid successful
result. Tuple order is the order returned by the future implementation.

Expected unavailable backends use existing application errors such as
``DependencyUnavailableError``. There is no Hydro-specific error hierarchy.
"""

from typing import Protocol

from energy_trading.domain.models.observations import HydroRecord
from energy_trading.domain.value_objects.quantities import EntityId
from energy_trading.domain.value_objects.time import UtcDateTime


class HydroRecordSourcePort(Protocol):
    """Application-owned source of canonical hydro records for one horizon.

    Implementations satisfy this protocol structurally. The application
    depends on the protocol, never on a concrete hydro provider, HTTP
    client, or file adapter.

    ``fetch`` accepts only an opaque resource identifier and explicit UTC
    horizon bounds. It must not accept provider names, credentials, URLs,
    raw payloads, retry parameters, cache keys, or persistence handles.
    """

    async def fetch(
        self,
        *,
        resource_id: EntityId,
        horizon_start: UtcDateTime,
        horizon_end: UtcDateTime,
    ) -> tuple[HydroRecord, ...]:
        """Return canonical hydro records for one resource and horizon.

        An empty tuple is a valid successful result. Implementations must
        not raise merely because the source contained no points.
        """
        ...
