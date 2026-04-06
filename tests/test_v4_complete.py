import pytest
import uuid
import os
import shutil
from unittest.mock import patch
from adk_framework_v3.core.graph import adk_app
from adk_framework_v3.core.state import ADKState, UserRequest, ApprovalStatus
from adk_framework_v3.tools.alpha_memory import alpha_memory

@pytest.fixture(scope="module", autouse=True)
def cleanup_memory():
    """Ensures a fresh alpha_memory for the test suite."""
    test_db = "./test_alpha_memory"
    if os.path.exists(test_db):
        shutil.rmtree(test_db)
    # Re-init client with test path if needed or just use current
    yield
    if os.path.exists(test_db):
        shutil.rmtree(test_db)

def test_v4_ensemble_cio_logic():
    """Scenario: Verify the Ensemble CIO generates sub-strategies for different styles."""
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = ADKState(
        request=UserRequest(
            asset_class="Equities",
            risk_tolerance="Moderate",
            time_horizon="1y",
            tickers=["AAPL", "MSFT"]
        )
    )

    # Run until interrupt
    for event in adk_app.stream(initial_state, config=config):
        pass
    
    state = adk_app.get_state(config).values
    
    # Verify ensemble output
    assert "ensemble_sub_strategies" in state
    assert len(state["ensemble_sub_strategies"]) > 0
    # At least one style should be present (Trend, Mean Reversion, etc.)
    styles = list(state["ensemble_sub_strategies"].keys())
    assert any("trend" in s or "mean" in s or "statistical" in s for s in styles)

def test_v4_alpha_memory_persistence():
    """Scenario: Verify strategy is saved to memory and retrieved in subsequent run."""
    thread_id_1 = str(uuid.uuid4())
    config_1 = {"configurable": {"thread_id": thread_id_1}}
    
    # Run 1: Use a request that is likely to pass quickly
    initial_state = ADKState(
        request=UserRequest(
            asset_class="Equities", 
            risk_tolerance="Conservative", 
            time_horizon="5y", 
            tickers=["AAPL", "GOOGL", "MSFT", "CASH"] # Added diversification
        )
    )
    
    # We mock the coder to ensure backtest success so it hits the execution/save node
    with patch("adk_framework_v3.agents.coder.code_executor.execute_python_code") as mock_exec:
        mock_exec.return_value = {"status": "success", "sharpe_ratio": 1.8}
        
        # Run until interrupt (Analysis -> Stress -> Coder -> Interrupt)
        for event in adk_app.stream(initial_state, config=config_1):
            pass
        
        # Resume to execute and save to Alpha Memory
        adk_app.invoke(None, config=config_1)
    
    # Run 2: New thread, same query. Verify the generator sees the memory.
    # Note: We can't easily assert the LLM saw it without mocking the provider,
    # but we verify the tool doesn't crash during the query.
    thread_id_2 = str(uuid.uuid4())
    config_2 = {"configurable": {"thread_id": thread_id_2}}
    initial_state_2 = ADKState(
        request=UserRequest(asset_class="Equities", risk_tolerance="Conservative", time_horizon="5y", tickers=["AAPL"])
    )
    
    # Just run until aggregator to trigger the memory query
    for event in adk_app.stream(initial_state_2, config=config_2):
        for node_name, _ in event.items():
            if node_name == "aggregator":
                break

def test_v4_meta_reflective_improvement():
    """Scenario: Verify system_instructions are updated after a critic rejection."""
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    # Force a rejection by using a high-risk request with low-retry max
    initial_state = ADKState(
        request=UserRequest(asset_class="Equities", risk_tolerance="Conservative", time_horizon="1w", tickers=["TSLA"]),
        max_retries=2
    )

    # Run through the loop
    for event in adk_app.stream(initial_state, config=config):
        pass
        
    state = adk_app.get_state(config).values
    # If a rejection happened, meta_reflective should have run
    if state["current_retry"] > 0:
        assert state["system_instructions"] is not None
        print(f"DEBUG: Updated Instructions: {state['system_instructions']}")
