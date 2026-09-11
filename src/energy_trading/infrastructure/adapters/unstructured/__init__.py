"""Unstructured-source adapters. Concrete readers live beside this package."""

from energy_trading.infrastructure.adapters.unstructured.pdf_text_extraction import (
    PdfTextExtractionAdapter,
)

__all__ = ["PdfTextExtractionAdapter"]
