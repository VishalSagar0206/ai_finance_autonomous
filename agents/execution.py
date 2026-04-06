from typing import Dict, Any
from adk_framework_v3.core.state import ADKState
import logging

logger = logging.getLogger(__name__)

from adk_framework_v3.tools.alpha_memory import alpha_memory

class ExecutionAgent:
    """
    Connects to live/paper brokers and persists success to Alpha Memory.
    """

    @staticmethod
    def execute_strategy(state: ADKState) -> Dict[str, Any]:
        """
        Sends the approved strategy to the brokerage. 
        """
        strategy = state.draft_strategy
        allocations = strategy.target_allocations
        
        print(f"-> Execution: Routing orders for {len(allocations)} tickers to Alpaca Sandbox.")
        
        # Simulated Order Routing Logic
        filled_holdings = {}
        for ticker, weight in allocations.items():
            if ticker == "CASH": continue
            shares = int((100000 * weight) / 150) 
            filled_holdings[ticker] = shares
            print(f"   [Execution] Executed BUY: {shares} shares of {ticker}.")

        # PERSIST TO ALPHA MEMORY
        if state.backtest_results and state.backtest_results.get("status") == "success":
            alpha_memory.save_strategy(
                strategy_id=strategy.strategy_id,
                rationale=strategy.rationale,
                parameters=strategy.parameters,
                results=state.backtest_results
            )

        return {
            "portfolio": {
                "holdings": filled_holdings,
                "buying_power": 12500.0,
                "last_execution_id": "ORD_ALP_9912"
            }
        }

def execution_agent(state: ADKState) -> Dict[str, Any]:
    """Node implementation for final trade execution."""
    return ExecutionAgent.execute_strategy(state)
