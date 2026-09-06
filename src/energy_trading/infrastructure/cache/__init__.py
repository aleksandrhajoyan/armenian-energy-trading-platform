"""Ephemeral Redis cache infrastructure.

This package exposes the async Redis client factory and ``RedisCache``.
It does not create a global client or connect on import. Future composition
roots own client lifecycle (``aclose``) and wiring.
"""

from energy_trading.infrastructure.cache.codec import CacheCodec, CacheCodecError
from energy_trading.infrastructure.cache.redis_cache import RedisCache
from energy_trading.infrastructure.cache.redis_client import create_redis_client

__all__ = [
    "CacheCodec",
    "CacheCodecError",
    "RedisCache",
    "create_redis_client",
]
