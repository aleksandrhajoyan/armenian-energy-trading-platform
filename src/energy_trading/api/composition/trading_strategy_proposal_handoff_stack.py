"""Outer Trading Strategy proposal handoff object composition.

This module wires a caller-supplied Trading Strategy bid port into the
already-published Trading Strategy execution composition and the
already-published Trading Strategy proposal handoff service. It does not
choose a bid proposal implementation, load configuration, or execute a
proposal.

Ownership:

* API composition root: owns ``build_trading_strategy_proposal_handoff_service``.
* Existing API composition: the published Chunk 206 Trading Strategy
  builder owns Trading Strategy agent and execution service construction.
* Injected: ``TradingStrategyBidPort``.
* Application: owns ``TradingStrategyProposalHandoffService`` and the bid
  port contract.
* Concrete bid proposal choice, bid MW and price calculation, risk
  assessment, eligibility and market rules, market submission, graph
  routing, and HTTP routes remain deferred.

The builder constructs objects only. It does not call application runtime
methods, and no Risk & Bid proposal handoff exists until a separate caller
executes the returned service.
"""

from energy_trading.api.composition.trading_strategy_stack import (
    build_trading_strategy_execution_service,
)
from energy_trading.application.orchestration.trading_strategy_proposal_handoff import (
    TradingStrategyProposalHandoffService,
)
from energy_trading.application.ports.trading_strategy_bid import TradingStrategyBidPort


def build_trading_strategy_proposal_handoff_service(
    *,
    bid_port: TradingStrategyBidPort,
) -> TradingStrategyProposalHandoffService:
    """Return a wired Trading Strategy proposal handoff service.

    The argument is an already-constructed application port implementation.
    This function does not discover, select, configure, or invoke it, and
    the caller keeps ownership of its lifetime.
    """

    trading_strategy_service = build_trading_strategy_execution_service(bid_port=bid_port)
    return TradingStrategyProposalHandoffService(
        trading_strategy_service=trading_strategy_service,
    )
