import pytest
import uuid
from unittest.mock import patch, MagicMock
from core.graph import adk_app
from core.state import ADKState, UserRequest, ApprovalStatus


@pytest.fixture
def thread_config():
    return {"configurable": {"thread_id": str(uuid.uuid4())}}


def test_industry_edge_case_self_correction(thread_config):
    """
    Industry Edge Case: Simulation of a 'Runtime Error' in generated backtest code.
    Verifies that the system detects the error, increments backtest_attempts,
    and would (in a real run) feed the error back to Gemini for correction.
    """
    # We will mock code_executor to fail on the first attempt and succeed on the second
    with patch("agents.coder.code_executor.execute_python_code") as mock_exec:
        # First call returns error, second returns success
        mock_exec.side_effect = [
            {"status": "error", "error": "NameError: name 'pd' is not defined"},
            {"status": "success", "sharpe_ratio": 1.5, "max_drawdown": -0.1},
        ]

        initial_state = ADKState(
            request=UserRequest(
                asset_class="Equities",
                risk_tolerance="Moderate",
                time_horizon="1y",
                tickers=["AAPL"],
            ),
            max_backtest_retries=2,
        ).model_dump()

        # Run the graph
        final_state = adk_app.invoke(initial_state, config=thread_config)

        # Verify self-correction flow
        # It should have called coder twice (one failure, one success)
        # Note: LangGraph loop logic will hit the coder node, then routing, then coder node again.
        assert final_state["backtest_attempts"] >= 2
        assert "SUCCESS" in final_state["execution_logs"]
        assert final_state["backtest_results"]["status"] == "success"


def test_industry_edge_case_risk_conflict(thread_config):
    """
    Industry Edge Case: High-Risk request vs Low-Risk constraint.
    Verifies the Critic correctly rejects aggressive strategies that don't align with state constraints.
    """
    # Requesting volatile assets (NVDA, TSLA) but setting a 'Conservative' tolerance
    initial_state = ADKState(
        request=UserRequest(
            asset_class="Equities",
            risk_tolerance="Conservative",
            time_horizon="1y",
            tickers=["NVDA", "TSLA"],
        )
    ).model_dump()

    final_state = adk_app.invoke(initial_state, config=thread_config)

    # If the AI is working correctly, the Aggregator should have been forced into
    # a defensive posture or the Critic should have triggered a retry.
    assert final_state["approval_status"] == ApprovalStatus.APPROVED
    strategy = final_state["draft_strategy"]

    # In a conservative mode, the system should either drop high-vol tickers or reduce weights.
    # Our 'extreme_defensive' fallback results in CASH.
    if strategy.strategy_id.startswith("DEFENSIVE_"):
        assert "CASH" in strategy.target_allocations
    else:
        # If it passed, verify it isn't too aggressive (this depends on Gemini's reasoning)
        rationale = strategy.rationale.lower()
        params_str = str(strategy.parameters).lower()
        assert (
            "conservative" in rationale
            or "defensive" in rationale
            or "defensive" in params_str
        )


def test_industry_edge_case_partial_api_failure(thread_config):
    """
    Industry Edge Case: Market data for one ticker is corrupt/missing.
    Verifies the Aggregator handles partial success without crashing the whole pipeline.
    """
    initial_state = ADKState(
        request=UserRequest(
            asset_class="Equities",
            risk_tolerance="Moderate",
            time_horizon="1y",
            tickers=["AAPL", "SUSPENDED_TICKER_X"],
        )
    ).model_dump()

    final_state = adk_app.invoke(initial_state, config=thread_config)

    assert final_state["approval_status"] == ApprovalStatus.APPROVED
    strategy = final_state["draft_strategy"]
    # Should have ignored SUSPENDED_TICKER_X and built strategy for AAPL
    assert "AAPL" in strategy.target_allocations
    assert "SUSPENDED_TICKER_X" not in strategy.target_allocations
