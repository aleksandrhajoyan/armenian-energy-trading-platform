"""HTTP API error envelope. Transport-specific; not a domain contract."""

from pydantic import BaseModel, ConfigDict, Field


class ApiErrorDetail(BaseModel):
    """Sanitized validation detail. Raw input values are never included."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    field: str
    message: str
    type: str


class ApiError(BaseModel):
    """Machine-readable error body included in every API error response."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    message: str
    correlation_id: str
    details: tuple[ApiErrorDetail, ...] | None = Field(default=None)


class ApiErrorResponse(BaseModel):
    """Standard API error envelope."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    error: ApiError
