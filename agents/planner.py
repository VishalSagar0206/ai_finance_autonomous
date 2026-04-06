from typing import Dict, Any, List
from adk_framework_v3.core.state import ADKState
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

class PlannerOutput(BaseModel):
    """Schema for the Planner's structured output."""
    extracted_tickers: List[str] = Field(description="Ticker symbols extracted from request.")
    tasks: List[str] = Field(description="Step-by-step goal decomposition.")
    risk_profile_adjustment: str = Field(description="Determined risk profile (e.g., 'Conservative').")

from adk_framework_v3.core.llm_provider import llm_provider
import os

def planner_agent(state: ADKState) -> Dict[str, Any]:
    """
    LLM-powered Planner Node using Gemini.
    Decomposes the natural language UserRequest into actionable H-SSS updates.
    """
    print(f"-> Planner: Orchestrating strategy for {state.request.asset_class}.")
    
    # 1. Check for API Key to determine if we use real Gemini or Mock
    if not os.environ.get("GOOGLE_API_KEY"):
        logger.warning("Planner: No API Key found. Falling back to mock planner logic.")
        req = state.request
        tasks = [
            f"Analyze fundamental health for {', '.join(req.tickers)}.",
            f"Generate {req.risk_tolerance}-aware quantitative alpha signals.",
            "Synthesize results into a cohesive strategy draft."
        ]
        return {
            "request": req.model_dump(),
            "plan": tasks
        }

    # 2. Real Gemini Call
    prompt = "Decompose this financial request into a list of tasks for specialized agents. Extract any tickers mentioned."
    try:
        llm_out = llm_provider.run_structured_chain(
            prompt_text=prompt,
            input_data=state.request.model_dump(),
            output_schema=PlannerOutput
        )
        
        return {
            "request": {
                "asset_class": state.request.asset_class,
                "risk_tolerance": llm_out.risk_profile_adjustment or state.request.risk_tolerance,
                "time_horizon": state.request.time_horizon,
                "tickers": llm_out.extracted_tickers or state.request.tickers,
                "additional_constraints": state.request.additional_constraints
            },
            "plan": llm_out.tasks
        }
    except Exception as e:
        logger.error(f"Planner: Gemini call failed. Falling back. Error: {str(e)}")
        return {"plan": ["Fallback: Analyze provided tickers manually."]}
