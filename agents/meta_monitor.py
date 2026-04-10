from typing import Dict, Any
from core.state import ADKState
from core.llm_provider import llm_provider
import logging
import os

logger = logging.getLogger(__name__)


def meta_reflective_agent(state: ADKState) -> Dict[str, Any]:
    """
    Agent that reflects on the current session's failures and successes.
    Updates 'system_instructions' to improve future agent performance.
    """
    print("-> Meta-Reflective Agent: Optimizing system prompts.")

    if not os.environ.get("GOOGLE_API_KEY") or not state.feedback_loop:
        return {}

    prompt = (
        "You are a Meta-Optimization Agent. Review the current session's feedback loop and execution logs. "
        "Generate a set of improved 'Meta-Instructions' for the Planner and Aggregator agents to prevent "
        "these issues in the next iteration."
    )

    try:
        # We use a simple JSON output here for instructions
        llm_out = llm_provider.run_structured_chain(
            prompt_text=prompt,
            input_data={
                "feedback_loop": state.feedback_loop,
                "execution_logs": state.execution_logs,
                "current_instructions": state.system_instructions,
            },
            output_schema=Dict[str, str],  # Schema for instruction map
        )

        return {"system_instructions": llm_out}
    except Exception as e:
        logger.error(f"Meta-Reflector: Reflection failed. Error: {str(e)}")
        return {}
