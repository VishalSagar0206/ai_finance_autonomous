from typing import Dict, Any
from tools.sec_edgar import sec_edgar_client
from core.state import ADKState
import logging

logger = logging.getLogger(__name__)

from tools.market_data import MarketDataClient


def fundamental_analyst_agent(state: ADKState) -> Dict[str, Any]:
    """
    Node implementation for the Fundamental Analyst.
    Collects fundamental metrics for all tickers in the request.
    """
    tickers = state.request.tickers or ["AAPL"]
    all_results = {}

    for ticker in tickers:
        formatted_ticker = MarketDataClient._format_ticker(ticker)
        # 1. Fetch Filings & Summary
        filings = sec_edgar_client.get_recent_filings(formatted_ticker)
        summary = sec_edgar_client.get_fundamental_summary(formatted_ticker)

        # 2. Logic to evaluate health
        pe_ratio = summary.get("trailing_pe")
        roe = summary.get("return_on_equity")

        investor_type = state.request.investor_type
        insight = f"[{investor_type.value}] Fundamental state is neutral."
        if roe and roe > 0.2:
            insight = f"[{investor_type.value}] Excellent profitability/ROE."

        if investor_type == "LONG_TERM":
            if pe_ratio and pe_ratio > 40:
                insight += " High P/E may be a concern for value-driven long-term hold."
            elif pe_ratio and pe_ratio < 15:
                insight += " Attractive P/E for long-term accumulation."
        elif investor_type == "INTRADAY":
            insight += " Fundamentals are secondary for intraday; focusing on news catalysts."
        else: # SHORT_TERM
            insight += " Monitoring for short-term earnings surprises."

        # Edge Case: Check if we actually got info/summary data
        is_invalid = summary.get("status") == "error" or (
            not summary.get("trailing_pe") and not summary.get("return_on_equity")
        )

        all_results[formatted_ticker] = {
            "filings_count": len(filings),
            "metrics": summary,
            "insight": insight if not is_invalid else "No fundamental data available.",
            "status": "failed" if is_invalid else "completed",
        }

    return {
        "observations": {
            "fundamental": {
                "results": all_results,
                "status": "completed" if all_results else "no_data",
            }
        }
    }
