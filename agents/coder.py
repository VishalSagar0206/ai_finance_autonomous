import json
import os
from typing import Dict, Any
from core.state import ADKState
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
        # Remove 'CASH' from yfinance download if present
        yf_tickers = [t for t in tickers if t != 'CASH']
        allocations = strategy.target_allocations

        # Template for a PyTorch Neural Network backtest script
        code_template = f"""
import yfinance as yf
import pandas as pd
import numpy as np
import json
import torch
import torch.nn as nn

class AlphaNet(nn.Module):
    def __init__(self, input_size):
        super(AlphaNet, self).__init__()
        self.fc1 = nn.Linear(input_size, 64)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, 1)
        
    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        return self.fc3(x)

def run_neural_backtest():
    tickers = {yf_tickers}
    base_weights = {allocations}
    
    if not tickers:
        results = {{"total_return": 0.0, "annualized_volatility": 0.0, "sharpe_ratio": 0.0, "max_drawdown": 0.0, "status": "success"}}
        print(f"BACKTEST_RESULTS:{{json.dumps(results)}}")
        return

    # 1. Fetch historical data (2 years for training/testing)
    data = yf.download(tickers, period="2y")
    if "Close" in data:
        data = data["Close"]
    
    if isinstance(data, pd.Series):
        data = data.to_frame(name=tickers[0])
        
    returns = data.pct_change().dropna()
    dates = returns.index
    
    # 2. Neural Network Feature Engineering (Lookback window)
    X_data = []
    y_data = []
    valid_dates = []
    
    lookback = 5
    for i in range(lookback, len(returns) - 1):
        X_data.append(returns.iloc[i-lookback:i].values.flatten())
        y_data.append(returns.iloc[i].values) # Next day returns
        valid_dates.append(dates[i+1])
        
    X_tensor = torch.tensor(np.array(X_data), dtype=torch.float32)
    y_tensor = torch.tensor(np.array(y_data), dtype=torch.float32)
    
    # Train/Test Split (80/20)
    split = int(len(X_tensor) * 0.8)
    X_train, X_test = X_tensor[:split], X_tensor[split:]
    y_train, y_test = y_tensor[:split], y_tensor[split:]
    test_dates = valid_dates[split:]
    
    # 3. Train the Model
    input_size = X_train.shape[1]
    model = AlphaNet(input_size)
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    
    epochs = 50
    for epoch in range(epochs):
        optimizer.zero_grad()
        outputs = model(X_train)
        loss = criterion(outputs, y_train)
        loss.backward()
        optimizer.step()
        
    # XAI: Extract Feature Importance (Mean absolute weights of first layer)
    with torch.no_grad():
        importance = model.fc1.weight.abs().mean(dim=0).numpy()
    
    # Map importance to readable feature names
    feature_names = []
    for i in range(lookback, 0, -1):
        for t in tickers:
            feature_names.append(f"{{t}} (t-{{i}})")
            
    # Top 5 most important features
    top_indices = importance.argsort()[-5:][::-1]
    feat_importance_dict = {{feature_names[idx]: float(importance[idx]) for idx in top_indices}}
        
    # 4. Predict & Simulate Portfolio
    model.eval()
    with torch.no_grad():
        predictions = model(X_test).numpy()
    
    weighted_returns = []
    benchmark_returns = []
    actual_test_returns = y_test.numpy()
    
    for i in range(len(predictions)):
        pred_signal = predictions[i]
        step_returns = 0
        bench_step = 0
        
        for j, t in enumerate(tickers):
            base_w = base_weights.get(t, 0.0)
            signal_multiplier = 1.0 + (pred_signal[j] if len(pred_signal) > j else 0)
            step_returns += actual_test_returns[i][j] * base_w * max(0, signal_multiplier)
            bench_step += actual_test_returns[i][j] * (1.0 / len(tickers)) # Equal weight benchmark
            
        weighted_returns.append(step_returns)
        benchmark_returns.append(bench_step)
        
    weighted_returns = pd.Series(weighted_returns)
    benchmark_returns = pd.Series(benchmark_returns)
    
    # 5. Extract Key Metrics
    total_return = (1 + weighted_returns).prod() - 1
    annualized_volatility = weighted_returns.std() * np.sqrt(252)
    sharpe_ratio = (weighted_returns.mean() * 252) / annualized_volatility if annualized_volatility > 0 else 0
    
    cum_returns = (1 + weighted_returns).cumprod()
    bench_cum = (1 + benchmark_returns).cumprod()
    
    rolling_max = cum_returns.cummax()
    drawdowns = (cum_returns - rolling_max) / rolling_max
    max_drawdown = drawdowns.min() if not pd.isna(drawdowns.min()) else 0.0

    # Build Equity Curve Data
    equity_curve = []
    for d, strat, bench in zip(test_dates, cum_returns, bench_cum):
        equity_curve.append({{"date": d.strftime("%Y-%m-%d"), "strategy": float(strat), "benchmark": float(bench)}})

    results = {{
        "total_return": float(total_return),
        "annualized_volatility": float(annualized_volatility),
        "sharpe_ratio": float(sharpe_ratio),
        "max_drawdown": float(max_drawdown),
        "status": "success",
        "nn_loss": float(loss.item()),
        "equity_curve": equity_curve,
        "feature_importance": feat_importance_dict
    }}
    print(f"BACKTEST_RESULTS:{{json.dumps(results)}}")

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings('ignore')
    run_neural_backtest()
"""
        return code_template


from pydantic import BaseModel, Field
from typing import Dict, Any, List
from core.llm_provider import llm_provider
import os


class CoderOutput(BaseModel):
    """Schema for the Coder's output, including the generated script."""

    python_code: str = Field(
        description="Complete, runnable Python script for backtesting."
    )
    required_libraries: List[str] = Field(description="List of pip libraries needed.")


from tools.code_executor import code_executor


def coder_agent(state: ADKState) -> Dict[str, Any]:
    """Node implementation: Generates, EXECUTES, and SELF-CORRECTS backtest code using Gemini."""
    print(
        f"-> Quant Coder [Attempt {state.backtest_attempts}]: Orchestrating backtest."
    )

    if not state.draft_strategy:
        return {
            "backtest_results": {"status": "error", "message": "No strategy available."}
        }

    # 1. Fallback for Mock
    if not os.environ.get("GOOGLE_API_KEY"):
        logger.warning("Coder: No API Key. Using template fallback.")
        code = QuantCoder.generate_backtest_code(state)
        results = code_executor.execute_python_code(code)
        return {
            "backtest_results": results,
            "backtest_attempts": state.backtest_attempts + 1,
        }

    # 2. Real Gemini Code Generation
    template = QuantCoder.generate_backtest_code(state)
    prompt = (
        "You are an expert Python Quantitative Developer. "
        "I need a backtest script. To ensure stability in our automated pipeline, "
        "you MUST output the Python code exactly following the structure of this template, "
        "only adjusting the variables if absolutely necessary to match the requested strategy.\n\n"
        f"TEMPLATE:\n```python\n{template}\n```\n\n"
        "Output ONLY the Python code. Ensure it prints the final JSON with 'BACKTEST_RESULTS:' prefix."
    )

    if state.execution_logs:
        prompt += f"\n\nCRITICAL: Previous execution failed. Fix the following error:\n{state.execution_logs[-1]}"

    try:
        llm_out = llm_provider.run_structured_chain(
            prompt_text=prompt,
            input_data=state.draft_strategy.model_dump(),
            output_schema=CoderOutput,
        )

        # 3. Execution
        print(f"   [Coder] Executing generated code...")
        results = code_executor.execute_python_code(llm_out.python_code)

        if results.get("status") == "error":
            print(f"   [Coder] Execution FAILED. Logging error for correction.")
            return {
                "execution_logs": [results.get("error")],
                "backtest_attempts": state.backtest_attempts + 1,
                "backtest_results": results,
            }

        print(f"   [Coder] Execution SUCCESSFUL. Sharpe: {results.get('sharpe_ratio')}")
        return {
            "backtest_results": results,
            "backtest_attempts": state.backtest_attempts + 1,
            "execution_logs": ["SUCCESS"],
        }
    except Exception as e:
        logger.error(f"Coder: Gemini code generation failed. Error: {str(e)}")
        return {
            "backtest_results": {"status": "error", "error": str(e)},
            "backtest_attempts": state.backtest_attempts + 1,
        }
