import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from the workspace root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class Config:
    """Centralized configuration management."""
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
    # Add other configurations (e.g., DB URLs, Ticker defaults) here as needed.

config = Config()
