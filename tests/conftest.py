"""Shared test fixtures. Isolate cached settings from a developer's local .env."""

from collections.abc import Iterator

import pytest

from energy_trading.shared.config.settings import clear_settings_cache


@pytest.fixture(autouse=True)
def reset_settings_cache() -> Iterator[None]:
    """Ensure settings cache does not leak across tests."""

    clear_settings_cache()
    yield
    clear_settings_cache()
