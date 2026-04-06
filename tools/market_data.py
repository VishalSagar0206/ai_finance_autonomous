import yfinance as yf
from typing import Dict, Any, Optional
import logging
import pandas as pd

# Basic Logger Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketDataClient:
    """Wrapper for Yahoo Finance with Global (including Indian Market) support."""

    @staticmethod
    def _format_ticker(ticker: str) -> str:
        """Ensures Indian tickers have the correct suffix for Yahoo Finance."""
        ticker = ticker.upper().strip()
        # Common Indian tickers often sent without suffix
        indian_bluechips = {"RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "BAJFINANCE"}
        if ticker in indian_bluechips and not (ticker.endswith(".NS") or ticker.endswith(".BO")):
            logger.info(f"Auto-formatting Indian ticker: {ticker} -> {ticker}.NS")
            return f"{ticker}.NS"
        return ticker

    @staticmethod
    def get_ticker_info(ticker: str) -> Dict[str, Any]:
        """Fetch general info for a ticker, handling global symbols."""
        try:
            ticker = MarketDataClient._format_ticker(ticker)
            logger.info(f"Fetching info for {ticker}...")
            t = yf.Ticker(ticker)
            info = t.info
            
            # Edge Case: yfinance might return an empty dict for invalid tickers
            if not info or 'symbol' not in info:
                logger.warning(f"No info found for ticker {ticker}. Ticker may be invalid.")
                return {"error": f"Invalid ticker: {ticker}", "status": "failed"}

            return {
                "symbol": info.get("symbol"),
                "long_name": info.get("longName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("forwardPE"),
                "dividend_yield": info.get("dividendYield"),
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Error fetching info for {ticker}: {str(e)}")
            return {"error": str(e), "status": "error"}

    @staticmethod
    def get_historical_stats(ticker: str, period: str = "1mo") -> Dict[str, Any]:
        """Fetch historical price stats, handling global tickers."""
        try:
            ticker = MarketDataClient._format_ticker(ticker)
            logger.info(f"Fetching historical data for {ticker} (period: {period})...")
            t = yf.Ticker(ticker)
            df = t.history(period=period)

            # Edge Case: Check for empty dataframe
            if df.empty:
                logger.warning(f"No historical data for {ticker}.")
                return {"error": "No data found for period.", "status": "failed"}

            # Basic quantitative metrics
            volatility = df['Close'].pct_change().std()
            momentum = (df['Close'].iloc[-1] / df['Close'].iloc[0]) - 1
            avg_volume = df['Volume'].mean()

            return {
                "ticker": ticker,
                "volatility_std": float(volatility) if not pd.isna(volatility) else None,
                "momentum_pct": float(momentum),
                "avg_daily_volume": float(avg_volume),
                "last_price": float(df['Close'].iloc[-1]),
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Error calculating stats for {ticker}: {str(e)}")
            return {"error": str(e), "status": "error"}

    @staticmethod
    def get_sentiment_score(ticker: str) -> Dict[str, Any]:
        """Perform basic sentiment analysis on news headlines for global tickers."""
        try:
            ticker = MarketDataClient._format_ticker(ticker)
            logger.info(f"Fetching news sentiment for {ticker}...")
            t = yf.Ticker(ticker)
            news = t.news
            if not news:
                return {"score": 0, "label": "neutral", "status": "no_data"}
            
            positive_words = {"bullish", "buy", "growth", "profit", "beat", "upgrade", "success", "positive"}
            negative_words = {"bearish", "sell", "loss", "miss", "downgrade", "failure", "negative", "risk"}
            
            score = 0
            for item in news:
                headline = item.get("title", "").lower()
                for word in positive_words:
                    if word in headline: score += 1
                for word in negative_words:
                    if word in headline: score -= 1
            
            label = "bullish" if score > 0 else "bearish" if score < 0 else "neutral"
            return {"score": score, "label": label, "status": "success", "headline_count": len(news)}
        except Exception as e:
            logger.error(f"Error in sentiment analysis for {ticker}: {str(e)}")
            return {"error": str(e), "status": "error"}

# Singleton instance for the tool
market_data_client = MarketDataClient()
