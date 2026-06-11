# Use a stable Python 3.11 image
FROM python:3.12-slim

# System-level dependencies for building certain Python packages (e.g., chromadb)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set up project directory
WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files first for layer caching
COPY pyproject.toml .
# Note: We'll install dependencies using uv
RUN uv pip install --system .

# Install heavy quantitative libs explicitly to ensure they are available
RUN uv pip install --system \
    torch \
    scikit-learn \
    streamlit \
    python-dotenv \
    yfinance \
    chromadb \
    langgraph \
    langchain-google-genai

# Copy the entire framework into the container
COPY . .

# Expose the API port
EXPOSE 8000

# Run the API server as the entrypoint
ENTRYPOINT ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
