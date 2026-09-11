"""Request-scoped Document Vector Index execution accessor.

This module reads the lifespan-scoped service from FastAPI application state.
It does not own lifecycle, invoke the service, or install a route.
"""

from fastapi import Request

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.orchestration.document_vector_index_execution import (
    DocumentVectorIndexExecutionService,
)

_SERVICE_ATTR = "document_vector_index_execution_service"
_MISSING = object()
_UNAVAILABLE_MESSAGE = "Document Vector Index service is unavailable."


def get_document_vector_index_execution_service(
    request: Request,
) -> DocumentVectorIndexExecutionService:
    """Return the exact lifespan-scoped Document Vector Index execution service.

    Missing or invalid application state fails closed as
    ``DependencyUnavailableError``. The service is not invoked.
    """

    service = getattr(request.app.state, _SERVICE_ATTR, _MISSING)
    if not isinstance(service, DocumentVectorIndexExecutionService):
        raise DependencyUnavailableError(_UNAVAILABLE_MESSAGE)
    return service
