# ADK v4.0 Developer & Operator Guide

## 1. Adding a New Market
To add support for a new market (e.g., Crypto or Forex):
1.  Update `MarketDataClient._format_ticker` in `tools/market_data.py` to handle the specific symbol formats (e.g., `BTC-USD`).
2.  Ensure the `Quant Coder` prompt in `agents/coder.py` is updated to include market-specific libraries if `yfinance` is insufficient.

## 2. Extending the Ensemble Committee
To add a new specialized strategy agent:
1.  Add a new style to the `styles` list in `agents/ensemble.py`.
2.  Update `EnsembleCommittee.generate_style_strategy` to include persona-specific instructions (e.g., "You are an Arbitrage Specialist").

## 3. Human-in-the-Loop (HITL) Workflow
By default, ADK v4.0 will pause before placing orders.
- To approve: Click **"CONFIRM & EXECUTE ORDERS"** in the Dashboard.
- Under the hood: This triggers `adk_app.invoke(None, config=config)`, which resumes the graph from its last checkpoint.

## 4. Ticker Suffixing (Indian Market)
Common Indian stocks are auto-formatted.
- `RELIANCE` -> `RELIANCE.NS`
- `TCS` -> `TCS.NS`
To add more, update the `indian_bluechips` set in `tools/market_data.py`.
