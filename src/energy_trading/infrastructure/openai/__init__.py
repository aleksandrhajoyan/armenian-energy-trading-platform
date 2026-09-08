"""Async OpenAI client foundation.

This package exposes the lazy ``AsyncOpenAI`` factory. It does not create a
global client, connect on import, select a model, or wire ``create_app()``.
Future composition roots own client lifecycle (``close``) and wiring.
"""

from energy_trading.infrastructure.openai.client import create_openai_client

__all__ = ["create_openai_client"]
