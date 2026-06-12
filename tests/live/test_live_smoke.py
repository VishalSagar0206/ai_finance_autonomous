import os
import uuid

import pytest

pytestmark = pytest.mark.live


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


@pytest.fixture(autouse=True)
def require_live_mode():
    if not _truthy(os.getenv("ADK_LIVE_MODE")):
        pytest.skip("ADK_LIVE_MODE=1 is required for live tests.")

    if not os.getenv("GOOGLE_API_KEY"):
        pytest.skip("GOOGLE_API_KEY is required for live Gemini tests.")


def test_live_config_detects_gemini():
    from core.config import config

    assert config.OFFLINE_MODE is False
    assert config.has_live_llm() is True


def test_live_gemini_smoke():
    from langchain_google_genai import ChatGoogleGenerativeAI
    from core.config import config

    model = getattr(config, "GEMINI_MODEL", "gemini-2.5-flash")

    llm = ChatGoogleGenerativeAI(
        model=model,
        google_api_key=config.GOOGLE_API_KEY,
    )

    response = llm.invoke("Reply with exactly one word: PONG")

    assert "pong" in str(response.content).lower()


def test_live_agent_chain_smoke_reaches_backtest():
    from core.graph import adk_app
    from core.state import ADKState, UserRequest, InvestorType

    initial_state = ADKState(
        request=UserRequest(
            asset_class="Equities",
            risk_tolerance="Moderate",
            time_horizon="6-12 Months",
            investor_type=InvestorType.LONG_TERM,
            tickers=["AAPL", "MSFT"],
            additional_constraints="Live smoke test. Prefer risk-aware diversified strategy.",
        )
    ).model_dump()

    config = {"configurable": {"thread_id": f"live-test-{uuid.uuid4()}"}}

    events = list(adk_app.stream(initial_state, config=config))
    executed_nodes = [list(event.keys())[0] for event in events]

    assert "planner" in executed_nodes
    assert "fundamental" in executed_nodes
    assert "quantitative" in executed_nodes
    assert "sentiment" in executed_nodes
    assert "aggregator" in executed_nodes
    assert "coder" in executed_nodes

    snapshot = adk_app.get_state(config)
    state = snapshot.values

    assert state["draft_strategy"] is not None
    assert state["backtest_results"] is not None
    assert state["backtest_results"].get("status") == "success"
