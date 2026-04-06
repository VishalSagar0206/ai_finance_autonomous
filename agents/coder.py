import json
import os
from typing import Dict, Any
from adk_framework_v3.core.state import ADKState
import logging

logger = logging.getLogger(__name__)

class QuantCoder:
    """
    LLM-powered Agent to generate Python backtest code.
    Generates a script ('backtest.py') for execution in a sandbox.
    """

    @staticmethod
    def generate_backtest_code(state: ADKState) -> str:
        """Dynamically builds a pandas-based backtest script from the approved strategy."""
        strategy = state.draft_strategy
        tickers = list(strategy.target_allocations.keys())
        allocations = strategy.target_allocations
        
        # Template for a robust backtest script
        code_template = f"""
import yfinance as yf
import pandas as pd
import numpy as np

def run_backtest():
    tickers = {tickers}
    weights = {allocations}
    
    # 1. Fetch historical data (1 year for backtest)
    data = yf.download(tickers, period="1y")["Close"]
    
    # 2. Calculate daily returns
    returns = data.pct_change().dropna()
    
    # 3. Calculate portfolio returns
    # Weighted returns for each asset
    weighted_returns = (returns * pd.Series(weights)).sum(axis=1)
    
    # 4. Extract Key Metrics
    total_return = (1 + weighted_returns).prod() - 1
    annualized_volatility = weighted_returns.std() * np.sqrt(252)
    sharpe_ratio = (weighted_returns.mean() * 252) / annualized_volatility if annualized_volatility > 0 else 0
    
    # Drawdown calculation
    cum_returns = (1 + weighted_returns).cumprod()
    rolling_max = cum_returns.cummax()
    drawdowns = (cum_returns - rolling_max) / rolling_max
    max_drawdown = drawdowns.min()

    # Results dictionary for the Coder to parse
    results = {{
        "total_return": float(total_return),
        "annualized_volatility": float(annualized_volatility),
        "sharpe_ratio": float(sharpe_ratio),
        "max_drawdown": float(max_drawdown),
        "status": "success"
    }}
    print(f"BACKTEST_RESULTS:{{json.dumps(results)}}")

if __name__ == "__main__":
    run_backtest()
"""
        return code_template

from pydantic import BaseModel, Field
from typing import Dict, Any, List
from adk_framework_v3.core.llm_provider import llm_provider
import os

class CoderOutput(BaseModel):
    """Schema for the Coder's output, including the generated script."""
    python_code: str = Field(description="Complete, runnable Python script for backtesting.")
    required_libraries: List[str] = Field(description="List of pip libraries needed.")

from adk_framework_v3.tools.code_executor import code_executor

def coder_agent(state: ADKState) -> Dict[str, Any]:
    """Node implementation: Generates, EXECUTES, and SELF-CORRECTS backtest code using Gemini."""
    print(f"-> Quant Coder [Attempt {state.backtest_attempts}]: Orchestrating backtest.")
    
    if not state.draft_strategy:
        return {"backtest_results": {"status": "error", "message": "No strategy available."}}

    # 1. Fallback for Mock
    if not os.environ.get("GOOGLE_API_KEY"):
        logger.warning("Coder: No API Key. Using template fallback.")
        code = QuantCoder.generate_backtest_code(state)
        results = code_executor.execute_python_code(code)
        return {"backtest_results": results, "backtest_attempts": state.backtest_attempts + 1}

    # 2. Real Gemini Code Generation with Deep Learning focus
    prompt = (
        "Generate a professional Python backtest script using Deep Learning. "
        "Use yfinance for data. Implement a simple LSTM or Transformer-based feature "
        "to predict returns. Use PyTorch or Scikit-Learn. "
        "Calculate Sharpe Ratio and Max Drawdown. Output JSON with 'BACKTEST_RESULTS:' prefix. "
        "IMPORTANT: Use modern pandas offsets (e.g., use 'BQE' or 'ME')."
    )
    
    if state.execution_logs:
        prompt += f"\n\nCRITICAL: Previous execution failed. Fix the following error:\n{state.execution_logs[-1]}"

    try:
        llm_out = llm_provider.run_structured_chain(
            prompt_text=prompt,
            input_data=state.draft_strategy.model_dump(),
            output_schema=CoderOutput
        )
        
        # 3. Execution
        print(f"   [Coder] Executing generated code...")
        results = code_executor.execute_python_code(llm_out.python_code)
        
        if results.get("status") == "error":
            print(f"   [Coder] Execution FAILED. Logging error for correction.")
            return {
                "execution_logs": [results.get("error")],
                "backtest_attempts": state.backtest_attempts + 1,
                "backtest_results": results
            }

        print(f"   [Coder] Execution SUCCESSFUL. Sharpe: {results.get('sharpe_ratio')}")
        return {
            "backtest_results": results,
            "backtest_attempts": state.backtest_attempts + 1,
            "execution_logs": ["SUCCESS"]
        }
    except Exception as e:
        logger.error(f"Coder: Gemini code generation failed. Error: {str(e)}")
        return {"backtest_results": {"status": "error", "error": str(e)}, "backtest_attempts": state.backtest_attempts + 1}
