"""FastAPI application factory (HTTP composition root)."""

from fastapi import FastAPI

from energy_trading import __version__
from energy_trading.api.routers.health import router as health_router
from energy_trading.shared.config.settings import AppSettings, get_settings


def create_app(settings: AppSettings | None = None) -> FastAPI:
    """Build a FastAPI application without initializing external systems.

    Passing ``settings`` overrides the default provider so tests do not depend
    on process-wide cached configuration or a local ``.env`` file.
    """

    resolved_settings = settings if settings is not None else get_settings()
    application = FastAPI(
        title=resolved_settings.app_name,
        version=__version__,
    )
    application.include_router(health_router, prefix=resolved_settings.api_prefix)

    if settings is not None:

        def override_settings() -> AppSettings:
            return resolved_settings

        application.dependency_overrides[get_settings] = override_settings

    return application


app = create_app()
