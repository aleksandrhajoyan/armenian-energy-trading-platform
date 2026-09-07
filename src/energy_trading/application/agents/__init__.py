"""Application agents.

Shared invocation contract plus concrete Weather, Hydro, Generation
Availability, News Intelligence, and Market Monitoring agents.
"""

from energy_trading.application.agents.base import AgentName, AgentPort

__all__ = [
    "AgentName",
    "AgentPort",
]
