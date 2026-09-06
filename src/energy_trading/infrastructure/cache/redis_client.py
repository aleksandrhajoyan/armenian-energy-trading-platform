"""Async Redis client factory.

Construction does not open a network connection or issue a command. A future
composition root owns the shared client lifecycle and must call
``await client.aclose()``. This factory does not close the client.
"""

from redis.asyncio import Redis

from energy_trading.shared.config.redis import RedisSettings


def create_redis_client(settings: RedisSettings) -> Redis:
    """Return an async redis-py client without connecting.

    Credentials are passed as constructor keywords. Callers must not build or
    log a password-bearing Redis DSN.
    """

    password: str | None = None
    if settings.password is not None:
        password = settings.password.get_secret_value()
    return Redis(
        host=settings.host,
        port=settings.port,
        db=settings.db,
        password=password,
        ssl=settings.ssl,
        socket_timeout=settings.socket_timeout_seconds,
        socket_connect_timeout=settings.socket_timeout_seconds,
        max_connections=settings.max_connections,
        decode_responses=False,
    )
