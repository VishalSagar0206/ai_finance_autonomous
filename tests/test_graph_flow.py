import pytest
from core.graph import adk_app
from core.state import ADKState, UserRequest, ApprovalStatus


def test_graph_execution_end_to_end():
    """Verify the entire graph compiles and executes to the reporting node."""
    initial_state = ADKState(
        request=UserRequest(
            asset_class="Equities",
            risk_tolerance="Moderate",
            time_horizon="1y",
            tickers=["AAPL"],
        )
    ).model_dump()

    # config is required by LangGraph but optional for this mock run
    config = {"configurable": {"thread_id": "test_thread_1"}}

    # Execute the graph
    # We'll just invoke it to get the final state update
    # Note: invoke returns a dict of the final state (the state after the last node)
    final_state_dict = adk_app.invoke(initial_state, config=config)

    # In LangGraph, the final_state_dict will be the accumulated state
    # We expect approval_status to be APPROVED (after 1 rejection loop)
    assert final_state_dict["approval_status"] == ApprovalStatus.APPROVED
    assert len(final_state_dict["feedback_loop"]) == 1
    assert "final_report" in final_state_dict
    assert "Success: Alpha strategy" in final_state_dict["final_report"]
