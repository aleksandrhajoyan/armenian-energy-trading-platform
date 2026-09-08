"""Regulatory Intelligence HTTP query route.

This module is a thin transport boundary. It binds the published request DTO,
resolves the published query-execution service through FastAPI ``Depends``,
invokes ``execute`` once, and projects canonical constraints into the
existing response DTO. Production ``create_app()`` does not install it.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from energy_trading.api.dependencies.regulatory_intelligence import (
    get_regulatory_intelligence_query_execution_service,
)
from energy_trading.api.schemas.regulatory_intelligence import (
    RegulatoryConstraintResponse,
    RegulatoryIntelligenceQueryRequest,
    RegulatoryIntelligenceQueryResponse,
)
from energy_trading.application.orchestration.regulatory_intelligence_query_execution import (
    RegulatoryIntelligenceQueryExecutionService,
)

router = APIRouter(prefix="/regulatory-intelligence", tags=["regulatory-intelligence"])


@router.post("/query", response_model=RegulatoryIntelligenceQueryResponse)
async def query_regulatory_intelligence(
    request: RegulatoryIntelligenceQueryRequest,
    service: Annotated[
        RegulatoryIntelligenceQueryExecutionService,
        Depends(get_regulatory_intelligence_query_execution_service),
    ],
) -> RegulatoryIntelligenceQueryResponse:
    """Execute a Regulatory Intelligence query and return HTTP constraint DTOs."""

    result = await service.execute(
        query_text=request.query_text,
        limit=request.limit,
    )
    return RegulatoryIntelligenceQueryResponse(
        constraints=tuple(
            RegulatoryConstraintResponse(
                constraint_id=constraint.constraint_id,
                constraint_type=constraint.constraint_type,
                description=constraint.description,
                effective_from=constraint.effective_from,
                effective_to=constraint.effective_to,
                minimum_value=constraint.minimum_value,
                maximum_value=constraint.maximum_value,
                unit=constraint.unit,
                currency=constraint.currency,
                source_document_id=constraint.source_document_id,
            )
            for constraint in result.constraints
        )
    )
