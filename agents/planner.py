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

from adk_framework_v3.tools.compliance_engine import compliance_engine

def planner_agent(state: ADKState) -> Dict[str, Any]:
    """
    LLM-powered Planner Node with Institutional Compliance Pre-Check.
    """
    print(f"-> Planner: Orchestrating strategy for {state.request.asset_class}.")
    
    # 1. Institutional Compliance Pre-Check
    initial_tickers = state.request.tickers or ["AAPL"]
    compliance_results = compliance_engine.check_ticker_compliance(initial_tickers)
    
    safe_tickers = compliance_results["approved_tickers"]
    rejected_tickers = compliance_results["rejected_tickers"]

    if rejected_tickers:
        print(f"   [Compliance] BLOCKED restricted assets: {rejected_tickers}")

    # 2. Check for API Key for Gemini Planning
    if not os.environ.get("GOOGLE_API_KEY"):
        logger.warning("Planner: No API Key found. Falling back to mock planner logic.")
        req = state.request
        tasks = [
            f"Analyze fundamental health for {', '.join(safe_tickers)}.",
            f"Generate {req.risk_tolerance}-aware quantitative alpha signals.",
            "Synthesize results into a cohesive strategy draft."
        ]
        return {
            "request": {
                "asset_class": req.asset_class,
                "risk_tolerance": req.risk_tolerance,
                "time_horizon": req.time_horizon,
                "tickers": safe_tickers,
                "additional_constraints": req.additional_constraints
            },
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
