"""Infrastructure-local cache serialization boundary.

Application cache values stay statically typed. Redis stores bytes. Encoding
and decoding belong here, not on ``CachePort``. There is no default unsafe
serializer: a concrete ``CacheCodec[TValue]`` is injected into the adapter.
"""

from typing import Protocol


class CacheCodecError(Exception):
    """Infrastructure-local codec failure.

    This type must not appear on ``CachePort``. Callers of the Redis adapter
    observe ``DependencyUnavailableError`` instead.
    """


class CacheCodec[TValue](Protocol):
    """Encode and decode a typed cache value as Redis bytes.

    Implementations satisfy this protocol structurally. There is no
    infrastructure base class and no executable object-serialization path.
    """

    def encode(self, value: TValue) -> bytes:
        """Serialize ``value`` to Redis payload bytes."""
        ...

    def decode(self, payload: bytes) -> TValue:
        """Deserialize Redis payload bytes to a typed value."""
        ...
