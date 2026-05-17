import os
from agents.planner import planner_agent
from core.state import ADKState, UserRequest, InvestorType

def test_planner_customization():
    print("\n--- Testing Planner Customization for Investor Types ---")
    
    # 1. Test INTRADAY
    state_intraday = ADKState(
        request=UserRequest(
            asset_class="Equities",
            risk_tolerance="Aggressive",
            time_horizon="1 Day",
            investor_type=InvestorType.INTRADAY,
            tickers=["AAPL"]
        )
    )
    
    # Mocking environment for Gemini
    os.environ["GOOGLE_API_KEY"] = "" # Force fallback logic
    
    print("Running Planner for INTRADAY...")
    result_intraday = planner_agent(state_intraday)
    tasks_intraday = result_intraday.get("plan", [])
    print(f"Intraday Tasks: {tasks_intraday}")
    assert any("intraday" in task.lower() or "high-frequency" in task.lower() for task in tasks_intraday)

    # 2. Test LONG_TERM
    state_longterm = ADKState(
        request=UserRequest(
            asset_class="Equities",
            risk_tolerance="Conservative",
            time_horizon="10 Years",
            investor_type=InvestorType.LONG_TERM,
            tickers=["AAPL"]
        )
    )
    
    print("\nRunning Planner for LONG_TERM...")
    result_longterm = planner_agent(state_longterm)
    tasks_longterm = result_longterm.get("plan", [])
    print(f"Long-term Tasks: {tasks_longterm}")
    assert any("fundamental" in task.lower() or "long-term" in task.lower() for task in tasks_longterm)

    print("\nTest PASSED: Planner correctly tailors tasks to investor type.")

if __name__ == "__main__":
    test_planner_customization()
