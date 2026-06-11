# ADK Framework v4.0: Autonomous Institutional Trading Engine

**ADK v4.0** is an elite, production-ready, autonomous multi-agent framework designed for quantitative finance. It bridges the gap between natural language investment mandates and execution by combining Large Language Models (Gemini 1.5 Pro) with Deep Learning (PyTorch), orchestrating them via an Adaptive Directed Acyclic Graph (LangGraph).

## 🌟 The Ultimate Stack (v4.0 Upgrades)
- **Deep Learning Alpha Engine (PyTorch):** Generates and trains a Multi-Layer Perceptron (MLP) on-the-fly to predict dynamic portfolio weightings.
- **Explainable AI (XAI):** Extracts neural network tensor weights to display *Feature Importance*, bringing complete transparency to black-box models.
- **Institutional Execution (Alpaca):** Directly wired into the Alpaca Trade API for real-time paper and live market bracket order execution.
- **Decoupled Microservice (FastAPI):** A high-performance REST/SSE backend that streams real-time AI node traversals to any frontend.
- **Durable State Infrastructure (PostgreSQL):** Robust LangGraph checkpointing utilizing Postgres and Connection Pooling, deployed via Docker Compose.
- **Institutional Risk Scorecard:** Advanced verification metrics including Sortino Ratio, Calmar Ratio, and automated **Monte Carlo Robustness Testing** (100+ randomized simulations per strategy).
- **Glassmorphism Command Center:** A top-tier Streamlit UI featuring animated agent DAGs, interactive Altair equity curves, and explicit Human-In-The-Loop (HITL) compliance gates.

## 🏗️ Architecture
1. **Fan-Out Analysis:** Master Planner delegates to Fundamental, Quant, Macro, and Sentiment agents.
2. **Strategy CIO:** Aggregates findings and queries ChromaDB (Alpha Memory) for historical precedents.
3. **Quant Coder:** Autonomously writes and trains a PyTorch Neural Network to backtest the thesis.
4. **Risk Critic:** A multi-factor mathematical and logical review gate. Rejections trigger an `Optimizer` -> `Meta-Reflector` loop for self-correction.
5. **Execution:** Approved strategies hit a strict Human-In-The-Loop pause before routing to Alpaca.

## 🚀 Quick Start (Docker / Production)

1. **Configure Environment:**
   Create a `.env` file in the root:
   ```env
   ADK_LIVE_MODE=1
   GEMINI_MODEL=gemini-2.5-flash
   GOOGLE_API_KEY=your_gemini_api_key
   ALPACA_API_KEY=your_alpaca_key
   ALPACA_SECRET_KEY=your_alpaca_secret
   ALPACA_BASE_URL=https://paper-api.alpaca.markets
   DB_URL=postgresql://adk_user:adk_pass@postgres:5432/adk_state
   ```

2. **Launch the Infrastructure:**
   ```bash
   docker-compose up -d
   ```
   *This starts the FastAPI backend (Port 8000), PostgreSQL, and ChromaDB.*

3. **Launch the Command Center (UI):**
   ```bash
   uv sync --extra ui --extra live
   uv run streamlit run web/dashboard.py
   ```

## 🧪 Testing
The framework is verified by a comprehensive PyTest suite covering complex routing, deterministic LLM fallback protocols, and agentic error-correction loops.
```bash
uv run pytest tests/ -v
```
