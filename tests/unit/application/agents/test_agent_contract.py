"""Application-owned agent identity and invocation contract."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from enum import StrEnum
from typing import get_args, get_origin

from energy_trading.application.agents import AgentName, AgentPort

CANONICAL_AGENT_NAMES: tuple[str, ...] = (
    "Regulatory Intelligence Agent",
    "Pricing & Sales Agent",
    "Weather & Renewable Forecast Agent",
    "Hydro Resources Agent",
    "Generation Availability Agent",
    "News Intelligence Agent",
    "Market Monitoring Agent",
    "Consumer Load Forecast Agent",
    "DAM Price Forecast Agent",
    "Portfolio & Risk Agent",
    "Trading Strategy Agent",
    "Billing & Settlement Agent",
    "Chief Orchestrator Agent",
)

CANONICAL_MEMBERS: tuple[tuple[str, str], ...] = (
    ("REGULATORY_INTELLIGENCE", "Regulatory Intelligence Agent"),
    ("PRICING_AND_SALES", "Pricing & Sales Agent"),
    ("WEATHER_AND_RENEWABLE_FORECAST", "Weather & Renewable Forecast Agent"),
    ("HYDRO_RESOURCES", "Hydro Resources Agent"),
    ("GENERATION_AVAILABILITY", "Generation Availability Agent"),
    ("NEWS_INTELLIGENCE", "News Intelligence Agent"),
    ("MARKET_MONITORING", "Market Monitoring Agent"),
    ("CONSUMER_LOAD_FORECAST", "Consumer Load Forecast Agent"),
    ("DAM_PRICE_FORECAST", "DAM Price Forecast Agent"),
    ("PORTFOLIO_AND_RISK", "Portfolio & Risk Agent"),
    ("TRADING_STRATEGY", "Trading Strategy Agent"),
    ("BILLING_AND_SETTLEMENT", "Billing & Settlement Agent"),
    ("CHIEF_ORCHESTRATOR", "Chief Orchestrator Agent"),
)


@dataclass(frozen=True, slots=True)
class _ProbeRequest:
    """Test-only typed request. Not a production agent payload."""

    value: str


@dataclass(frozen=True, slots=True)
class _ProbeResult:
    """Test-only typed result. Not a production agent envelope."""

    value: str


class _StructuralAgentFake:
    """Test-only fake that structurally satisfies ``AgentPort``.

    Not a production agent. Does not inherit a production base class.
    """

    def __init__(self, name: AgentName) -> None:
        self._name = name
        self.received: _ProbeRequest | None = None

    @property
    def name(self) -> AgentName:
        return self._name

    async def run(self, request: _ProbeRequest) -> _ProbeResult:
        self.received = request
        return _ProbeResult(value=request.value)


def _as_agent_port(agent: _StructuralAgentFake) -> AgentPort[_ProbeRequest, _ProbeResult]:
    """Application-shaped call site: the port type is the only accepted argument."""

    return agent


def test_agent_name_is_strenum() -> None:
    assert issubclass(AgentName, StrEnum)
    assert issubclass(AgentName, str)


def test_agent_name_has_exactly_thirteen_canonical_members() -> None:
    assert len(AgentName) == 13
    assert len(AgentName.__members__) == 13
    assert tuple(member.name for member in AgentName) == tuple(
        identifier for identifier, _ in CANONICAL_MEMBERS
    )
    assert tuple(member.value for member in AgentName) == CANONICAL_AGENT_NAMES


def test_agent_name_values_are_unique_and_unaliased() -> None:
    values = [member.value for member in AgentName]
    assert len(values) == len(set(values))
    assert set(AgentName.__members__) == {identifier for identifier, _ in CANONICAL_MEMBERS}
    for identifier, display_name in CANONICAL_MEMBERS:
        assert AgentName[identifier].value == display_name
        assert AgentName(display_name) is AgentName[identifier]


def test_agent_name_preserves_canonical_spelling() -> None:
    assert AgentName.PRICING_AND_SALES.value == "Pricing & Sales Agent"
    assert AgentName.WEATHER_AND_RENEWABLE_FORECAST.value == ("Weather & Renewable Forecast Agent")
    assert AgentName.DAM_PRICE_FORECAST.value == "DAM Price Forecast Agent"
    assert AgentName.PORTFOLIO_AND_RISK.value == "Portfolio & Risk Agent"
    assert "&" in AgentName.PRICING_AND_SALES.value


def test_agent_port_is_generic_protocol() -> None:
    origin = get_origin(AgentPort[_ProbeRequest, _ProbeResult])
    assert origin is AgentPort
    args = get_args(AgentPort[_ProbeRequest, _ProbeResult])
    assert args == (_ProbeRequest, _ProbeResult)


def test_agent_port_exposes_only_name_and_run() -> None:
    assert isinstance(AgentPort.name, property)
    run_parameters = inspect.signature(AgentPort.run).parameters
    assert tuple(run_parameters) == ("self", "request")
    assert inspect.iscoroutinefunction(AgentPort.run)
    defined = {
        name
        for name, value in vars(AgentPort).items()
        if not name.startswith("_") and (inspect.isfunction(value) or isinstance(value, property))
    }
    assert defined == {"name", "run"}


def test_structural_fake_does_not_inherit_production_base() -> None:
    assert AgentPort not in _StructuralAgentFake.__mro__
    assert not any(
        base.__name__ in {"AgentPort", "Protocol"} for base in _StructuralAgentFake.__bases__
    )


async def test_structural_fake_satisfies_agent_port() -> None:
    fake = _StructuralAgentFake(AgentName.MARKET_MONITORING)
    port = _as_agent_port(fake)
    assert port.name is AgentName.MARKET_MONITORING
    result = await port.run(_ProbeRequest(value="typed-request"))
    assert result == _ProbeResult(value="typed-request")
    assert fake.received == _ProbeRequest(value="typed-request")
