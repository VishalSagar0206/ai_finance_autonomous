from __future__ import annotations

from typing import Dict, Any
import logging
import uuid

from core.config import config

try:
    from alpaca_trade_api.rest import REST
except Exception:  # pragma: no cover - optional dependency
    REST = None

logger = logging.getLogger(__name__)


class AlpacaSORRouter:
    """Smart Order Router with safe mock execution fallback."""

    def __init__(self):
        self.api = None
        if config.has_live_broker() and REST is not None:
            try:
                self.api = REST(
                    config.ALPACA_API_KEY,
                    config.ALPACA_SECRET_KEY,
                    config.ALPACA_BASE_URL,
                    api_version="v2",
                )
            except Exception as exc:
                logger.warning("Alpaca initialization failed; using mock execution. Error: %s", exc)

    def route_order(self, ticker: str, shares: float, side: str = "buy", order_type: str = "market") -> Dict[str, Any]:
        logger.info("SOR: routing %s order for %s shares of %s", side.upper(), shares, ticker)
        if not self.api:
            return {
                "order_id": f"MOCK-ALP-{str(uuid.uuid4())[:8]}",
                "ticker": ticker,
                "shares": shares,
                "broker": "Alpaca-Paper-Mock",
                "execution_price": "Market",
                "venue": "Alpaca-Paper-Mock",
                "status": "filled_mock",
                "timestamp": "2026-06-10T10:00:00Z",
            }

        try:
            order = self.api.submit_order(
                symbol=ticker,
                qty=shares,
                side=side,
                type=order_type,
                time_in_force="gtc",
            )
            return {
                "order_id": order.id,
                "ticker": order.symbol,
                "shares": float(order.qty),
                "broker": "Alpaca-Paper",
                "execution_price": order.filled_avg_price if order.filled_avg_price else "Pending",
                "venue": "Alpaca-Paper",
                "status": order.status,
                "timestamp": str(order.submitted_at),
            }
        except Exception as exc:
            logger.error("Alpaca order failed: %s", exc)
            return {"status": "error", "error": str(exc), "ticker": ticker, "shares": shares}


sor_router = AlpacaSORRouter()
