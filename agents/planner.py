from typing import Dict, Any, List
from core.state import ADKState
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class PlannerOutput(BaseModel):
    """Schema for the Planner's structured output."""

    extracted_tickers: List[str] = Field(
        description="Ticker symbols extracted from request."
    )
    tasks: List[str] = Field(description="Step-by-step goal decomposition.")
    risk_profile_adjustment: str = Field(
        description="Determined risk profile (e.g., 'Conservative')."
    )
    investor_focus: str = Field(
        description="The primary analytical focus based on investor type (e.g. 'Volatility/Sentiment' for Intraday)."
    )


from core.llm_provider import llm_provider
import os

from tools.compliance_engine import compliance_engine


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
        
        # Customize tasks based on investor type
        if req.investor_type == "INTRADAY":
            tasks = [
                f"Analyze high-frequency sentiment and volatility for {', '.join(safe_tickers)}.",
                "Identify intraday momentum signals and support/resistance levels.",
                "Construct a high-turnover strategy with tight stop-losses."
            ]
        elif req.investor_type == "SHORT_TERM":
            tasks = [
                f"Analyze technical indicators and recent news for {', '.join(safe_tickers)}.",
                "Check for upcoming earnings or macro catalysts.",
                "Draft a swing-trading strategy focusing on 1-4 week price targets."
            ]
        else: # LONG_TERM
            tasks = [
                f"Analyze fundamental health and industry position for {', '.join(safe_tickers)}.",
                f"Generate {req.risk_tolerance}-aware quantitative alpha signals.",
                "Synthesize results into a long-term value-driven strategy draft.",
            ]
            
        return {
            "request": {
                "asset_class": req.asset_class,
                "risk_tolerance": req.risk_tolerance,
                "time_horizon": req.time_horizon,
                "investor_type": req.investor_type,
                "tickers": safe_tickers,
                "additional_constraints": req.additional_constraints,
            },
            "plan": tasks,
        }

    # 2. Real Gemini Call
    prompt = f"Decompose this financial request for a {state.request.investor_type} investor into specialized tasks. Focus on indicators relevant to the {state.request.investor_type} horizon. Extract compliant tickers."
    try:
        # Use a wrapper for structured chain to ensure event loop if needed
        llm_out = llm_provider.run_structured_chain(
            prompt_text=prompt,
            input_data={
                "request": state.request.model_dump(),
                "compliant_tickers": safe_tickers,
                "investor_type": state.request.investor_type
            },
            output_schema=PlannerOutput,
        )

        # Ensure we only use compliant tickers
        final_tickers = [t for t in (llm_out.extracted_tickers or safe_tickers) if t in safe_tickers]

        return {
            "request": {
                "asset_class": state.request.asset_class,
                "risk_tolerance": llm_out.risk_profile_adjustment
                or state.request.risk_tolerance,
                "time_horizon": state.request.time_horizon,
                "investor_type": state.request.investor_type,
                "tickers": final_tickers,
                "additional_constraints": state.request.additional_constraints,
            },
            "plan": llm_out.tasks,
        }
    except Exception as e:
        logger.error(f"Planner: Gemini call failed. Falling back. Error: {str(e)}")
        return {"plan": ["Fallback: Analyze provided tickers manually."]}
