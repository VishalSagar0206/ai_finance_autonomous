from __future__ import annotations

from typing import List, Dict, Any
import logging

import numpy as np

from tools.market_data import MarketDataClient

logger = logging.getLogger(__name__)


class RiskEngine:
    """Mathematical risk engine with deterministic offline market data."""

    @staticmethod
    def calculate_portfolio_risk(tickers: List[str], weights: Dict[str, float]) -> Dict[str, Any]:
        try:
            formatted = [MarketDataClient._format_ticker(t) for t in tickers if t != "CASH"]
            formatted = [t for t in formatted if not MarketDataClient._is_invalid(t)]
            if not formatted:
                return {"status": "error", "message": "No valid tickers for risk calc."}

            prices = MarketDataClient.synthetic_price_frame(formatted, periods=126)
            if prices.empty:
                return {"status": "error", "message": "No price history available."}

            returns = prices.pct_change().dropna()
            if returns.empty:
                return {"status": "error", "message": "No returns available."}

            corr = returns.corr()
            corr_matrix = corr.to_dict()
            w_list = [float(weights.get(t, weights.get(t.replace(".NS", ""), 0.0))) for t in returns.columns]
            weight_sum = sum(abs(w) for w in w_list)
            if weight_sum == 0:
                w_list = [1.0 / len(returns.columns)] * len(returns.columns)
            port_returns = (returns * w_list).sum(axis=1)
            var_95 = np.percentile(port_returns, 5)

            corr_vals = corr.values
            upper_tri = corr_vals[np.triu_indices_from(corr_vals, k=1)]
            if upper_tri.size == 0 or np.isnan(upper_tri).all():
                avg_corr = 0.0
            else:
                avg_corr = float(np.nanmean(upper_tri))

            return {
                "var_95": float(var_95),
                "avg_correlation": float(avg_corr),
                "correlation_matrix": corr_matrix,
                "status": "success",
            }
        except Exception as exc:
            logger.error("RiskEngine: Calculation failed. %s", exc)
            return {"status": "error", "error": str(exc)}


class SimilarityEngine:
    """Deterministic historical-regime lookup used by the Quant Analyst."""

    @staticmethod
    def find_historical_analogs(ticker: str) -> Dict[str, Any]:
        ticker = MarketDataClient._format_ticker(ticker)
        regimes = [
            "Accumulation Phase (2016-style)",
            "Overextended Growth (2021-style)",
            "Defensive Pivot (2022-style)",
        ]
        selected = regimes[MarketDataClient._seed_for(ticker) % len(regimes)]
        return {
            "matched_regime": selected,
            "confidence_score": 0.82,
            "historical_outcome": "Positive 6-month drift",
        }


risk_engine = RiskEngine()
similarity_engine = SimilarityEngine()
