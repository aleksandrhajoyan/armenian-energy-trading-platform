"""Async OpenAI client factory.

Construction does not issue an OpenAI request or readiness probe. A future
composition root owns the shared client lifecycle and must call
``await client.close()``. This factory does not close the client.
"""

from openai import AsyncOpenAI

from energy_trading.shared.config.openai import OpenAISettings


def create_openai_client(settings: OpenAISettings) -> AsyncOpenAI:
    """Return an official async OpenAI client without connecting.

    Credentials are passed as constructor keywords. SDK implicit retries are
    disabled so application orchestration retains retry ownership.
    """

    return AsyncOpenAI(
        api_key=settings.api_key.get_secret_value(),
        max_retries=0,
    )
