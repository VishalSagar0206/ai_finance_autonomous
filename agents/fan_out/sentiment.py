from typing import Dict, Any
from adk_framework_v3.tools.market_data import market_data_client
from adk_framework_v3.core.state import ADKState
import logging

logger = logging.getLogger(__name__)

def sentiment_analyst_agent(state: ADKState) -> Dict[str, Any]:
    """
    Sentiment Analysis Agent using live news data.
    """
    tickers = state.request.tickers
    all_results = {}

    for ticker in tickers:
        formatted_ticker = market_data_client._format_ticker(ticker)
        sentiment = market_data_client.get_sentiment_score(formatted_ticker)
        
        if sentiment.get("status") != "success":
            all_results[formatted_ticker] = {"status": "failed", "insight": "No sentiment data available."}
            continue

        label = sentiment.get("label")
        score = sentiment.get("score", 0)
        
        insight = f"News sentiment for {formatted_ticker} is {label} (Score: {score})."
        if score >= 2:
            insight += " Strong positive news coverage identified."
        elif score <= -2:
            insight += " Significant negative news or risks identified."

        all_results[formatted_ticker] = {
            "score": score,
            "label": label,
            "insight": insight,
            "status": "completed"
        }

    return {
        "observations": {
            "sentiment": {
                "results": all_results,
                "status": "completed" if all_results else "no_data"
            }
        }
    }
