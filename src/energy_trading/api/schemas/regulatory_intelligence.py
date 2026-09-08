"""HTTP transport contracts for Regulatory Intelligence query.

These models project the published query-execution input
(``query_text``, ``limit``) and the published
``RegulatoryIntelligenceResult`` constraint payload. They do not invoke
the service, own lifecycle, or install a route.
"""

from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

_PositiveLimit = Annotated[int, Field(gt=0)]
_NonEmptyText = Annotated[str, Field(min_length=1)]
_FiniteValue = Annotated[float, Field(allow_inf_nan=False)]
_CurrencyCode = Annotated[str, Field(pattern=r"^[A-Z]{3}$", min_length=3, max_length=3)]


class RegulatoryIntelligenceQueryRequest(BaseModel):
    """HTTP body for a future Regulatory Intelligence query.

    Mirrors ``RegulatoryIntelligenceQueryExecutionService.execute``:
    required ``query_text`` and a positive ``limit``. Query text is not
    stripped. Limit positivity follows ``DocumentVectorSearchQuery``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    query_text: str
    limit: _PositiveLimit


class RegulatoryConstraintResponse(BaseModel):
    """HTTP projection of canonical ``RegulatoryConstraint`` fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    constraint_id: _NonEmptyText
    constraint_type: _NonEmptyText
    description: _NonEmptyText
    effective_from: date
    effective_to: date | None = None
    minimum_value: _FiniteValue | None = None
    maximum_value: _FiniteValue | None = None
    unit: _NonEmptyText | None = None
    currency: _CurrencyCode | None = None
    source_document_id: _NonEmptyText | None = None


class RegulatoryIntelligenceQueryResponse(BaseModel):
    """HTTP body projecting ``RegulatoryIntelligenceResult.constraints``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    constraints: tuple[RegulatoryConstraintResponse, ...]
