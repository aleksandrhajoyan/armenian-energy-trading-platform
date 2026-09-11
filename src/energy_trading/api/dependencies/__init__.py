"""Request-scoped API accessors for published application services."""

from energy_trading.api.dependencies.document_vector_index import (
    get_document_vector_index_execution_service,
)
from energy_trading.api.dependencies.regulatory_intelligence import (
    get_regulatory_intelligence_query_execution_service,
)

__all__ = [
    "get_document_vector_index_execution_service",
    "get_regulatory_intelligence_query_execution_service",
]
