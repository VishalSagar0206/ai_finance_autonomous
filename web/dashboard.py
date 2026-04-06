import streamlit as st
import uuid
import pandas as pd
import json
from adk_framework_v3.core.graph import adk_app
from adk_framework_v3.core.state import ADKState, UserRequest
from adk_framework_v3.core.config import config

st.set_page_config(page_title="ADK v4.0: Autonomous Hedge Fund", layout="wide")

st.title("🏛️ ADK v4.0: Institutional Command Center")
st.markdown("---")

# Sidebar: Configuration
with st.sidebar:
    st.header("🎯 Strategy Config")
    asset_class = st.selectbox("Asset Class", ["Equities", "Forex", "Crypto"])
    risk_tolerance = st.select_slider("Risk Tolerance", options=["Conservative", "Moderate", "Aggressive"])
    tickers_input = st.text_input("Tickers (comma separated)", value="RELIANCE, AAPL, GOOG")
    time_horizon = st.selectbox("Time Horizon", ["1 Month", "6 Months", "1 Year", "2 Years"])
    
    if st.button("🚀 LAUNCH THE BRAIN", use_container_width=True):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.tickers = [t.strip() for t in tickers_input.split(",")]
        st.session_state.running = True
        st.session_state.events = []
        st.session_state.hitl_ready = False

# Main Area: Live Execution Monitor
if "running" in st.session_state and st.session_state.running:
    st.header("📡 Live Agent Orchestration")
    
    # Execution Thread
    thread_config = {"configurable": {"thread_id": st.session_state.thread_id}}
    initial_state = ADKState(
        request=UserRequest(
            asset_class=asset_class,
            risk_tolerance=risk_tolerance,
            time_horizon=time_horizon,
            tickers=st.session_state.tickers
        )
    )

    # Containers for live updates
    log_container = st.empty()
    col1, col2 = st.columns(2)
    
    # stream the graph
    events_log = []
    try:
        for event in adk_app.stream(initial_state, config=thread_config):
            for node_name, state_update in event.items():
                events_log.append(f"✅ Finished Node: {node_name}")
                log_container.code("\n".join(events_log))
                
                # Check for HITL state
                state_snapshot = adk_app.get_state(thread_config)
                if "execution" in state_snapshot.next:
                    st.session_state.hitl_ready = True
                    st.session_state.running = False
                    st.rerun()

    except Exception as e:
        st.error(f"Brain Execution Error: {str(e)}")

# Post-Analysis UI
if "hitl_ready" in st.session_state and st.session_state.hitl_ready:
    st.success("🎯 Strategy Ready for Review & Approval")
    
    thread_config = {"configurable": {"thread_id": st.session_state.thread_id}}
    state = adk_app.get_state(thread_config).values
    
    # 1. Strategy Dashboard
    st.subheader("📋 Draft Strategy Summary")
    strategy = state.get("draft_strategy")
    if strategy:
        c1, c2, c3 = st.columns(3)
        c1.metric("ID", strategy.strategy_id)
        c2.metric("Risk Mode", strategy.parameters.get("risk_mode", "N/A"))
        
        st.info(f"**Rationale:** {strategy.rationale}")
        
        st.write("**Target Allocations:**")
        st.table(pd.DataFrame([strategy.target_allocations]))

    # 2. Stress Test & Backtest
    col_st, col_bt = st.columns(2)
    
    with col_st:
        st.subheader("🌪️ Stress Test Report")
        stress = state.get("stress_test_report")
        if stress:
            st.warning(f"Scenario: {stress.get('scenario_name')}")
            st.write(f"Resilient: {'✅ Yes' if stress.get('is_resilient') else '❌ No'}")
            st.write(f"Est. Drawdown: {stress.get('estimated_drawdown')*100:.1f}%")
            st.write("**Recs:** " + ", ".join(stress.get("recommendations", [])))

    with col_bt:
        st.subheader("📈 Backtest Metrics")
        bt = state.get("backtest_results")
        if bt:
            st.metric("Sharpe Ratio", f"{bt.get('sharpe_ratio', 0):.2f}")
            st.metric("Max Drawdown", f"{bt.get('max_drawdown', 0)*100:.1f}%")

    # 3. HITL Action
    st.markdown("---")
    st.header("⚡ HUMAN-IN-THE-LOOP APPROVAL")
    if st.button("🚨 CONFIRM & EXECUTE ORDERS", type="primary", use_container_width=True):
        with st.spinner("Routing orders to Alpaca..."):
            adk_app.invoke(None, config=thread_config)
            st.balloons()
            st.success("Execution Complete. Transaction logged.")
            st.session_state.hitl_ready = False
