"""Async Qdrant HTTP client factory.

Construction does not issue a Qdrant command, version check, or readiness probe.
A future composition root owns the shared client lifecycle and must call
``await client.close()``. This factory does not close the client.
"""

from qdrant_client import AsyncQdrantClient

from energy_trading.shared.config.qdrant import QdrantSettings


def create_qdrant_client(settings: QdrantSettings) -> AsyncQdrantClient:
    """Return an official async Qdrant client without connecting.

    Credentials are passed as constructor keywords. Callers must not build or
    log an API-key-bearing Qdrant URL. Embedding inference stays disabled;
    vectors are produced through ``DocumentEmbeddingPort``.
    """

    api_key: str | None = None
    if settings.api_key is not None:
        api_key = settings.api_key.get_secret_value()
    return AsyncQdrantClient(
        host=settings.host,
        port=settings.port,
        https=settings.https,
        api_key=api_key,
        timeout=settings.timeout_seconds,
        prefer_grpc=False,
        cloud_inference=False,
        check_compatibility=False,
    )
