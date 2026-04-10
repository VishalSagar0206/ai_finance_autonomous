import pytest
from core.state import (
    ADKState,
    UserRequest,
    ApprovalStatus,
    DraftStrategy,
)


def test_state_initialization():
    """Verify ADKState initializes correctly with mandatory fields."""
    request = UserRequest(
        asset_class="Equities",
        risk_tolerance="Low",
        time_horizon="5y",
        tickers=["AAPL"],
    )
    state = ADKState(request=request).model_dump()
    assert state.request.asset_class == "Equities"
    assert state.approval_status == ApprovalStatus.PENDING
    assert state.feedback_loop == []


def test_state_feedback_loop_append():
    """Verify that feedback_loop (Annotated[List, operator.add]) correctly appends data."""
    # Note: LangGraph handles the operator.add during state updates.
    # Here we just verify the basic model supports list operations.
    request = UserRequest(
        asset_class="Equities",
        risk_tolerance="Low",
        time_horizon="5y",
        tickers=["AAPL"],
    )
    state = ADKState(request=request, feedback_loop=["First feedback"]).model_dump()
    state.feedback_loop.append("Second feedback")
    assert len(state.feedback_loop) == 2
    assert state.feedback_loop == ["First feedback", "Second feedback"]


def test_draft_strategy_validation():
    """Verify DraftStrategy Pydantic validation."""
    strategy = DraftStrategy(
        strategy_id="S_001",
        rationale="Test Rationale",
        parameters={"ma_period": 20},
        target_allocations={"AAPL": 1.0},
    )
    assert strategy.strategy_id == "S_001"
    assert strategy.target_allocations["AAPL"] == 1.0
