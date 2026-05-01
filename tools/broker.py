import os
import logging
from typing import Dict, Any
from alpaca_trade_api.rest import REST
import uuid

logger = logging.getLogger(__name__)

class AlpacaSORRouter:
    """
    Smart Order Router (SOR) integrating with Alpaca Markets.
    Handles real execution, order types, and time-in-force (TIF) logic.
    """
    def __init__(self):
        self.api_key = os.environ.get("ALPACA_API_KEY", "MOCK_KEY")
        self.secret_key = os.environ.get("ALPACA_SECRET_KEY", "MOCK_SECRET")
        self.base_url = os.environ.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
        
        # Initialize only if real keys are provided to avoid crashing on import
        if self.api_key != "MOCK_KEY":
            self.api = REST(self.api_key, self.secret_key, self.base_url, api_version='v2')
        else:
            self.api = None

    def route_order(self, ticker: str, shares: float, side: str = "buy", order_type: str = "market") -> Dict[str, Any]:
        """
        Routes an order to Alpaca via REST API.
        """
        logger.info(f"SOR: Routing {side.upper()} order for {shares} shares of {ticker}...")
        
        if not self.api:
            logger.warning("Alpaca keys missing. Running SOR in MOCK execution mode.")
            return {
                "order_id": f"MOCK-ALP-{str(uuid.uuid4())[:8]}",
                "ticker": ticker,
                "shares": shares,
                "execution_price": "Market", 
                "venue": "Alpaca-Paper-Mock",
                "status": "filled_mock",
                "timestamp": "2026-05-01T10:00:00Z"
            }

        try:
            # Submit real institutional order (Paper Trading)
            order = self.api.submit_order(
                symbol=ticker,
                qty=shares,
                side=side,
                type=order_type,
                time_in_force='gtc' # Good Till Cancelled
            )
            
            return {
                "order_id": order.id,
                "ticker": order.symbol,
                "shares": float(order.qty),
                "execution_price": order.filled_avg_price if order.filled_avg_price else "Pending",
                "venue": "Alpaca-Paper",
                "status": order.status,
                "timestamp": str(order.submitted_at)
            }
            
        except Exception as e:
            logger.error(f"Alpaca Order Failed: {str(e)}")
            return {"status": "error", "error": str(e), "ticker": ticker}

sor_router = AlpacaSORRouter()
