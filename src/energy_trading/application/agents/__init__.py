"""Application agents.

Shared invocation contract plus concrete Weather, Hydro, Generation
Availability, News Intelligence, Market Monitoring, Regulatory
Intelligence, Consumer Load Forecast, and DAM Price Forecast agents.
"""

from energy_trading.application.agents.base import AgentName, AgentPort

__all__ = [
    "AgentName",
    "AgentPort",
]
