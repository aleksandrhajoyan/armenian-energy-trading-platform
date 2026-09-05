"""Application ports. Implementations are injected from outer layers."""

from energy_trading.application.ports.cache import CachePort
from energy_trading.application.ports.consumption_repository import ConsumptionRepositoryPort
from energy_trading.application.ports.dlq import DeadLetterQueuePort
from energy_trading.application.ports.document_extraction import (
    DocumentExtractionPort,
    DocumentExtractionResult,
    ExtractedDocumentChunk,
)
from energy_trading.application.ports.structured_ingestion import (
    StructuredIngestionPort,
    StructuredIngestionResult,
)

__all__ = [
    "CachePort",
    "ConsumptionRepositoryPort",
    "DeadLetterQueuePort",
    "DocumentExtractionPort",
    "DocumentExtractionResult",
    "ExtractedDocumentChunk",
    "StructuredIngestionPort",
    "StructuredIngestionResult",
]
