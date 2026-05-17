import os
from core.graph import adk_app
from core.state import ADKState, UserRequest, InvestorType
import uuid

def test_reporting_and_investor_customization():
    print("\n--- Testing ADK v4.0 Reporting and Investor Customization ---")
    
    # 1. Setup State for a Short-Term Investor
    state = ADKState(
        request=UserRequest(
            asset_class="Equities",
            risk_tolerance="Aggressive",
            time_horizon="1 Month",
            investor_type=InvestorType.SHORT_TERM,
            tickers=["RELIANCE", "TCS", "AAPL"]
        )
    )
    
    # Mocking some intermediate results to skip complex agent logic if needed
    # but let's try running the actual graph nodes if possible.
    # For a unit test of ReportingAgent, we can just call it directly.
    
    from agents.reporting import reporting_agent
    from core.state import DraftStrategy, ApprovalStatus
    
    state.draft_strategy = DraftStrategy(
        strategy_id=f"STRAT-{uuid.uuid4().hex[:6]}",
        rationale="Short-term momentum play on Indian IT and Energy bluechips.",
        parameters={"lookback": 20},
        target_allocations={"RELIANCE.NS": 0.4, "TCS.NS": 0.4, "AAPL": 0.1, "CASH": 0.1}
    )
    state.approval_status = ApprovalStatus.APPROVED
    state.backtest_results = {"status": "success", "sharpe": 1.5}
    state.stress_test_report = {"status": "success", "robustness_score": 0.85}
    
    print("\nRunning Reporting Agent...")
    result = reporting_agent(state)
    
    report = result.get("final_report", "")
    print("\n--- Generated Report ---")
    print(report)
    
    # Assertions
    assert "Evaluation Metric" in report
    assert "Overall Score" in report
    assert "Sector Breakdown" in report
    assert f"Investor Profile:** {InvestorType.SHORT_TERM.value}" in report
    assert "Energy" in report or "Technology" in report or "Information Technology" in report
    
    print("\nTest PASSED: Report generated with metrics and sector allocation.")

if __name__ == "__main__":
    # Mock GOOGLE_API_KEY to avoid actual LLM calls during this check if not present
    if "GOOGLE_API_KEY" not in os.environ:
        os.environ["GOOGLE_API_KEY"] = "mock_key"
        
    try:
        test_reporting_and_investor_customization()
    except Exception as e:
        print(f"Test FAILED: {e}")
        import traceback
        traceback.print_exc()
