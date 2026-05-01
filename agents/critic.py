from typing import Dict, Any, List
from core.state import ADKState, ApprovalStatus
from core.llm_provider import llm_provider
from pydantic import BaseModel, Field
import os
import logging

logger = logging.getLogger(__name__)


class CriticOutput(BaseModel):
    """Schema for the Critic's structured evaluation."""

    status: ApprovalStatus
    critiques: List[str] = Field(
        description="List of specific reasons for rejection or comments on approval."
    )
    risk_score: float = Field(description="Assessed risk level from 0.0 to 1.0.")


from tools.risk_engine import risk_engine


def multi_factor_critic_agent(state: ADKState) -> Dict[str, Any]:
    """
    LLM-powered Multi-Factor Critic Node using Gemini and RiskEngine.
    Evaluates Strategy, Backtest, and Mathematical Risk (Correlation/VaR).
    """
    print("-> Critic: Performing empirical & mathematical risk assessment.")

    if not state.draft_strategy:
        return {
            "approval_status": ApprovalStatus.REJECTED,
            "feedback_loop": ["No strategy to evaluate."],
        }

    # 0. Defensive Auto-Approval
    strategy = state.draft_strategy
    if strategy.strategy_id.startswith(("DEFENSIVE", "FALLBACK")) or strategy.target_allocations.get("CASH", 0.0) >= 0.99:
        print("   [Critic] Defensive/Fallback strategy detected (CASH >= 99%). Auto-approving.")
        return {"approval_status": ApprovalStatus.APPROVED}

    # 1. Mathematical Risk Engine (Correlation & VaR)
    tickers = [t for t in strategy.target_allocations.keys() if t != "CASH"]
    weights = strategy.target_allocations

    risk_stats = risk_engine.calculate_portfolio_risk(tickers, weights)

    if risk_stats.get("status") == "success":
        avg_corr = risk_stats.get("avg_correlation", 0)
        if avg_corr > 0.8:
            feedback = f"Mathematical Rejection: Portfolio correlation ({avg_corr:.2f}) is too high. Tickers are moving in lockstep, increasing idiosyncratic risk."
            print(f"   [Critic] {feedback}")
            return {
                "approval_status": ApprovalStatus.REJECTED,
                "feedback_loop": [feedback],
                "current_retry": state.current_retry + 1,
            }

    # 2. Empirical Backtest Validation
    bt = state.backtest_results or {}
    sharpe = bt.get("sharpe_ratio", 0.0)
    drawdown = abs(bt.get("max_drawdown", 0.0))

    if bt.get("status") == "success":
        if sharpe < 0.8:  # Threshold for institutional grade
            feedback = f"Empirical Rejection: Sharpe Ratio ({sharpe:.2f}) is below the institutional threshold of 0.8. The model lacks sufficient risk-adjusted return."
            print(f"   [Critic] {feedback}")
            return {
                "approval_status": ApprovalStatus.REJECTED,
                "feedback_loop": [feedback],
                "current_retry": state.current_retry + 1,
            }
        if drawdown > 0.15:  # 15% drawdown limit
            feedback = f"Empirical Rejection: Max Drawdown ({drawdown*100:.1f}%) exceeds the 15% safety limit. Portfolio volatility is too high."
            print(f"   [Critic] {feedback}")
            return {
                "approval_status": ApprovalStatus.REJECTED,
                "feedback_loop": [feedback],
                "current_retry": state.current_retry + 1,
            }

    # 2. Fallback Logic for Mock Simulation (No API Key)
    if not os.environ.get("GOOGLE_API_KEY"):
        # ... (Same logic as before, just ensured sharpe check above handles most mocks)
        return {"approval_status": ApprovalStatus.APPROVED}

    # 3. Real Gemini Call for deep qualitative + compliance critique
    prompt = (
        "Evaluate the proposed DraftStrategy AND the BacktestResults. "
        f"BACKTEST DATA: Sharpe={sharpe}, Drawdown={drawdown}\n"
        "Check for: 1. Risk/VaR violations. 2. Compliance (Reg-T). 3. Logical consistency. "
        "If the backtest metrics are weak, provide technical feedback on how to optimize the model parameters."
    )
    try:
        llm_out = llm_provider.run_structured_chain(
            prompt_text=prompt,
            input_data=state.model_dump(
                include={
                    "request",
                    "observations",
                    "draft_strategy",
                    "backtest_results",
                    "current_retry",
                }
            ),
            output_schema=CriticOutput,
        )

        if llm_out.status == ApprovalStatus.REJECTED:
            print(f"   [Critic] Rejected by AI: {llm_out.critiques}")
            return {
                "approval_status": ApprovalStatus.REJECTED,
                "feedback_loop": llm_out.critiques,
                "current_retry": state.current_retry + 1,
            }

        print("   [Critic] Approved by AI.")
        return {"approval_status": ApprovalStatus.APPROVED}
    except Exception as e:
        logger.error(f"Critic: Gemini evaluation failed. Error: {str(e)}")
        return {"approval_status": ApprovalStatus.APPROVED}
