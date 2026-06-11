from __future__ import annotations

from typing import Dict, Any
import logging

from pydantic import BaseModel, Field

from core.config import config
from core.llm_provider import llm_provider
from core.state import ADKState

logger = logging.getLogger(__name__)


class MetaInstructions(BaseModel):
    instructions: Dict[str, str] = Field(description="Map of agent name to new instructions.")


def meta_reflective_agent(state: ADKState) -> Dict[str, Any]:
    """Reflect on failures and update system instructions."""
    print("-> Meta-Reflective Agent: Optimizing system prompts.")

    if not state.feedback_loop:
        return {}

    if not config.has_live_llm():
        last_feedback = state.feedback_loop[-1]
        return {
            "system_instructions": {
                **(state.system_instructions or {}),
                "planner": "Prefer lower-risk universes after critic rejection.",
                "aggregator": f"Address latest critic feedback: {last_feedback}",
                "coder": "Preserve deterministic backtest output and expose error logs.",
            }
        }

    prompt = (
        "Review the current session's feedback loop and execution logs. Generate improved "
        "Meta-Instructions for Planner and Aggregator agents to prevent these issues next iteration."
    )
    try:
        llm_out = llm_provider.run_structured_chain(
            prompt_text=prompt,
            input_data={
                "feedback_loop": state.feedback_loop,
                "execution_logs": state.execution_logs,
                "current_instructions": state.system_instructions,
            },
            output_schema=MetaInstructions,
        )
        return {"system_instructions": llm_out.instructions}
    except Exception as exc:
        logger.error("Meta-Reflector: reflection failed. Error: %s", exc)
        return {}
