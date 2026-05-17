import os
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from .state import ADKState, ApprovalStatus

from agents.planner import planner_agent as planner_node
from agents.ensemble import (
    ensemble_cio_agent as aggregator_generator_node,
)
from agents.critic import multi_factor_critic_agent as critic_node
from agents.stress_tester import (
    stress_tester_agent as stress_tester_node,
)
from agents.meta_monitor import (
    meta_reflective_agent as meta_reflective_node,
)
from agents.fan_out.fundamental import (
    fundamental_analyst_agent as fundamental_node,
)
from agents.fan_out.quantitative import (
    quantitative_analyst_agent as quantitative_node,
)
from agents.fan_out.sentiment import (
    sentiment_analyst_agent as sentiment_node,
)

from agents.coder import coder_agent as coder_node
from agents.execution import execution_agent as execution_node
from agents.reporting import reporting_agent as reporting_node
from agents.optimizer import optimizer_agent as optimizer_node

# --- 1. Node Definitions (Remaining Mocks) ---


def alternative_node(state: ADKState) -> Dict[str, Any]:
    print("   -> [Parallel] Alternative Data checking satellite/foot traffic.")
    return {"observations": {"alternative": {"insight": "High retail traffic"}}}


def macroeconomic_node(state: ADKState) -> Dict[str, Any]:
    print("   -> [Parallel] Macroeconomic parsing global yield curves.")
    return {"observations": {"macroeconomic": {"insight": "Fed dovish tilt"}}}

# --- 2. Conditional Edge Logic ---


def critic_routing(state: ADKState) -> str:
    """Routes based on the Multi-Factor Critic's approval status."""
    if state.approval_status == ApprovalStatus.APPROVED:
        return "stress_tester"
    elif state.current_retry >= state.max_retries:
        print("   [Routing] MAX RETRIES EXCEEDED. Abandoning strategy.")
        return "reporting"
    else:
        return "optimizer"


def coder_routing(state: ADKState) -> str:
    """Self-Correction Routing: Retries if backtest failed. On success, goes to Critic."""
    results = state.backtest_results or {}
    if results.get("status") == "success":
        return "critic"

    if state.backtest_attempts < state.max_backtest_retries:
        print(
            f"   [Routing] Backtest failed. Retrying (Attempt {state.backtest_attempts}/{state.max_backtest_retries})."
        )
        return "coder"

    print("   [Routing] Backtest failed repeatedly. Routing to Reporting.")
    return "reporting"


from langgraph.checkpoint.memory import MemorySaver

# --- 3. Graph Construction ---


def build_graph() -> StateGraph:
    workflow = StateGraph(ADKState)
    
    # Industry-level Durable Checkpointing
    db_url = os.environ.get("DB_URL")
    if db_url:
        print(f"📦 Production Mode: Using PostgreSQL Checkpointer at {db_url}")
        from langgraph.checkpoint.postgres import PostgresSaver
        from psycopg_pool import ConnectionPool
        
        # We need a pool for high-concurrency production trading
        pool = ConnectionPool(conninfo=db_url, max_size=20)
        checkpointer = PostgresSaver(pool)
        # Note: In a real app, we would run checkpointer.setup() at startup
    else:
        print("💾 Dev Mode: Using In-Memory Checkpointer")
        checkpointer = MemorySaver()

    # Add Nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("fundamental", fundamental_node)
    workflow.add_node("quantitative", quantitative_node)
    workflow.add_node("alternative", alternative_node)
    workflow.add_node("macroeconomic", macroeconomic_node)
    workflow.add_node("sentiment", sentiment_node)
    workflow.add_node("aggregator", aggregator_generator_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("stress_tester", stress_tester_node)
    workflow.add_node("optimizer", optimizer_node)
    workflow.add_node("meta_reflective", meta_reflective_node)
    workflow.add_node("coder", coder_node)
    workflow.add_node("execution", execution_node)
    workflow.add_node("reporting", reporting_node)

    # Entry Point
    workflow.set_entry_point("planner")

    parallel_nodes = [
        "fundamental",
        "quantitative",
        "alternative",
        "macroeconomic",
        "sentiment",
    ]
    for node in parallel_nodes:
        workflow.add_edge("planner", node)

    for node in parallel_nodes:
        workflow.add_edge(node, "aggregator")

    # Generator to Backtest (Coder) Loop
    workflow.add_edge("aggregator", "coder")

    # Post-Coder Routing (Self-Correction or Proceed to Critic)
    workflow.add_conditional_edges(
        "coder",
        coder_routing,
        {
            "critic": "critic",  # If code executed successfully
            "coder": "coder",  # If code failed and retrying
            "reporting": "reporting",  # If code failed max retries
        },
    )

    # Critic Routing (The Core Loop)
    workflow.add_conditional_edges(
        "critic",
        critic_routing,
        {
            "stress_tester": "stress_tester",  # If Approved
            "optimizer": "optimizer",  # If Rejected
            "reporting": "reporting",  # If Max Retries Exceeded
        },
    )

    # Optimizer goes to Meta-Reflective for prompt tuning
    workflow.add_edge("optimizer", "meta_reflective")

    # Meta-Reflective returns to Aggregator
    workflow.add_edge("meta_reflective", "aggregator")

    # Stress Tester goes to Execution
    workflow.add_edge("stress_tester", "execution")
    workflow.add_edge("execution", "reporting")
    workflow.add_edge("reporting", END)

    return workflow.compile(checkpointer=checkpointer, interrupt_before=["execution"])


# Compile the app to be used elsewhere
adk_app = build_graph()
