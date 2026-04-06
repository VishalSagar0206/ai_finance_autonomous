import sqlite3
import json
import os
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class TradeLedger:
    """
    Permanent SQL Ledger for trade confirmations and performance tracking.
    Implements the 'Transaction Ledger' from the diagram.
    """

    def __init__(self, db_path: str = "trade_ledger.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initializes the SQLite ledger table."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    strategy_id TEXT,
                    ticker TEXT,
                    shares INTEGER,
                    broker TEXT,
                    status TEXT,
                    raw_data TEXT
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Ledger: Initialization failed. {str(e)}")

    def log_execution(self, strategy_id: str, records: List[Dict[str, Any]]):
        """Logs multiple execution records to the SQL ledger."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            for rec in records:
                cursor.execute("""
                    INSERT INTO trades (strategy_id, ticker, shares, broker, status, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    strategy_id,
                    rec.get("ticker"),
                    rec.get("shares"),
                    rec.get("broker"),
                    rec.get("status"),
                    json.dumps(rec)
                ))
            conn.commit()
            conn.close()
            logger.info(f"Ledger: Persisted {len(records)} records for {strategy_id}.")
        except Exception as e:
            logger.error(f"Ledger: Log failed. {str(e)}")

# Singleton instance
trade_ledger = TradeLedger()
