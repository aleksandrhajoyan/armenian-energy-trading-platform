"""Shared helpers for API unit tests."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from energy_trading.api.app import create_app
from energy_trading.shared.config.settings import AppEnvironment, AppSettings


def make_test_settings(
    *,
    app_name: str = "AI Energy Trading Platform",
    environment: AppEnvironment = AppEnvironment.TEST,
    api_prefix: str = "/api/v1",
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO",
) -> AppSettings:
    return AppSettings(
        _env_file=None,
        app_name=app_name,
        environment=environment,
        api_prefix=api_prefix,
        log_level=log_level,
    )


@asynccontextmanager
async def api_client(
    application: FastAPI | None = None,
    *,
    raise_app_exceptions: bool = True,
) -> AsyncIterator[AsyncClient]:
    app = application if application is not None else create_app(make_test_settings())
    transport = ASGITransport(app=app, raise_app_exceptions=raise_app_exceptions)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
