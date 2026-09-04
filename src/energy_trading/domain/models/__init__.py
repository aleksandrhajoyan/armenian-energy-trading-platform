"""Public canonical domain contracts."""

from energy_trading.domain.models.forecasting import LoadForecastPoint, PriceForecastPoint
from energy_trading.domain.models.ingestion import AdapterDiagnostic, DiagnosticSeverity, DLQRecord
from energy_trading.domain.models.observations import (
    ConsumptionRecord,
    GenerationAvailabilityRecord,
    GenerationStatus,
    HydroRecord,
    MarketPriceRecord,
    NewsEvent,
    NewsSeverity,
    WeatherRecord,
)
from energy_trading.domain.models.regulatory import RegulatoryConstraint
from energy_trading.domain.models.settlement import SettlementResult
from energy_trading.domain.models.trading import (
    BidSide,
    ClearingStatus,
    MarketBid,
    MarketClearingResult,
    RiskAssessment,
)

__all__ = [
    "AdapterDiagnostic",
    "BidSide",
    "ClearingStatus",
    "ConsumptionRecord",
    "DLQRecord",
    "DiagnosticSeverity",
    "GenerationAvailabilityRecord",
    "GenerationStatus",
    "HydroRecord",
    "LoadForecastPoint",
    "MarketBid",
    "MarketClearingResult",
    "MarketPriceRecord",
    "NewsEvent",
    "NewsSeverity",
    "PriceForecastPoint",
    "RegulatoryConstraint",
    "RiskAssessment",
    "SettlementResult",
    "WeatherRecord",
]
