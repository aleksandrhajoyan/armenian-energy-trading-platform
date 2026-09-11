"""FastAPI application factory (HTTP composition root)."""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from fastapi import FastAPI

from energy_trading import __version__
from energy_trading.api.composition.production_lifespan import (
    build_production_lifespan,
)
from energy_trading.api.exception_handlers import register_exception_handlers
from energy_trading.api.middleware import CorrelationMiddleware, RequestLoggingMiddleware
from energy_trading.api.routers.health import router as health_router
from energy_trading.api.routers.regulatory_intelligence import (
    router as regulatory_intelligence_router,
)
from energy_trading.shared.config.settings import AppSettings, get_settings
from energy_trading.shared.observability.logging import configure_logging


def create_app(
    settings: AppSettings | None = None,
    *,
    lifespan: Callable[[FastAPI], AbstractAsyncContextManager[None]] | None = None,
) -> FastAPI:
    """Build a FastAPI application without initializing external systems.

    Passing ``settings`` overrides the default provider so tests do not depend
    on process-wide cached configuration or a local ``.env`` file.

    Passing ``lifespan`` replaces the production composite lifespan so
    transport tests can stay independent of provider credentials. The default
    installs ``build_production_lifespan`` and includes the published
    Regulatory query router; constructing the app does not load Regulatory or
    document-index settings or create clients.
    """

    resolved_settings = settings if settings is not None else get_settings()
    configure_logging(resolved_settings.log_level)
    resolved_lifespan = lifespan if lifespan is not None else build_production_lifespan()

    application = FastAPI(
        title=resolved_settings.app_name,
        version=__version__,
        lifespan=resolved_lifespan,
    )
    application.add_middleware(RequestLoggingMiddleware)
    application.add_middleware(CorrelationMiddleware)
    register_exception_handlers(application)
    application.include_router(health_router, prefix=resolved_settings.api_prefix)
    application.include_router(
        regulatory_intelligence_router,
        prefix=resolved_settings.api_prefix,
    )

    if settings is not None:

        def override_settings() -> AppSettings:
            return resolved_settings

        application.dependency_overrides[get_settings] = override_settings

    return application


app = create_app()
