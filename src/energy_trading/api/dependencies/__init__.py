"""Request-scoped API accessors for published application services."""

from energy_trading.api.dependencies.regulatory_intelligence import (
    get_regulatory_intelligence_query_execution_service,
)

__all__ = ["get_regulatory_intelligence_query_execution_service"]
