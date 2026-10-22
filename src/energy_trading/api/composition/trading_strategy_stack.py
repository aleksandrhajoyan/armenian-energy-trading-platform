"""Outer Trading Strategy execution object composition.

This module wires a caller-supplied Trading Strategy bid port into the
already-published Trading Strategy agent and bid proposal execution service.
It does not choose a bid proposal implementation, load configuration, or
execute a proposal.

Ownership:

* API composition root: owns ``build_trading_strategy_execution_service``.
* Injected: ``TradingStrategyBidPort``.
* Application: owns ``TradingStrategyAgent``,
  ``TradingStrategyExecutionService``, and the bid port contract.
* Concrete bid proposal choice, bid MW and price calculation, eligibility
  and market rules, market submission, graph routing, and HTTP routes remain
  deferred.

The builder constructs objects only. It does not call application runtime
methods.
"""

from energy_trading.application.agents.trading_strategy import TradingStrategyAgent
from energy_trading.application.orchestration.trading_strategy_execution import (
    TradingStrategyExecutionService,
)
from energy_trading.application.ports.trading_strategy_bid import TradingStrategyBidPort


def build_trading_strategy_execution_service(
    *,
    bid_port: TradingStrategyBidPort,
) -> TradingStrategyExecutionService:
    """Return a wired Trading Strategy execution service.

    The argument is an already-constructed application port implementation.
    This function does not discover, select, configure, or invoke it, and
    the caller keeps ownership of its lifetime.
    """

    bid_agent = TradingStrategyAgent(bid_port=bid_port)
    return TradingStrategyExecutionService(bid_agent=bid_agent)
