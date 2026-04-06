from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class ComplianceEngine:
    """
    Institutional Compliance Guardrails (Pre-Check).
    Prevents analysis of restricted or high-regulatory-risk assets.
    """
    RESTRICTED_LIST = {"GME", "AMC"} # Example insider-trading or volatility blocks
    
    @staticmethod
    def check_ticker_compliance(tickers: List[str]) -> Dict[str, Any]:
        approved = []
        rejected = []
        for t in tickers:
            if t.upper() in ComplianceEngine.RESTRICTED_LIST:
                rejected.append(t)
                logger.warning(f"Compliance: REJECTED restricted ticker {t}.")
            else:
                approved.append(t)
        
        return {
            "approved_tickers": approved,
            "rejected_tickers": rejected,
            "status": "passed" if not rejected else "partial_block"
        }

class SmartOrderRouter:
    """
    Simulates Multi-Broker Smart Order Routing (SOR).
    Routes to Alpaca, IBKR, or Tradier based on 'best execution' logic.
    """
    
    @staticmethod
    def route_order(ticker: str, shares: int) -> Dict[str, Any]:
        # Industry Logic: Split order based on simulated liquidity
        # In real life, this would query IBKR and Alpaca spreads
        broker = "Alpaca Sandbox" if shares < 100 else "IBKR Paper TWS"
        
        print(f"   [SOR] Routing {shares} shares of {ticker} to {broker} for Best Execution.")
        
        return {
            "broker": broker,
            "shares": shares,
            "ticker": ticker,
            "status": "filled"
        }

compliance_engine = ComplianceEngine()
sor_router = SmartOrderRouter()
