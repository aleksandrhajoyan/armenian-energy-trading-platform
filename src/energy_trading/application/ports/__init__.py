"""Application ports. Implementations are injected from outer layers."""

from energy_trading.application.ports.cache import CachePort
from energy_trading.application.ports.consumer_load_forecast_model import (
    ConsumerLoadForecastModelPort,
    ConsumerLoadForecastModelRequest,
)
from energy_trading.application.ports.consumption_repository import ConsumptionRepositoryPort
from energy_trading.application.ports.dam_price_forecast_model import (
    DAMPriceForecastModelPort,
    DAMPriceForecastModelRequest,
)
from energy_trading.application.ports.dlq import DeadLetterQueuePort
from energy_trading.application.ports.document_embedding import (
    DocumentChunkEmbedding,
    DocumentEmbeddingPort,
)
from energy_trading.application.ports.document_extraction import (
    DocumentExtractionPort,
    DocumentExtractionResult,
    ExtractedDocumentChunk,
)
from energy_trading.application.ports.document_query_embedding import (
    DocumentQueryEmbedding,
    DocumentQueryEmbeddingPort,
)
from energy_trading.application.ports.document_vector_index import (
    DocumentVectorIndexEntry,
    DocumentVectorIndexPort,
)
from energy_trading.application.ports.document_vector_search import (
    DocumentVectorSearchPort,
    DocumentVectorSearchQuery,
)
from energy_trading.application.ports.generation_availability_records import (
    GenerationAvailabilityRecordSourcePort,
)
from energy_trading.application.ports.hydro_records import HydroRecordSourcePort
from energy_trading.application.ports.market_price_records import MarketPriceRecordSourcePort
from energy_trading.application.ports.news_events import NewsEventSourcePort
from energy_trading.application.ports.regulatory_constraint_inference import (
    RegulatoryConstraintInferencePort,
)
from energy_trading.application.ports.structured_ingestion import (
    StructuredIngestionPort,
    StructuredIngestionResult,
)
from energy_trading.application.ports.weather_records import WeatherRecordSourcePort

__all__ = [
    "CachePort",
    "ConsumerLoadForecastModelPort",
    "ConsumerLoadForecastModelRequest",
    "ConsumptionRepositoryPort",
    "DAMPriceForecastModelPort",
    "DAMPriceForecastModelRequest",
    "DeadLetterQueuePort",
    "DocumentChunkEmbedding",
    "DocumentEmbeddingPort",
    "DocumentExtractionPort",
    "DocumentExtractionResult",
    "DocumentQueryEmbedding",
    "DocumentQueryEmbeddingPort",
    "DocumentVectorIndexEntry",
    "DocumentVectorIndexPort",
    "DocumentVectorSearchPort",
    "DocumentVectorSearchQuery",
    "ExtractedDocumentChunk",
    "GenerationAvailabilityRecordSourcePort",
    "HydroRecordSourcePort",
    "MarketPriceRecordSourcePort",
    "NewsEventSourcePort",
    "RegulatoryConstraintInferencePort",
    "StructuredIngestionPort",
    "StructuredIngestionResult",
    "WeatherRecordSourcePort",
]
