# ADK v4.0 Architectural Design (Ultimate Stack)

## 1. System Topology
The ADK v4.0 framework has transitioned from a monolithic prototype to a fully decoupled, cloud-native microservice architecture.

- **Frontend (UI):** Streamlit (Glassmorphism Dashboard) / Next.js.
- **Backend (API):** FastAPI with Server-Sent Events (SSE) for real-time LangGraph streaming.
- **Orchestration:** LangGraph (Cyclic DAG execution).
- **Deep Learning Core:** PyTorch + Scikit-Learn.
- **Durable State & Memory:** PostgreSQL (Checkpointer) + ChromaDB (Vector Search).
- **Execution:** Alpaca Trade API.

## 2. LangGraph Orchestration (Cyclic DAG)
The core logic flows through a self-healing, multi-agent loop:

```text
[Planner] ---> [Analysts (Fundamental, Quant, Macro, Sentiment)]
                 |
                 v
           [Strategy CIO] <-----------------------------------------|
                 |                                                  |
                 v                                                  |
           [Quant Coder] (Trains PyTorch Model)                     |
                 |                                                  |
                 v                                                  |
          [Risk Critic] ----(Rejected)----> [Optimizer] ---> [Meta-Reflector]
                 |
             (Approved)
                 |
         [HITL Interrupt] (Awaiting Human Compliance)
                 |
           [Execution] (Alpaca API)
                 |
            [Reporting]
```

## 3. The Deep Learning Alpha Engine
Instead of basic mathematical backtests, the `Quant Coder` writes and executes a **Multi-Layer Perceptron (PyTorch)**.
1. **Feature Engineering:** Extracts historical returns over an `N-day` lookback window.
2. **Training:** Trains the `AlphaNet` model on 80% of historical data.
3. **Prediction:** Evaluates the 20% Out-Of-Sample data to predict asset movement.
4. **XAI (Explainable AI):** Extracts layer weights (`fc1.weight`) to generate Feature Importance metrics, explaining *why* the AI made the trade.

## 4. Hierarchical Shared Session State (H-SSS)
The LangGraph state is strictly typed using Pydantic and persisted to **PostgreSQL**.
- **UserRequest:** Initial capital, risk tolerance, and asset universe.
- **Observations:** Parallel agent outputs.
- **DraftStrategy:** Current allocation proposals.
- **BacktestResults:** Output of the PyTorch neural network, including the Equity Curve.
- **FeedbackLoop:** Accumulates AI critiques to prevent repeated mistakes during optimization cycles.

## 5. Security & Infrastructure
- **Sandboxed Execution:** AI-generated Python code executes locally (intended for Docker/Firecracker in prod).
- **Connection Pooling:** Uses `psycopg_pool` to handle concurrent state retrieval requests.
- **Secrets Management:** Environment variables strictly manage Alpaca and Gemini keys.
