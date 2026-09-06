"""Application-owned agent identity and invocation boundary.

This module defines how future orchestration identifies and calls the
platform's canonical agents. Concrete agents, shared workflow snapshots,
retries, fallback, and graph runtimes are deferred.

Ownership:

* Application: owns ``AgentName`` and generic ``AgentPort[TRequest, TResult]``.
* Future concrete agents: satisfy the protocol structurally. There is no
  application base class and no registry.
* Future graph orchestration: invokes agents through this contract. The
  contract itself does not import or expose a graph runtime.

``TRequest`` and ``TResult`` stay agent-specific. This module does not
introduce a shared payload envelope or unconstrained mapping type.
"""

from enum import StrEnum
from typing import Protocol


class AgentName(StrEnum):
    """Canonical application agent identity.

    Values match ``AGENTS.md`` display names exactly. This is not a domain
    entity and is not a lookup registry.
    """

    REGULATORY_INTELLIGENCE = "Regulatory Intelligence Agent"
    PRICING_AND_SALES = "Pricing & Sales Agent"
    WEATHER_AND_RENEWABLE_FORECAST = "Weather & Renewable Forecast Agent"
    HYDRO_RESOURCES = "Hydro Resources Agent"
    GENERATION_AVAILABILITY = "Generation Availability Agent"
    NEWS_INTELLIGENCE = "News Intelligence Agent"
    MARKET_MONITORING = "Market Monitoring Agent"
    CONSUMER_LOAD_FORECAST = "Consumer Load Forecast Agent"
    DAM_PRICE_FORECAST = "DAM Price Forecast Agent"
    PORTFOLIO_AND_RISK = "Portfolio & Risk Agent"
    TRADING_STRATEGY = "Trading Strategy Agent"
    BILLING_AND_SETTLEMENT = "Billing & Settlement Agent"
    CHIEF_ORCHESTRATOR = "Chief Orchestrator Agent"


class AgentPort[TRequest, TResult](Protocol):
    """Framework-neutral agent invocation contract.

    Implementations satisfy this protocol structurally. The application
    depends on the protocol, never on a concrete agent class, graph runtime,
    LLM vendor, or ML library.

    ``name`` is canonical identity. ``run`` is the only shared invocation
    verb. Request and result types remain specific to each later agent.
    """

    @property
    def name(self) -> AgentName:
        """Return the canonical identity of this agent."""
        ...

    async def run(self, request: TRequest) -> TResult:
        """Execute the agent against a typed request and return a typed result."""
        ...
