from typing import Dict, Any
from core.state import ADKState
import logging

logger = logging.getLogger(__name__)

from tools.alpha_memory import alpha_memory

from tools.ledger import trade_ledger
from tools.broker import sor_router


class ExecutionAgent:
    """
    Connects to multi-broker venues and persists results to SQL Ledger.
    """

    @staticmethod
    def execute_strategy(state: ADKState) -> Dict[str, Any]:
        """
        Sends the approved strategy to the SOR and logs to Ledger.
        """
        strategy = state.draft_strategy
        allocations = strategy.target_allocations

        print(
            f"-> Execution: Initiating Smart Order Routing for {len(allocations)} tickers."
        )

        filled_holdings = {}
        execution_records = []
        for ticker, weight in allocations.items():
            if ticker == "CASH":
                continue
            shares = int((100000 * weight) / 150)

            routing_result = sor_router.route_order(ticker, shares)

            filled_holdings[ticker] = shares
            execution_records.append(routing_result)

        # PERSIST TO SQL LEDGER
        trade_ledger.log_execution(strategy.strategy_id, execution_records)

        # PERSIST TO ALPHA MEMORY
        if state.backtest_results and state.backtest_results.get("status") == "success":
            alpha_memory.save_strategy(
                strategy_id=strategy.strategy_id,
                rationale=strategy.rationale,
                parameters=strategy.parameters,
                results=state.backtest_results,
            )

        return {
            "portfolio": {
                "holdings": filled_holdings,
                "buying_power": 12500.0,
                "last_execution_id": "ORD_ALP_9912",
            }
        }


def execution_agent(state: ADKState) -> Dict[str, Any]:
    """Node implementation for final trade execution."""
    return ExecutionAgent.execute_strategy(state)
