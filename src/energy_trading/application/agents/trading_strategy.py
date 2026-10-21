"""Trading Strategy Agent application boundary.

This module is the tenth concrete application agent. It consumes the
already-published ``TradingStrategyBidRequest``, calls the injected
application bid port once, and returns the exact canonical ``MarketBid``
proposal tuple. Bid MW, prices, sides, products, intervals, eligibility, and
risk-acceptance rules never enter here.

Ownership:

* Application: owns the concrete agent.
* Injected ``TradingStrategyBidPort``: supplies the already-canonical bid
  proposals for the published request.
* Future bid-generation implementation: structurally implements that port.
  No concrete implementation exists yet.
* Callers: obtain the risk assessment and forecasts and assemble the
  request. The agent does not read forecasts, run a risk assessment, inspect
  workflow state, or resolve a workflow plan.
* LangGraph, workflow context, persistence, market submission, retry,
  fallback, API composition, and Phase-4 routing remain deferred.

Proposal is not authorization, submission, clearing, or settlement. An
empty proposal tuple is returned unchanged and does not imply risk approval
or permission to trade.

The agent satisfies ``AgentPort`` structurally. It does not inherit a base
class and is not registered in a factory. It does not calculate bids.
"""

from energy_trading.application.agents.base import AgentName
from energy_trading.application.ports.trading_strategy_bid import (
    TradingStrategyBidPort,
    TradingStrategyBidRequest,
)
from energy_trading.domain.models.trading import MarketBid


class TradingStrategyAgent:
    """Thin application agent over the Trading Strategy bid port.

    ``run`` awaits ``TradingStrategyBidPort.propose_bids`` exactly once with
    the supplied request and returns that proposal tuple unchanged. It does
    not construct bids, default a proposal, translate errors, retry, submit,
    or call an LLM.
    """

    def __init__(self, *, bid_port: TradingStrategyBidPort) -> None:
        self._bid_port = bid_port

    @property
    def name(self) -> AgentName:
        return AgentName.TRADING_STRATEGY

    async def run(self, request: TradingStrategyBidRequest) -> tuple[MarketBid, ...]:
        return await self._bid_port.propose_bids(request=request)
