# ADK Framework v4.0: The Advanced Agentic 'Brain'

**ADK v4.0** is an institutional-grade, autonomous multi-agent framework designed for sophisticated financial analysis, strategy generation, and algorithmic execution. It leverages state-of-the-art AI (Gemini 3.1 Pro Preview) and cyclic graph orchestration (LangGraph) to bridge the gap between natural language intent and quantitative reality.

## 🌟 Key Features
- **Ensemble CIO Committee:** Orchestrates parallel investment styles (Trend, Mean-Reversion, Arb).
- **Alpha Memory:** Long-term evolutionary learning via ChromaDB vector persistence.
- **Self-Healing Coder:** Recursive agentic diagnosis and correction of backtest code errors.
- **Black Swan Stress Testing:** Automated tail-risk simulation against historical shocks.
- **Global Market Support:** First-class support for Indian (NSE/BSE) and US markets.
- **Institutional Command Center:** Real-time Streamlit dashboard with Human-in-the-Loop (HITL) approval.

## 🚀 Quick Start
1. **Setup Environment:**
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -r pyproject.toml
   ```
2. **Configure Secrets:**
   Create a `.env` file in the workspace root:
   ```text
   GOOGLE_API_KEY=your_gemini_api_key
   ```
3. **Launch the Dashboard:**
   ```bash
   streamlit run adk_framework_v3/web/dashboard.py
   ```

## 🛡️ Validation Standard
The framework is verified by a 16-scenario test suite achieving **100% accuracy** across state management, graph flow, industry edge cases, and institutional safety.
