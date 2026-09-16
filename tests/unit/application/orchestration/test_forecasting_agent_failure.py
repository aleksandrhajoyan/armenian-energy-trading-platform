"""Phase 3 executor preserves canonical failing-agent attribution."""

from __future__ import annotations

import inspect

import pytest

from energy_trading.application.agents import AgentName
from energy_trading.application.orchestration import ForecastingAgentFailure

_SENTINEL_TEXT = "sentinel-forecast-agent-failure-text-not-for-clients"
_PHASE3_AGENT_NAMES = (
    AgentName.CONSUMER_LOAD_FORECAST,
    AgentName.DAM_PRICE_FORECAST,
)


def test_forecasting_agent_failure_requires_canonical_agent_name() -> None:
    with pytest.raises(TypeError, match="agent_name must be an AgentName"):
        ForecastingAgentFailure("Consumer Load Forecast Agent")  # type: ignore[arg-type]


@pytest.mark.parametrize("agent_name", _PHASE3_AGENT_NAMES)
def test_forecasting_agent_failure_preserves_agent_and_sanitized_message(
    agent_name: AgentName,
) -> None:
    failure = ForecastingAgentFailure(agent_name)
    expected = f"Forecasting agent failed: {agent_name.value}."
    assert failure.agent_name is agent_name
    assert str(failure) == expected
    assert _SENTINEL_TEXT not in str(failure)
    assert "traceback" not in str(failure).lower()
    public_fields = {name for name in vars(failure) if not name.startswith("_")}
    assert public_fields == {"agent_name"}
    assert failure.__cause__ is None
    assert not hasattr(failure, "code")
    assert not hasattr(failure, "error_code")
    signature = inspect.signature(ForecastingAgentFailure.__init__)
    assert tuple(signature.parameters) == ("self", "agent_name")
