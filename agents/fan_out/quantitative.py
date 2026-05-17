from typing import Dict, Any
from tools.market_data import market_data_client, MarketDataClient
from core.state import ADKState
import logging

logger = logging.getLogger(__name__)

from tools.risk_engine import similarity_engine


def quantitative_analyst_agent(state: ADKState) -> Dict[str, Any]:
    """
    Node implementation for the Quantitative Analyst.
    Collects quantitative metrics and Regime Similarity (Siamese Network pattern).
    """
    tickers = state.request.tickers or ["AAPL"]
    all_results = {}

    for ticker in tickers:
        formatted_ticker = MarketDataClient._format_ticker(ticker)
        # 1. Fetch Quantitative Stats
        stats = market_data_client.get_historical_stats(formatted_ticker)

        # 2. Find Historical Analogs (Siamese pattern)
        regime = similarity_engine.find_historical_analogs(formatted_ticker)

        if stats.get("status") != "success":
            logger.warning(f"Quant Analyst: Data fetch failed for {formatted_ticker}.")
            all_results[formatted_ticker] = {
                "error": stats.get("error"),
                "status": "failed",
            }
            continue

        # 3. Simulated "Analysis" Logic
        momentum = stats.get("momentum_pct", 0)
        investor_type = state.request.investor_type

        insight = f"[{investor_type.value}] Regime Match: {regime['matched_regime']}. "
        
        if investor_type == "INTRADAY":
            volatility = stats.get("volatility_std", 0)
            if volatility and volatility > 0.02:
                insight += "High intraday volatility provides trading opportunities."
            else:
                insight += "Low volatility may limit intraday gains."
        else:
            if momentum > 0.05:
                insight += "Strong positive momentum."
            elif momentum < -0.05:
                insight += "Significant negative momentum."
            else:
                insight += "Neutral momentum."

        all_results[formatted_ticker] = {
            "metrics": stats,
            "regime": regime,
            "insight": insight,
            "status": "completed",
        }

    return {
        "observations": {
            "quantitative": {
                "results": all_results,
                "status": "completed" if all_results else "no_data",
            }
        }
    }
