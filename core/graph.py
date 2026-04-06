from typing import Dict, Any
from langgraph.graph import StateGraph, END
from .state import ADKState, ApprovalStatus

from adk_framework_v3.agents.planner import planner_agent as planner_node
from adk_framework_v3.agents.ensemble import ensemble_cio_agent as aggregator_generator_node
from adk_framework_v3.agents.critic import multi_factor_critic_agent as critic_node
from adk_framework_v3.agents.stress_tester import stress_tester_agent as stress_tester_node
from adk_framework_v3.agents.meta_monitor import meta_reflective_agent as meta_reflective_node
from adk_framework_v3.agents.fan_out.fundamental import fundamental_analyst_agent as fundamental_node
from adk_framework_v3.agents.fan_out.quantitative import quantitative_analyst_agent as quantitative_node
from adk_framework_v3.agents.fan_out.sentiment import sentiment_analyst_agent as sentiment_node

from adk_framework_v3.agents.coder import coder_agent as coder_node
from adk_framework_v3.agents.execution import execution_agent as execution_node

# --- 1. Node Definitions (Remaining Mocks) ---

def alternative_node(state: ADKState) -> Dict[str, Any]:
    print("   -> [Parallel] Alternative Data checking satellite/foot traffic.")
    return {"observations": {"alternative": {"insight": "High retail traffic"}}}

def macroeconomic_node(state: ADKState) -> Dict[str, Any]:
    print("   -> [Parallel] Macroeconomic parsing global yield curves.")
    return {"observations": {"macroeconomic": {"insight": "Fed dovish tilt"}}}

def optimizer_node(state: ADKState) -> Dict[str, Any]:
    print("-> Optimizer: Adjusting allocations to be more defensive.")
    return {} # In a real scenario, this would update state with specific guidance

def reporting_node(state: ADKState) -> Dict[str, Any]:
    print("-> Reporting: Updating Transaction Ledger and final summary.")
    if state.approval_status == ApprovalStatus.REJECTED:
        return {"final_report": f"System Failure: Strategy rejected after {state.current_retry} retries. Rationale: {state.feedback_loop[-1] if state.feedback_loop else 'No feedback'}"}
    return {"final_report": f"Success: Alpha strategy {state.draft_strategy.strategy_id} executed successfully."}

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
    """Self-Correction Routing: Retries if backtest failed."""
    results = state.backtest_results or {}
    if results.get("status") == "success":
        return "execution"
    
    if state.backtest_attempts < state.max_backtest_retries:
        print(f"   [Routing] Backtest failed. Retrying (Attempt {state.backtest_attempts}/{state.max_backtest_retries}).")
        return "coder"
    
    print("   [Routing] Backtest failed repeatedly. Routing to Reporting.")
    return "reporting"

from langgraph.checkpoint.memory import MemorySaver

# --- 3. Graph Construction ---

def build_graph() -> StateGraph:
    workflow = StateGraph(ADKState)
    checkpointer = MemorySaver()

    # ... (Add Nodes logic remains the same)
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

    # ... (Parallel fan-out/in logic remains the same)
    parallel_nodes = ["fundamental", "quantitative", "alternative", "macroeconomic", "sentiment"]
    for node in parallel_nodes:
        workflow.add_edge("planner", node)

    for node in parallel_nodes:
        workflow.add_edge(node, "aggregator")

    # Generator to Critic Loop
    workflow.add_edge("aggregator", "critic")

    # Critic Routing (The Core Loop)
    workflow.add_conditional_edges(
        "critic",
        critic_routing,
        {
            "stress_tester": "stress_tester", # If Approved
            "optimizer": "optimizer",        # If Rejected
            "reporting": "reporting"         # If Max Retries Exceeded
        }
    )

    # Stress Tester goes to Coder
    workflow.add_edge("stress_tester", "coder")

    # Optimizer goes to Meta-Reflective for prompt tuning
    workflow.add_edge("optimizer", "meta_reflective")

    # Meta-Reflective returns to Aggregator
    workflow.add_edge("meta_reflective", "aggregator")

    # Post-Approval Execution Flow with Self-Correction Loop
    workflow.add_conditional_edges(
        "coder",
        coder_routing,
        {
            "execution": "execution",
            "coder": "coder",
            "reporting": "reporting"
        }
    )
    workflow.add_edge("execution", "reporting")
    workflow.add_edge("reporting", END)

    return workflow.compile(checkpointer=checkpointer, interrupt_before=["execution"])

# Compile the app to be used elsewhere
adk_app = build_graph()
