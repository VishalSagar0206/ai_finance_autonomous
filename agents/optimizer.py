from typing import Dict, Any
from core.state import ADKState
import logging

logger = logging.getLogger(__name__)

def optimizer_agent(state: ADKState) -> Dict[str, Any]:
    """
    Node implementation for the Strategy Optimizer.
    Adjusts strategy parameters based on feedback from the Risk Critic.
    """
    print(f"-> Optimizer: Analyzing feedback and adjusting strategy. (Retry: {state.current_retry})")
    
    last_feedback = state.feedback_loop[-1] if state.feedback_loop else "No specific feedback."
    
    # Simple logic: If feedback mentions 'risk' or 'volatility', reduce weights.
    # If it mentions 'diversification', add 'CASH' or check more tickers.
    
    adjustments = {}
    if "risk" in last_feedback.lower() or "volatile" in last_feedback.lower():
        adjustments["risk_bias"] = "DECREASED"
        print("   [Optimization] Reducing risk bias due to critic feedback.")
    
    if "diversification" in last_feedback.lower():
        adjustments["diversification_focus"] = "INCREASED"
        print("   [Optimization] Increasing diversification focus.")

    return {
        "current_retry": state.current_retry + 1,
        "system_instructions": {
            "optimizer_guidance": f"The critic rejected the previous draft because: {last_feedback}. Please adjust the target allocations to be more defensive."
        }
    }
