import pytest
import uuid
from adk_framework_v3.core.graph import adk_app
from adk_framework_v3.core.state import ADKState, UserRequest, ApprovalStatus

@pytest.fixture
def thread_id():
    return str(uuid.uuid4())

def test_institutional_stress_tester(thread_id):
    """Verifies that the stress tester node generates a valid report in the state."""
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = ADKState(
        request=UserRequest(
            asset_class="Equities",
            risk_tolerance="Moderate",
            time_horizon="1y",
            tickers=["AAPL"]
        )
    )

    # We run until the 'coder' node to ensure it passed stress testing
    # Since we have an interrupt at 'execution', we can just run until it stops
    final_state = None
    for event in adk_app.stream(initial_state, config=config):
        for node_name, state_update in event.items():
            if node_name == "stress_tester":
                # Check if stress test report exists in the update or state
                pass

    # Inspect state after interrupt
    state_snapshot = adk_app.get_state(config)
    state = state_snapshot.values
    
    assert state["stress_test_report"] is not None
    assert "scenario_name" in state["stress_test_report"]
    assert "is_resilient" in state["stress_test_report"]

from unittest.mock import patch

def test_institutional_hitl_interrupt(thread_id):
    """Verifies the graph correctly interrupts before execution."""
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = ADKState(
        request=UserRequest(
            asset_class="Equities",
            risk_tolerance="Conservative",
            time_horizon="1y",
            tickers=["GOOG"]
        )
    )

    # Force coder to succeed by mocking the underlying tool
    with patch("adk_framework_v3.agents.coder.code_executor.execute_python_code") as mock_exec:
        mock_exec.return_value = {"status": "success", "sharpe_ratio": 2.0}

        # Run until interrupt
        # stream() will stop at the interrupt_before node
        for event in adk_app.stream(initial_state, config=config):
            pass

        # The state should be 'suspended' before the 'execution' node
        state_snapshot = adk_app.get_state(config)
        
        # next is a tuple of node names that are ready to run
        print(f"DEBUG: state_snapshot.next={state_snapshot.next}")
        assert "execution" in state_snapshot.next
        
        # To 'Approve' and continue
        adk_app.invoke(None, config=config)
        
        # Verify it finished
        final_snapshot = adk_app.get_state(config)
        assert final_snapshot.next == ()
        holdings = final_snapshot.values["portfolio"].holdings if hasattr(final_snapshot.values["portfolio"], "holdings") else final_snapshot.values["portfolio"].get("holdings")
        assert holdings is not None

def test_indian_market_support(thread_id):
    """Verifies that Indian tickers (RELIANCE) are correctly formatted and analyzed."""
    config = {"configurable": {"thread_id": thread_id}}
    # We pass 'RELIANCE' without suffix
    initial_state = ADKState(
        request=UserRequest(
            asset_class="Equities",
            risk_tolerance="Moderate",
            time_horizon="2y",
            tickers=["RELIANCE"]
        )
    )

    # Run until interrupt
    adk_app.invoke(initial_state, config=config)
    
    state_snapshot = adk_app.get_state(config)
    state = state_snapshot.values
    
    # Robust data access for check-pointed state
    def get_results(obj):
        if hasattr(obj, "results"): return obj.results
        return obj.get("results") if isinstance(obj, dict) else {}

    obs = state.get("observations")
    quant_obs = obs.quantitative if hasattr(obs, "quantitative") else obs.get("quantitative")
    quant_results = get_results(quant_obs)

    assert "RELIANCE.NS" in quant_results
    status = quant_results["RELIANCE.NS"].get("status") if isinstance(quant_results["RELIANCE.NS"], dict) else quant_results["RELIANCE.NS"].status
    assert status == "completed"
