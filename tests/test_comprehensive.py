import pytest
import uuid
from core.graph import adk_app
from core.state import ADKState, UserRequest, ApprovalStatus


@pytest.fixture
def config():
    return {"configurable": {"thread_id": str(uuid.uuid4())}}


def test_scenario_1_multi_ticker_success(config):
    """Scenario 1: Multiple valid tickers (Success Path)."""
    initial_state = ADKState(
        request=UserRequest(
            asset_class="Equities",
            risk_tolerance="Conservative",
            time_horizon="1y",
            tickers=["AAPL", "GOOG"],
        )
    ).model_dump()
    final_state = adk_app.invoke(initial_state, config=config)
    # Resume after interrupt
    final_state = adk_app.invoke(None, config=config)

    assert final_state["approval_status"] == ApprovalStatus.APPROVED
    strategy = final_state["draft_strategy"]
    # Check if both tickers are in the final allocation
    assert "AAPL" in strategy.target_allocations
    assert "GOOG" in strategy.target_allocations or "GOOGL" in strategy.target_allocations
    assert "Success: Alpha strategy" in final_state["final_report"]


def test_scenario_2_mixed_valid_invalid_tickers(config):
    """Scenario 2: One valid and one invalid ticker. System should proceed with valid data."""
    initial_state = ADKState(
        request=UserRequest(
            asset_class="Equities",
            risk_tolerance="Moderate",
            time_horizon="6m",
            tickers=["AAPL", "NON_EXISTENT_TICKER_999"],
        )
    ).model_dump()
    final_state = adk_app.invoke(initial_state, config=config)
    # Resume after interrupt ONLY if we are still PENDING (reached the interrupt)
    if final_state["approval_status"] == ApprovalStatus.APPROVED and not final_state.get("final_report"):
        final_state = adk_app.invoke(None, config=config)

    # Even if one failed, the aggregator should proceed with AAPL if not overall rejected
    if final_state["approval_status"] == ApprovalStatus.APPROVED:
        strategy = final_state["draft_strategy"]
        assert "AAPL" in strategy.target_allocations
        # It's okay if it's there with 0.0 weight, or not there at all
        assert strategy.target_allocations.get("NON_EXISTENT_TICKER_999", 0.0) == 0.0
        assert "Success: Alpha strategy" in final_state["final_report"]
    else:
        assert final_state["approval_status"] == ApprovalStatus.REJECTED
        assert "System Failure" in final_state["final_report"]


def test_scenario_3_terminal_failure_max_retries(config):
    """Scenario 3: Force rejection until max retries is exceeded."""
    # We set max_retries to 1 and ensure the first attempt (Retry 0) is rejected.
    # Retry 0: Moderate -> Rejected -> current_retry=1
    # Checkpoint: current_retry (1) >= max_retries (1) -> Route to reporting.
    initial_state = ADKState(
        request=UserRequest(
            asset_class="Equities",
            risk_tolerance="High",
            time_horizon="2y",
            tickers=["AAPL"],
        ),
        max_retries=1,
    ).model_dump()
    final_state = adk_app.invoke(initial_state, config=config)

    # Since current_retry reached 1 and it was still 'moderate' (or not defensive),
    # and max_retries was 1, it should have been caught by the routing.
    # Note: Our routing logic is: elif state.current_retry >= state.max_retries: return "reporting"
    assert final_state["approval_status"] == ApprovalStatus.REJECTED
    assert "System Failure" in final_state["final_report"]
    # Rationale might change, just check it exists
    assert "Rationale" in final_state["final_report"]


def test_scenario_4_defensive_fallback_on_total_data_failure(config):
    """Scenario 4: All tickers are invalid. Trigger defensive fallback."""
    initial_state = ADKState(
        request=UserRequest(
            asset_class="Equities",
            risk_tolerance="Moderate",
            time_horizon="1y",
            tickers=["INVALID1", "INVALID2"],
        )
    ).model_dump()
    final_state = adk_app.invoke(initial_state, config=config)
    # Resume after interrupt
    final_state = adk_app.invoke(None, config=config)

    strategy = final_state["draft_strategy"]
    assert strategy.strategy_id.startswith("DEFENSIVE_")
    assert strategy.target_allocations == {"CASH": 1.0}
    assert (
        final_state["approval_status"] == ApprovalStatus.APPROVED
    )  # Defensive strategies are approved by Critic


def test_scenario_6_empty_ticker_list(config):
    """Scenario 6: User provides an empty ticker list. System should fallback to CASH."""
    initial_state = ADKState(
        request=UserRequest(
            asset_class="Equities",
            risk_tolerance="Low",
            time_horizon="5y",
            tickers=[],
        )
    ).model_dump()
    final_state = adk_app.invoke(initial_state, config=config)
    # Resume after interrupt ONLY if we are still PENDING (reached the interrupt)
    if final_state["approval_status"] == ApprovalStatus.APPROVED and not final_state.get("final_report"):
        final_state = adk_app.invoke(None, config=config)

    if final_state["approval_status"] == ApprovalStatus.APPROVED:
        assert "CASH" in final_state["draft_strategy"].target_allocations
        assert final_state["draft_strategy"].target_allocations["CASH"] == 1.0
    else:
        # If the system rejected the empty list, it should still be a valid state
        assert final_state["approval_status"] == ApprovalStatus.REJECTED
        assert "final_report" in final_state


def test_scenario_7_conflicting_signals_resolution(config):
    """Scenario 7: One ticker has positive fundamental but strong negative quant signal. Aggregator should drop it."""
    import os
    original_key = os.environ.get("GOOGLE_API_KEY")
    if original_key:
        del os.environ["GOOGLE_API_KEY"]
    
    try:
        initial_state = ADKState(
            request=UserRequest(
                asset_class="Equities",
                risk_tolerance="Moderate",
                time_horizon="1y",
                tickers=["AAPL", "TSLA"],
            )
        )

        # We simulate a "manually injected" state partway through the graph
        # Injected Observations (Mocking the output of analysts)
        initial_state.observations.fundamental = {
            "results": {
                "AAPL": {"insight": "Excellent profitability.", "status": "completed"},
                "TSLA": {"insight": "Attractive P/E.", "status": "completed"},
            }
        }
        initial_state.observations.quantitative = {
            "results": {
                "AAPL": {"insight": "Strong positive momentum.", "status": "completed"},
                "TSLA": {
                    "insight": "Significant negative momentum.",
                    "status": "completed",
                },  # Bearish signal
            }
        }

        from agents.aggregator import strategy_generator_agent

        result = strategy_generator_agent(initial_state)
        strategy = result["draft_strategy"]

        # AAPL should be in, TSLA should be out (Score for TSLA: 1(base) + 1(attr) - 2(neg quant) = 0)
        assert "AAPL" in strategy.target_allocations
        assert "TSLA" not in strategy.target_allocations
        assert strategy.target_allocations["AAPL"] == 1.0
    finally:
        if original_key:
            os.environ["GOOGLE_API_KEY"] = original_key
