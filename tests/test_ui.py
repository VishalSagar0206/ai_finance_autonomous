import pytest

streamlit_testing = pytest.importorskip(
    "streamlit.testing.v1",
    reason="Streamlit UI tests require optional UI dependency: pip install streamlit",
)
AppTest = streamlit_testing.AppTest


def test_dashboard_ui():
    print("Initializing UI Test Environment...")
    at = AppTest.from_file("web/dashboard.py").run(timeout=15)
    assert not at.exception, f"App threw an exception on load: {at.exception}"
    assert at.title[0].value == "🏛️ Institutional Hedge Fund Controller"
    assert at.sidebar.selectbox[1].label == "Investor Profile"
    at.sidebar.selectbox[1].set_value("Intraday").run()
    assert at.sidebar.selectbox[1].value == "Intraday"
    initiate_btn = at.sidebar.button[0]
    assert "INITIATE" in initiate_btn.label
    print("UI Interface Test Passed! Elements rendered and interactive.")


if __name__ == "__main__":
    test_dashboard_ui()
