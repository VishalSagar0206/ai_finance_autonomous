import os
from pathlib import Path
from dotenv import load_dotenv

# Workspace root: ai_finance_autonomous/
ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _looks_real_secret(value: str | None) -> bool:
    if not value:
        return False
    value = value.strip()
    if not value:
        return False
    lowered = value.lower()
    placeholders = {
        "mock",
        "mock_key",
        "your_gemini_api_key",
        "your_google_api_key",
        "your_api_key",
        "none",
        "null",
        "changeme",
    }
    return lowered not in placeholders and not lowered.startswith("your_")


class Config:
    """Centralized configuration management.

    By default the project runs in deterministic offline/demo mode. This prevents
    local tests from accidentally calling paid/cloud APIs just because a .env file
    exists. Set ADK_LIVE_MODE=1 when you intentionally want Gemini, Alpaca,
    Yahoo Finance, Chroma, etc. to be used.
    """

    ROOT_DIR = ROOT_DIR
    ENV_PATH = ENV_PATH
    OFFLINE_MODE = not _truthy(os.environ.get("ADK_LIVE_MODE"))

    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
    # gemini-2.0-flash is no longer available for many Gemini API users.
    # Keep the model configurable so future migrations only require .env edits.
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    ALPACA_API_KEY = os.environ.get("ALPACA_API_KEY")
    ALPACA_SECRET_KEY = os.environ.get("ALPACA_SECRET_KEY")
    ALPACA_BASE_URL = os.environ.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
    DB_URL = os.environ.get("DB_URL")

    @classmethod
    def has_live_llm(cls) -> bool:
        return (not cls.OFFLINE_MODE) and _looks_real_secret(cls.GOOGLE_API_KEY)

    @classmethod
    def has_live_broker(cls) -> bool:
        return (not cls.OFFLINE_MODE) and _looks_real_secret(cls.ALPACA_API_KEY) and _looks_real_secret(cls.ALPACA_SECRET_KEY)

    @classmethod
    def has_live_market_data(cls) -> bool:
        return not cls.OFFLINE_MODE


config = Config()
