"""Outer object composition for published application slices."""

from energy_trading.api.composition.regulatory_intelligence import (
    build_regulatory_intelligence_query_execution,
)

__all__ = ["build_regulatory_intelligence_query_execution"]
