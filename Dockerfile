# Use a stable Python 3.11 image
FROM python:3.11-slim

# System-level dependencies for building certain Python packages (e.g., chromadb)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
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

# Expose the Streamlit port
EXPOSE 8501

# Healthcheck to ensure the UI is running
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Run the dashboard as the entrypoint
ENTRYPOINT ["streamlit", "run", "web/dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
