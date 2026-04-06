from typing import Dict, Any, List
import yfinance as yf
import logging

logger = logging.getLogger(__name__)

from adk_framework_v3.tools.market_data import market_data_client

class SEC_EDGARClient:
    """Mock/Wrapper for SEC filings and Global Fundamental access via yfinance."""

    @staticmethod
    def get_recent_filings(ticker: str) -> List[Dict[str, Any]]:
        """Fetch basic info on recent filings, handling global tickers."""
        try:
            from adk_framework_v3.tools.market_data import MarketDataClient
            ticker = MarketDataClient._format_ticker(ticker)
            logger.info(f"Fetching filings metadata for {ticker}...")
            t = yf.Ticker(ticker)
            # yfinance provides some fundamental actions/news which can proxy for filings in a mock
            # In a real implementation, we would use sec-api or direct RSS feeds
            news = t.news
            if not news:
                logger.warning(f"No recent news/filings found for {ticker}.")
                return []
            
            # Simple metadata extraction
            return [
                {"title": item.get("title"), "publisher": item.get("publisher"), "link": item.get("link")}
                for item in news[:5]
            ]
        except Exception as e:
            logger.error(f"Error fetching filings for {ticker}: {str(e)}")
            return []

    @staticmethod
    def get_fundamental_summary(ticker: str) -> Dict[str, Any]:
        """Fetch fundamental summary metrics (P/E, Debt/Equity, etc.) with null safety."""
        try:
            t = yf.Ticker(ticker)
            info = t.info
            
            if not info or 'symbol' not in info:
                return {"status": "failed", "error": "No info found"}

            # Edge Case: Extract only what is necessary and provide safe defaults
            return {
                "trailing_pe": info.get("trailingPE"),
                "debt_to_equity": info.get("debtToEquity"),
                "return_on_equity": info.get("returnOnEquity"),
                "gross_margins": info.get("grossMargins"),
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Error summarizing fundamentals for {ticker}: {str(e)}")
            return {"error": str(e), "status": "error"}

sec_edgar_client = SEC_EDGARClient()
