import numpy as np
import pandas as pd
import yfinance as yf
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class RiskEngine:
    """
    Mathematical Risk Engine for VaR and Correlation analysis.
    Prevents 'hallucinated' risk assessments by providing empirical math to the Critic.
    """

    @staticmethod
    def calculate_portfolio_risk(tickers: List[str], weights: Dict[str, float]) -> Dict[str, Any]:
        """Calculates Value-at-Risk (VaR) and the Correlation Matrix."""
        try:
            if not tickers:
                return {"status": "error", "message": "No tickers for risk calc."}
            
            # 1. Fetch historical returns (90 days for risk)
            data = yf.download(tickers, period="90d")["Close"]
            returns = data.pct_change().dropna()
            
            # 2. Correlation Matrix
            corr_matrix = returns.corr().to_dict()
            
            # 3. Portfolio VaR (95% confidence)
            # Weighted returns
            w_list = [weights.get(t, 0) for t in tickers]
            port_returns = (returns * w_list).sum(axis=1)
            var_95 = np.percentile(port_returns, 5)
            
            # 4. Diversification Score (1 - avg correlation)
            avg_corr = returns.corr().values[np.triu_indices_from(returns.corr().values, k=1)].mean()
            
            return {
                "var_95": float(var_95),
                "avg_correlation": float(avg_corr),
                "correlation_matrix": corr_matrix,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"RiskEngine: Calculation failed. {str(e)}")
            return {"status": "error", "error": str(e)}

class SimilarityEngine:
    """
    Simulates a Siamese Network pattern by finding historical market analogs.
    Used by the Quantitative Analyst to identify the current market 'Regime'.
    """

    @staticmethod
    def find_historical_analogs(ticker: str) -> Dict[str, Any]:
        """
        In a real system, this would use Dynamic Time Warping (DTW) 
        to match current price charts with a 20-year database.
        """
        # Mocking regime identification
        regimes = ["Accumulation Phase (2016-style)", "Overextended Growth (2021-style)", "Defensive Pivot (2022-style)"]
        selected = regimes[hash(ticker) % len(regimes)]
        
        return {
            "matched_regime": selected,
            "confidence_score": 0.82,
            "historical_outcome": "Positive 6-month drift"
        }

risk_engine = RiskEngine()
similarity_engine = SimilarityEngine()
