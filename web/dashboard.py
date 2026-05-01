import streamlit as st
import uuid
import pandas as pd
import json
import altair as alt
import time
from datetime import datetime
from streamlit_agraph import agraph, Node, Edge, Config

from core.graph import adk_app
from core.state import ADKState, UserRequest, ApprovalStatus
from core.config import config
from tools.market_data import MarketDataClient

# ==========================================
# ADVANCED PAGE STYLING (Glassmorphism & Neon)
# ==========================================
st.set_page_config(
    page_title="ADK v4.0 | Institutional Alpha",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Premium Dark Theme */
    .stApp {
        background: radial-gradient(circle at top left, #0f172a, #020617);
        color: #e2e8f0;
    }
    
    /* Custom Sidebar */
    [data-testid="stSidebar"] {
        background-color: rgba(15, 23, 42, 0.8);
        border-right: 1px solid #1e293b;
    }

    /* Glassmorphism Cards */
    .metric-card {
        background: rgba(30, 41, 59, 0.5);
        backdrop-filter: blur(10px);
        padding: 24px;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        text-align: left;
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        border-color: #38bdf8;
    }
    
    /* Terminal Console */
    .terminal-log {
        background-color: #000;
        color: #10b981;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        padding: 20px;
        border-radius: 12px;
        height: 500px;
        overflow-y: auto;
        border: 1px solid #064e3b;
        box-shadow: inset 0 0 10px #064e3b;
        font-size: 0.85rem;
        line-height: 1.5;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(30, 41, 59, 0.5);
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        color: #94a3b8;
    }
    .stTabs [aria-selected="true"] {
        background-color: #38bdf8 !important;
        color: #fff !important;
    }

    /* Titles */
    h1 {
        font-weight: 800 !important;
        background: linear-gradient(to right, #38bdf8, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.02em;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# HELPER: ENHANCED GRAPH VISUALIZATION
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
st.markdown(f"**Cluster Instance:** `ADK-V4-MAIN` | **Session:** `{st.session_state.get('thread_id', 'INACTIVE')}`")

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
            tickers=st.session_state.tickers,
        )
    ).model_dump()

    events_log = []
    completed_nodes = set()
    
    try:
        # Use status for better UX
        with st.status("Initializing High-Frequency Graph...", expanded=True) as status:
            for event in adk_app.stream(initial_state, config=thread_config):
                for node_name, _ in event.items():
                    completed_nodes.add(node_name)
                    ts = datetime.now().strftime("%H:%M:%S")
                    events_log.append(f"[{ts}] NODE_COMPLETE: {node_name.upper()}")
                    
                    log_terminal.markdown(f"<div class='terminal-log'>{'<br>'.join(events_log[-20:])}</div>", unsafe_allow_html=True)
                    
                    with graph_placeholder.container():
                        render_agent_graph(completed_nodes)
                    
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
        if strategy:
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
            
    with t2:
        bt = state.get("backtest_results")
        if bt and bt.get("status") == "success":
            st.markdown("### Neural Backtest Performance")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Sharpe Ratio", f"{bt.get('sharpe_ratio', 0):.2f}")
            m2.metric("Max Drawdown", f"{bt.get('max_drawdown', 0)*100:.1f}%")
            m3.metric("Annual Vol", f"{bt.get('annualized_volatility', 0)*100:.1f}%")
            m4.metric("NN Loss", f"{bt.get('nn_loss', 0):.4f}")
            
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
