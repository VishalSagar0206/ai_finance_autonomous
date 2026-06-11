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
    # It will stop at the 'execution' interrupt
    final_state_dict = adk_app.invoke(initial_state, config=config)

    # Verify it reached the interrupt
    assert final_state_dict["approval_status"] == ApprovalStatus.APPROVED
    
    # Resume the graph (passing None to input to continue from checkpoint)
    final_state_dict = adk_app.invoke(None, config=config)

    # Now it should be at the end
    assert "final_report" in final_state_dict
    assert final_state_dict["final_report"] is not None
    assert "Success: Alpha strategy" in final_state_dict["final_report"]
