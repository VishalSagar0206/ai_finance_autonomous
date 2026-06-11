# Running the fixed project

The project now runs in deterministic offline mode by default. That means the multi-agent graph does not require Gemini, Yahoo Finance, ChromaDB, Alpaca, LangGraph, Streamlit, or live network access just to complete an end-to-end run.

## Quick run

```bash
python main.py
```

This runs every agent stage, auto-approves the human-in-the-loop execution checkpoint for the demo, and prints the final report.

## Tests

```bash
python -m pytest tests -q
```

The Streamlit UI test is skipped automatically when Streamlit is not installed. Install the UI extra to run it:

```bash
pip install -e ".[ui,test]"
python -m pytest tests/test_ui.py -q
```

## Live API mode

Offline mode is the default. To intentionally call live services, create `.env` from `.env.example`, fill your keys, and set:

```env
ADK_LIVE_MODE=1
```

Without `ADK_LIVE_MODE=1`, keys in `.env` are not used for live LLM/broker/market-data calls. This prevents accidental API calls while debugging.
