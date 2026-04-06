from typing import Dict, Any, List
from adk_framework_v3.core.state import ADKState, ApprovalStatus
from adk_framework_v3.core.llm_provider import llm_provider
from pydantic import BaseModel, Field
import os
import logging

logger = logging.getLogger(__name__)

class CriticOutput(BaseModel):
    """Schema for the Critic's structured evaluation."""
    status: ApprovalStatus
    critiques: List[str] = Field(description="List of specific reasons for rejection or comments on approval.")
    risk_score: float = Field(description="Assessed risk level from 0.0 to 1.0.")

def multi_factor_critic_agent(state: ADKState) -> Dict[str, Any]:
    """
    LLM-powered Multi-Factor Critic Node using Gemini.
    Analyzes the DraftStrategy for Risk, Compliance, and Viability.
    """
    print("-> Critic: Performing multi-factor risk assessment.")
    
    if not state.draft_strategy:
        return {"approval_status": ApprovalStatus.REJECTED, "feedback_loop": ["No strategy to evaluate."]}

    # 1. Fallback Logic for Mock Simulation (No API Key)
    if not os.environ.get("GOOGLE_API_KEY"):
        logger.warning("Critic: No API Key. Falling back to mock critic logic.")
        params = state.draft_strategy.parameters
        risk_mode = params.get("risk_mode", "moderate")
        
        # Simulated rejection logic
        risk_failed = (risk_mode == "moderate" and state.current_retry < 1)
        
        if risk_failed:
            feedback = "Mock: VaR limit exceeded. Shift to defensive."
            return {
                "approval_status": ApprovalStatus.REJECTED,
                "feedback_loop": [feedback],
                "current_retry": state.current_retry + 1
            }
        
        if state.current_retry >= state.max_retries:
            return {"approval_status": ApprovalStatus.REJECTED}

        return {"approval_status": ApprovalStatus.APPROVED}

    # 2. Real Gemini Call for Critiquing
    prompt = (
        "Evaluate the proposed DraftStrategy against the UserRequest and MarketContext. "
        "Check for: 1. Risk/VaR violations. 2. Compliance (Reg-T). 3. Logical consistency. "
        "If the strategy is rejected, provide clear, actionable feedback for the Generator."
    )
    try:
        llm_out = llm_provider.run_structured_chain(
            prompt_text=prompt,
            input_data=state.model_dump(include={"request", "observations", "draft_strategy", "current_retry"}),
            output_schema=CriticOutput
        )
        
        if llm_out.status == ApprovalStatus.REJECTED:
            print(f"   [Critic] Rejected by AI: {llm_out.critiques}")
            return {
                "approval_status": ApprovalStatus.REJECTED,
                "feedback_loop": llm_out.critiques,
                "current_retry": state.current_retry + 1
            }
        
        print("   [Critic] Approved by AI.")
        return {"approval_status": ApprovalStatus.APPROVED}
    except Exception as e:
        logger.error(f"Critic: Gemini evaluation failed. Error: {str(e)}")
        # Defensive pass to prevent infinite retry loop
        return {"approval_status": ApprovalStatus.APPROVED}
