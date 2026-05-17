import sys
import os
import streamlit as st
import uuid
import pandas as pd
import json
import altair as alt
import time
from datetime import datetime
from streamlit_agraph import agraph, Node, Edge, Config

# Ensure the root directory is in sys.path so 'core' can be found
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.graph import adk_app
from core.state import ADKState, UserRequest, ApprovalStatus
from core.config import config
from tools.market_data import MarketDataClient

# ==========================================
# ADVANCED PAGE STYLING (Bloomberg / Foundry Aesthetic)
# ==========================================
st.set_page_config(
    page_title="ADK v4.0 | Institutional Alpha",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');
    
    /* Global Reset - Deep Dark Theme */
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
        font-family: 'Inter', sans-serif;
    }
    
    /* Clean up default Streamlit padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Custom Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }

    /* Professional Metric Widgets */
    [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 2.2rem !important;
        font-weight: 700 !important;
        color: #58a6ff !important;
    }
    [data-testid="stMetricLabel"] {
        font-family: 'Inter', sans-serif;
        font-size: 0.85rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #8b949e !important;
    }
    [data-testid="stMetricDelta"] {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Glassmorphism / Dark Panel Cards */
    .metric-card {
        background: linear-gradient(145deg, #161b22, #0d1117);
        padding: 24px;
        border-radius: 8px;
        border: 1px solid #30363d;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
        text-align: left;
        transition: transform 0.2s, border-color 0.2s;
        margin-bottom: 1rem;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: #58a6ff;
    }
    
    .metric-card h3 { 
        margin-top: 0; 
        font-size: 0.85rem; 
        color: #8b949e; 
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-family: 'Inter', sans-serif;
    }
    .metric-card p { 
        font-family: 'JetBrains Mono', monospace; 
        font-size: 1.8rem; 
        color: #3fb950; 
        margin: 0; 
        font-weight: bold; 
    }
    
    /* Terminal Console */
    .terminal-log {
        background-color: #010409;
        color: #3fb950;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        padding: 20px;
        border-radius: 8px;
        height: 500px;
        overflow-y: auto;
        border: 1px solid #30363d;
        box-shadow: inset 0 0 15px rgba(0,0,0,0.8);
        font-size: 0.85rem;
        line-height: 1.6;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
        border-bottom: 1px solid #30363d;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border: none;
        border-radius: 0;
        padding: 12px 24px;
        color: #8b949e;
        font-weight: 600;
        font-family: 'Inter', sans-serif;
    }
    .stTabs [aria-selected="true"] {
        background-color: transparent !important;
        color: #58a6ff !important;
        border-bottom: 2px solid #58a6ff !important;
    }

    /* Titles */
    h1 {
        font-family: 'Inter', sans-serif;
        font-weight: 800 !important;
        background: linear-gradient(to right, #58a6ff, #bc8cff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.02em;
        margin-bottom: 0 !important;
    }
    h2, h3, h4 {
        font-family: 'Inter', sans-serif;
        color: #c9d1d9;
    }
    
    /* Top Header Meta Info */
    .header-meta {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        color: #8b949e;
        margin-bottom: 2rem;
        border-bottom: 1px solid #30363d;
        padding-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

import graphviz

# ==========================================
# HELPER: LIVE GRAPHVIZ (FOR LOOP STABILITY)
# ==========================================
def render_live_tree(completed_nodes):
    dot = graphviz.Digraph()
    dot.attr(bgcolor='transparent')
    dot.attr('node', fontcolor='#f8fafc', fontname='Inter', fontsize='12', shape='box', style='rounded,filled')
    dot.attr('edge', color='#475569', arrowhead='vee')

    # Define Nodes
    nodes = {
        "planner": "Master Planner",
        "fundamental": "Fundamental Analyst",
        "quantitative": "Quant Analyst",
        "alternative": "Alt Data Analyst",
        "macroeconomic": "Macro Analyst",
        "sentiment": "Sentiment Analyst",
        "aggregator": "Strategy CIO",
        "coder": "Quant Coder",
        "critic": "Risk Critic",
        "optimizer": "Optimizer",
        "meta_reflective": "Meta-Reflector",
        "execution": "SOR Execution",
        "reporting": "Final Report"
    }

    for node, label in nodes.items():
        # Institutional Green for completed, Slate for pending
        fill = "#10b981" if node in completed_nodes else "#1e293b"
        dot.node(node, label, fillcolor=fill)

    # Define Hierarchy
    dot.edge("planner", "fundamental")
    dot.edge("planner", "quantitative")
    dot.edge("planner", "alternative")
    dot.edge("planner", "macroeconomic")
    dot.edge("planner", "sentiment")
    
    for n in ["fundamental", "quantitative", "alternative", "macroeconomic", "sentiment"]:
        dot.edge(n, "aggregator")
        
    dot.edge("aggregator", "coder")
    dot.edge("coder", "critic")
    dot.edge("critic", "execution")
    dot.edge("critic", "optimizer")
    dot.edge("optimizer", "meta_reflective")
    dot.edge("meta_reflective", "aggregator")
    dot.edge("execution", "reporting")

    st.graphviz_chart(dot, use_container_width=True)

# ==========================================
# HELPER: ENHANCED GRAPH VISUALIZATION (FINAL)
# ==========================================
def render_agent_graph(completed_nodes):
    nodes = []
    edges = []
    
    # Industry-level Node Definitions without Icons
    graph_layout = {
        "planner": {"label": "Master Planner", "level": 0},
        "fundamental": {"label": "Fundamental", "level": 1},
        "quantitative": {"label": "Quantitative", "level": 1},
        "alternative": {"label": "Alternative", "level": 1},
        "macroeconomic": {"label": "Macro", "level": 1},
        "sentiment": {"label": "Sentiment", "level": 1},
        "aggregator": {"label": "Strategy CIO", "level": 2},
        "coder": {"label": "Quant Coder", "level": 3},
        "critic": {"label": "Risk Critic", "level": 4},
        "optimizer": {"label": "Optimizer", "level": 5},
        "meta_reflective": {"label": "Meta-Reflector", "level": 6},
        "execution": {"label": "SOR Execution", "level": 7},
        "reporting": {"label": "Final Report", "level": 8}
    }
    
    for node_id, info in graph_layout.items():
        is_done = node_id in completed_nodes
        # Glowing effect for completed nodes
        color = "#10b981" if is_done else "#334155"
        size = 35 if is_done else 25
        
        nodes.append(Node(
            id=node_id, 
            label=info["label"], 
            size=size,
            shape="dot",
            color=color,
            font={"color": "#f8fafc", "size": 16, "face": "Inter"}
        ))
        
    # Visual Edge Connections
    edge_links = [
        ("planner", "fundamental"), ("planner", "quantitative"), ("planner", "alternative"), 
        ("planner", "macroeconomic"), ("planner", "sentiment"),
        ("fundamental", "aggregator"), ("quantitative", "aggregator"), ("alternative", "aggregator"),
        ("macroeconomic", "aggregator"), ("sentiment", "aggregator"),
        ("aggregator", "coder"), ("coder", "critic"),
        ("critic", "execution"), ("critic", "optimizer"), ("optimizer", "meta_reflective"),
        ("meta_reflective", "aggregator"), ("execution", "reporting")
    ]
    
    for source, target in edge_links:
        edge_color = "#10b981" if (source in completed_nodes and target in completed_nodes) else "#475569"
        width = 3 if (source in completed_nodes and target in completed_nodes) else 1
        edges.append(Edge(source=source, target=target, color=edge_color, width=width))
        
    config = Config(
        width=1000, 
        height=600, 
        directed=True, 
        physics=True, # Enable physics for organic feel
        hierarchical=True,
        direction="UD",
        sortMethod="directed",
        nodeHighlightBehavior=True,
        highlightColor="#38bdf8",
        shakeBeforeClick=True
    )
    
    return agraph(nodes=nodes, edges=edges, config=config)

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.title("🏦 ADK COMMAND")
    st.markdown("---")
    
    st.subheader("Global Strategy")
    asset_class = st.selectbox("Asset Class", ["Equities", "Forex", "Crypto"])
    investor_type_ui = st.selectbox("Investor Profile", ["Long Term", "Short Term", "Intraday"])
    
    # Map UI selection to Enum values expected by the backend
    type_map = {
        "Long Term": "LONG_TERM",
        "Short Term": "SHORT_TERM",
        "Intraday": "INTRADAY"
    }
    investor_type = type_map[investor_type_ui]

    tickers_input = st.text_area("Investment Universe", value="RELIANCE, AAPL, GOOGL, NVDA", height=100)
    
    st.subheader("Risk Mandate")
    risk_tolerance = st.select_slider("Tolerance", options=["Conservative", "Moderate", "Aggressive", "Hyper-Alpha"])
    horizon = st.selectbox("Horizon", ["1M", "6M", "1Y", "3Y"], index=2)
    
    st.subheader("Capital Management")
    capital = st.number_input("Starting AUM ($)", min_value=100000, value=1000000)
    
    st.markdown("---")
    if st.button("🚀 INITIATE NEURAL ORCHESTRATION", type="primary", use_container_width=True):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
        st.session_state.running = True
        st.session_state.finished = False
        st.session_state.hitl_ready = False

# ==========================================
# MAIN INTERFACE
# ==========================================
st.title("🏛️ Institutional Hedge Fund Controller")
st.markdown(f"<div class='header-meta'>CLUSTER INSTANCE: <b>ADK-V4-MAIN</b> | SESSION_ID: <b>{st.session_state.get('thread_id', 'INACTIVE')}</b> | STATUS: <b>{'ONLINE' if st.session_state.get('running') else 'STANDBY'}</b></div>", unsafe_allow_html=True)

# Global KPI Header Row
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    st.metric("Total AUM Target", f"${capital:,.0f}")
with kpi2:
    st.metric("Active Assets", len([t for t in tickers_input.split(",") if t.strip()]))
with kpi3:
    st.metric("Risk Model", risk_tolerance)
with kpi4:
    st.metric("Strategy Horizon", horizon)
st.markdown("<br>", unsafe_allow_html=True)

if st.session_state.get("running"):
    st.markdown("### 📡 Live Session: Node Traversal")
    
    col_graph, col_logs = st.columns([3, 1])
    
    with col_graph:
        graph_placeholder = st.empty()
        
    with col_logs:
        st.markdown("#### Execution Stream")
        log_terminal = st.empty()
    
    thread_config = {"configurable": {"thread_id": st.session_state.thread_id}}
    initial_state = ADKState(
        request=UserRequest(
            asset_class=asset_class,
            risk_tolerance=risk_tolerance,
            time_horizon=horizon,
            investor_type=investor_type,
            tickers=st.session_state.tickers,
        )
    ).model_dump()

    events_log = []
    completed_nodes = set()
    
    try:
        # Use status for better UX
        with st.status("Initializing High-Frequency Graph...", expanded=True) as status:
            # Initial render
            with graph_placeholder.container():
                render_live_tree(completed_nodes)

            for event in adk_app.stream(initial_state, config=thread_config):
                for node_name, _ in event.items():
                    completed_nodes.add(node_name)
                    ts = datetime.now().strftime("%H:%M:%S")
                    events_log.append(f"[{ts}] NODE_COMPLETE: {node_name.upper()}")
                    
                    # Update Logs
                    log_terminal.markdown(f"<div class='terminal-log'>{'<br>'.join(events_log[-20:])}</div>", unsafe_allow_html=True)
                    
                    # Update Live Tree (Colored)
                    with graph_placeholder.container():
                        render_live_tree(completed_nodes)
                    
                    status.update(label=f"Active Agent: {node_name.upper()}")
                    
                    state_snapshot = adk_app.get_state(thread_config)
                    if "execution" in state_snapshot.next:
                        st.session_state.hitl_ready = True
                        st.session_state.running = False
                        st.rerun()

            st.session_state.running = False
            st.session_state.finished = True
            st.rerun()

    except Exception as e:
        st.error(f"Fatal Kernel Panic: {str(e)}")
        st.session_state.running = False

# ==========================================
# POST-ORCHESTRATION ANALYTICS
# ==========================================
if st.session_state.get("hitl_ready") or st.session_state.get("finished"):
    
    thread_config = {"configurable": {"thread_id": st.session_state.thread_id}}
    state = adk_app.get_state(thread_config).values
    strategy = state.get("draft_strategy")

    if st.session_state.get("hitl_ready"):
        st.success("✅ **Neural Strategy Approved by Critic.** Awaiting Institutional Execution.")
    else:
        st.error("⚠️ **Risk Boundaries Violated.** Strategy rejected after optimization loops.")

    t1, t2, t3, t4, t5 = st.tabs(["Overview", "Backtest (PyTorch)", "Stress Test", "Audit Trail", "Alpha Code"])

    with t1:
        st.markdown("### Orchestration DAG (Completed)")
        # Determine completed nodes for visualization
        final_nodes = {"planner", "fundamental", "quantitative", "alternative", "macroeconomic", "sentiment", "aggregator", "coder", "critic"}
        if state.get("approval_status") == ApprovalStatus.APPROVED:
            final_nodes.add("stress_tester")
        render_agent_graph(final_nodes)
        
        if strategy:
            st.markdown("---")
            st.markdown("### Strategic Rationale")
            st.info(strategy.rationale)
            
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"<div class='metric-card'><h3>ID</h3><p>{strategy.strategy_id}</p></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-card'><h3>Leverage</h3><p>1.0x</p></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='metric-card'><h3>Engine</h3><p>ADK-V4.0</p></div>", unsafe_allow_html=True)
            
            # Allocation Chart
            st.markdown("#### Portfolio Composition")
            df = pd.DataFrame([{"Asset": k, "Weight": v*100} for k, v in strategy.target_allocations.items()])
            chart = alt.Chart(df).mark_bar(cornerRadiusTopLeft=10, cornerRadiusTopRight=10).encode(
                x=alt.X("Asset:N", sort='-y'),
                y="Weight:Q",
                color=alt.Color("Asset:N", scale=alt.Scale(scheme="category20b")),
                tooltip=["Asset", "Weight"]
            ).properties(height=300)
            st.altair_chart(chart, use_container_width=True)

            # Check for Metrics Log (Added in ADK v4.0 enhancements)
            metrics_log = state.get("metrics_log")
            if metrics_log and "evaluation_score" in metrics_log:
                st.markdown("---")
                st.markdown("### Institutional Evaluation & Allocation")
                
                col_score, col_pie = st.columns([1, 2])
                
                with col_score:
                    score = metrics_log["evaluation_score"]
                    st.metric(
                        "Quality Score", 
                        f"{score}/100", 
                        delta="High Quality" if score > 80 else "Moderate" if score > 50 else "High Risk",
                        delta_color="normal" if score > 50 else "inverse"
                    )
                    
                with col_pie:
                    if "sector_allocation" in metrics_log:
                        st.markdown("**Mutual Fund Sector Breakdown**")
                        sector_df = pd.DataFrame([{"Sector": k, "Weight": v*100} for k, v in metrics_log["sector_allocation"].items()])
                        pie_chart = alt.Chart(sector_df).mark_arc(innerRadius=50).encode(
                            theta=alt.Theta(field="Weight", type="quantitative"),
                            color=alt.Color(field="Sector", type="nominal", scale=alt.Scale(scheme="set3")),
                            tooltip=["Sector", "Weight"]
                        ).properties(height=250)
                        st.altair_chart(pie_chart, use_container_width=True)
            
    with t2:
        bt = state.get("backtest_results")
        if bt and bt.get("status") == "success":
            st.markdown("### Institutional Risk Scorecard")
            
            # Primary Metrics Row
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Sharpe Ratio", f"{bt.get('sharpe_ratio', 0):.2f}")
            m2.metric("Sortino Ratio", f"{bt.get('sortino_ratio', 0):.2f}", help="Risk-adjusted return focusing on downside volatility.")
            m3.metric("Calmar Ratio", f"{bt.get('calmar_ratio', 0):.2f}", help="Annual return vs Max Drawdown.")
            m4.metric("Monte Carlo Score", f"{bt.get('mc_robustness_score', 0)*100:.0f}%", help="Percentage of randomized simulations that remained profitable.")
            
            # Secondary Metrics Row
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Max Drawdown", f"{bt.get('max_drawdown', 0)*100:.1f}%")
            s2.metric("Annual Vol", f"{bt.get('annualized_volatility', 0)*100:.1f}%")
            s3.metric("NN Training Loss", f"{bt.get('nn_loss', 0):.4f}")
            s4.metric("Total Return", f"{bt.get('total_return', 0)*100:.1f}%")
            
            st.markdown("---")
            
            col_eq, col_xai = st.columns([2, 1])
            
            with col_eq:
                st.markdown("#### Cumulative Equity Curve (Out-of-Sample)")
                if "equity_curve" in bt:
                    eq_df = pd.DataFrame(bt["equity_curve"])
                    eq_df["date"] = pd.to_datetime(eq_df["date"])
                    
                    # Melt dataframe for Altair multi-line
                    eq_melted = eq_df.melt(id_vars=["date"], value_vars=["strategy", "benchmark"], 
                                         var_name="Portfolio", value_name="Cumulative Return")
                    
                    line_chart = alt.Chart(eq_melted).mark_line().encode(
                        x=alt.X("date:T", title="Date"),
                        y=alt.Y("Cumulative Return:Q", scale=alt.Scale(zero=False)),
                        color=alt.Color("Portfolio:N", scale=alt.Scale(domain=["strategy", "benchmark"], range=["#10b981", "#64748b"])),
                        tooltip=["date:T", "Portfolio:N", "Cumulative Return:Q"]
                    ).interactive().properties(height=350)
                    
                    st.altair_chart(line_chart, use_container_width=True)
                else:
                    st.info("Equity curve data not available in this build.")
                    
            with col_xai:
                st.markdown("#### Explainable AI (Feature Importance)")
                if "feature_importance" in bt:
                    feat_dict = bt["feature_importance"]
                    feat_df = pd.DataFrame([{"Feature": k, "Importance": v} for k, v in feat_dict.items()])
                    
                    bar_chart = alt.Chart(feat_df).mark_bar(cornerRadiusEnd=4).encode(
                        x=alt.X("Importance:Q", title="Weight Magnitude"),
                        y=alt.Y("Feature:N", sort="-x", title=""),
                        color=alt.Color("Importance:Q", scale=alt.Scale(scheme="tealblues"), legend=None),
                        tooltip=["Feature:N", alt.Tooltip("Importance:Q", format=".4f")]
                    ).properties(height=350)
                    
                    st.altair_chart(bar_chart, use_container_width=True)
                else:
                    st.info("XAI data not available.")
            
        elif bt and bt.get("status") == "error":
            st.error(f"Backtest Execution Error: {bt.get('error')}")
        else:
            st.info("No quantitative backtest data available.")
        stress = state.get("stress_test_report")
        if stress:
            st.subheader(f"Scenario: {stress.get('scenario_name')}")
            st.warning(f"Estimated Drawdown: {stress.get('estimated_drawdown', 0)*100:.1f}%")
            st.write("**Hedging Logic:**")
            for r in stress.get("recommendations", []):
                st.markdown(f"- {r}")

    with t4:
        st.markdown("### Agent Audit Trail")
        if state.get("feedback_loop"):
            for f in state["feedback_loop"]:
                st.error(f"REJECTION: {f}")
        if state.get("final_report"):
            st.markdown("---")
            st.write(state["final_report"])

    with t5:
        from agents.coder import QuantCoder
        if strategy:
            temp_state = ADKState(request=UserRequest(**state["request"]), draft_strategy=strategy)
            st.code(QuantCoder.generate_backtest_code(temp_state), language="python")

    # Final Action Center
    if st.session_state.get("hitl_ready"):
        st.markdown("---")
        if st.button("🚨 EXECUTE INSTITUTIONAL ORDERS", type="primary", use_container_width=True):
            with st.spinner("Routing via SOR Engine..."):
                adk_app.invoke(None, config=thread_config)
                st.balloons()
                st.session_state.hitl_ready = False
                st.session_state.finished = True
                st.rerun()
