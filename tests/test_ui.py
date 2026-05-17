from streamlit.testing.v1 import AppTest
import os

def test_dashboard_ui():
    print("Initializing UI Test Environment...")
    
    # Initialize the AppTest targeting our dashboard
    at = AppTest.from_file("web/dashboard.py").run(timeout=15)
    
    # 1. Verify basic rendering (no syntax/import errors)
    assert not at.exception, f"App threw an exception on load: {at.exception}"
    
    # 2. Verify UI elements exist
    assert at.title[0].value == "🏛️ Institutional Hedge Fund Controller"
    
    # 3. Simulate user interaction in the sidebar
    # The selectbox for Investor Profile is the second selectbox (index 1) 
    # since Asset Class is index 0.
    assert at.sidebar.selectbox[1].label == "Investor Profile"
    
    # Change the value to "Intraday"
    at.sidebar.selectbox[1].set_value("Intraday").run()
    
    # Check if the value was updated
    assert at.sidebar.selectbox[1].value == "Intraday"
    
    # 4. Simulate clicking the Initiate button
    initiate_btn = at.sidebar.button[0]
    assert "INITIATE" in initiate_btn.label
    
    # Note: We won't actually click it in this CI test because it triggers an asynchronous 
    # generator with LangGraph that runs infinitely or requires LLM access, which can hang the test runner.
    # However, verifying the state change and widget interaction proves the UI is wired correctly.
    
    print("✅ UI Interface Test Passed! Elements rendered and interactive.")

if __name__ == "__main__":
    test_dashboard_ui()
