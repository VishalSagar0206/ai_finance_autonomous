from __future__ import annotations

from typing import Dict, Any
import logging

from core.state import ADKState

logger = logging.getLogger(__name__)


def optimizer_agent(state: ADKState) -> Dict[str, Any]:
    """Adjust strategy guidance based on critic feedback."""
    print(f"-> Optimizer: Analyzing feedback and adjusting strategy. (Retry: {state.current_retry})")
    last_feedback = state.feedback_loop[-1] if state.feedback_loop else "No specific feedback."

    adjustments: Dict[str, str] = {}
    feedback_lower = last_feedback.lower()
    if "risk" in feedback_lower or "volatile" in feedback_lower or "drawdown" in feedback_lower:
        adjustments["risk_bias"] = "DECREASED"
        print("   [Optimization] Reducing risk bias due to critic feedback.")
    if "diversification" in feedback_lower or "correlation" in feedback_lower:
        adjustments["diversification_focus"] = "INCREASED"
        print("   [Optimization] Increasing diversification focus.")

    return {
        "system_instructions": {
            "optimizer_guidance": (
                f"The critic rejected the previous draft because: {last_feedback}. "
                "Adjust allocations to be more defensive and better diversified."
            ),
            **adjustments,
        }
    }
