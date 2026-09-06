"""Application-owned canonical generation availability source boundary.

Future infrastructure adapters acquire outage or plant-availability payloads,
normalize them through the Anti-Corruption Layer, and return already-canonical
``GenerationAvailabilityRecord`` values. This module is the only
application-facing seam the Generation Availability Agent may call.

Ownership:

* Application: owns ``GenerationAvailabilityRecordSourcePort``.
* Future infrastructure adapter: structurally implements the protocol.
  Provider identity, credentials, HTTP clients, file paths, and raw schemas
  remain infrastructure concerns. There is no infrastructure base class.
* Persistence, cache, retry, graph wiring, capacity calculation, status
  inference, fleet-completeness policy, and Hydro coupling remain deferred.

Returned tuples are already canonical. This port does not sort, interpolate,
resample, infer cadence, fabricate missing assets or time points, infer
status, calculate ``available_capacity_mw`` or ``total_capacity_mw``, derive
records from Hydro, or assume an Armenian DAM interval. An empty tuple is a
valid successful result. Tuple order is the order returned by the future
implementation.

Expected unavailable backends use existing application errors such as
``DependencyUnavailableError``. There is no Generation-specific error
hierarchy.
"""

from typing import Protocol

from energy_trading.domain.models.observations import GenerationAvailabilityRecord
from energy_trading.domain.value_objects.quantities import EntityId
from energy_trading.domain.value_objects.time import UtcDateTime


class GenerationAvailabilityRecordSourcePort(Protocol):
    """Application-owned source of canonical generation availability records.

    Implementations satisfy this protocol structurally. The application
    depends on the protocol, never on a concrete outage provider, HTTP
    client, or file adapter.

    ``fetch`` accepts only an opaque asset identifier and explicit UTC
    horizon bounds. It must not accept provider names, credentials, URLs,
    raw payloads, retry parameters, cache keys, persistence handles, fleet
    metadata, or Hydro records.
    """

    async def fetch(
        self,
        *,
        asset_id: EntityId,
        horizon_start: UtcDateTime,
        horizon_end: UtcDateTime,
    ) -> tuple[GenerationAvailabilityRecord, ...]:
        """Return canonical generation availability records for one asset and horizon.

        An empty tuple is a valid successful result. Implementations must
        not raise merely because the source contained no points.
        """
        ...
