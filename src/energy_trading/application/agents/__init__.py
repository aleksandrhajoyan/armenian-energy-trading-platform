"""Application agents.

Shared invocation contract plus concrete Weather, Hydro, and Generation
Availability agents.
"""

from energy_trading.application.agents.base import AgentName, AgentPort

__all__ = [
    "AgentName",
    "AgentPort",
]
