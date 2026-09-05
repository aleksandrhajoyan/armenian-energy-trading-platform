"""Application-owned ephemeral cache boundary.

This module defines a vendor-neutral cache port. A later infrastructure
adapter may implement it with Redis (ADR-006) or another store. Chunk 16
adds no concrete cache, Redis client, serializer, or composition wiring.

Ownership:

* Application: owns ``CachePort[TValue]`` and the cache semantics below.
* Infrastructure (future): implements the protocol structurally, including
  serialization and backend I/O. There is no infrastructure base class.
* PostgreSQL/TimescaleDB remains the system of record. Cache entries are
  ephemeral, TTL-bound, and may be lost or expire without recovery.

This port is ordinary cache behavior only. It is not an orchestration-state
contract (no CAS/versioning/atomic workflow updates) and not a distributed
lock or lease contract. Those concerns, if needed later, require separate
purpose-specific application ports.

The cache is not approved for secret storage. Keys and values must not carry
credentials, authorization headers, cookies, API keys, passwords, raw CSV or
Excel rows, document bytes, vendor JSON, or source payload blobs.
"""

from datetime import timedelta
from typing import Protocol


class CachePort[TValue](Protocol):
    """Application-owned generic cache.

    Infrastructure implementations satisfy this protocol structurally. The
    application depends on the protocol, never on a concrete adapter or Redis
    type.

    ``key`` is an opaque application cache identifier. After surrounding
    whitespace is ignored it must be non-empty. The contract does not
    prescribe Redis key syntax, prefixes, hashes, database numbers, cluster
    slots, vendor namespaces, or hashing algorithms.

    ``TValue`` is the statically typed cached value. The application layer
    does not serialize. Serialization, bytes, JSON dictionaries, and Redis
    response types belong to a future infrastructure implementation.

    Every ``set`` requires an explicit ``timedelta`` TTL that is strictly
    greater than zero. There is no non-expiring entry API: cache state must
    not accidentally become an alternative system of record. The contract
    does not use Redis expiry types or integer-millisecond conventions.

    Conforming implementations treat invalid caller input (blank key or
    non-positive TTL) as ``InvalidRequestError``. A concrete adapter must
    translate expected cache/backend unavailability into
    ``DependencyUnavailableError``. Redis-specific application errors are
    not part of this boundary.
    """

    async def get(self, key: str) -> TValue | None:
        """Return the typed cached value when present and still live.

        A missing or expired entry returns ``None``. A normal cache miss is
        not an exception.
        """
        ...

    async def set(
        self,
        key: str,
        value: TValue,
        *,
        ttl: timedelta,
    ) -> None:
        """Store ``value`` under ``key`` for the supplied positive TTL.

        An existing cached value for the same key may be replaced. Replacement
        also establishes the newly supplied TTL. This overwrite applies to
        cache data only and is not a safe compare-and-set for authoritative
        orchestration state.
        """
        ...

    async def delete(self, key: str) -> None:
        """Remove ``key`` if present.

        Deleting a missing or expired key is a successful no-op.
        """
        ...
