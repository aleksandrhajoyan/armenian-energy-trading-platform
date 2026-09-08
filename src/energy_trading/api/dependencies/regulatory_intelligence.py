"""Request-scoped Regulatory Intelligence query-execution accessor.

This module reads the lifespan-scoped service from FastAPI application state.
It does not own lifecycle, invoke the service, or install a route.
"""

from fastapi import Request

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.orchestration.regulatory_intelligence_query_execution import (
    RegulatoryIntelligenceQueryExecutionService,
)

_SERVICE_ATTR = "regulatory_intelligence_query_execution_service"
_MISSING = object()
_UNAVAILABLE_MESSAGE = "Regulatory Intelligence service is unavailable."


def get_regulatory_intelligence_query_execution_service(
    request: Request,
) -> RegulatoryIntelligenceQueryExecutionService:
    """Return the exact lifespan-scoped Regulatory query-execution service.

    Missing or invalid application state fails closed as
    ``DependencyUnavailableError``. The service is not invoked.
    """

    service = getattr(request.app.state, _SERVICE_ATTR, _MISSING)
    if not isinstance(service, RegulatoryIntelligenceQueryExecutionService):
        raise DependencyUnavailableError(_UNAVAILABLE_MESSAGE)
    return service
