"""Process/application health. Does not probe infrastructure."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from energy_trading.shared.config.settings import AppEnvironment, AppSettings, get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Liveness of this process only — not databases, caches, or models."""

    status: Literal["ok"] = Field(description="Process is serving HTTP.")
    service: str = Field(description="Configured application name.")
    environment: AppEnvironment = Field(description="Configured application environment.")


@router.get("/health", response_model=HealthResponse)
async def get_health(
    settings: Annotated[AppSettings, Depends(get_settings)],
) -> HealthResponse:
    """Return process health derived from application settings only."""

    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.environment,
    )
