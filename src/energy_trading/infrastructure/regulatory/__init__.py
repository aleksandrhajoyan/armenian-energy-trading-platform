"""Regulatory Intelligence infrastructure adapters.

This package exposes the OpenAI regulatory-constraint inference adapter. It
does not construct ``AsyncOpenAI``, load credentials, or wire ``create_app()``.
"""

from energy_trading.infrastructure.regulatory.openai_constraint_inference import (
    OpenAIRegulatoryConstraintInferenceAdapter,
)

__all__ = ["OpenAIRegulatoryConstraintInferenceAdapter"]
