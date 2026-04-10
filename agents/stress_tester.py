from typing import Dict, Any, List
from core.state import ADKState
from core.llm_provider import llm_provider
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class StressTestResult(BaseModel):
    """Schema for the Stress Tester's analysis."""

    scenario_name: str
    impact_assessment: str
    estimated_drawdown: float = Field(
        description="Projected drawdown (0.0 to 1.0) under this shock."
    )
    is_resilient: bool
    recommendations: List[str]


def stress_tester_agent(state: ADKState) -> Dict[str, Any]:
    """
    Agent to simulate 'Black Swan' shocks on the proposed portfolio.
    Scenarios: 2008 GFC, 2020 COVID, 2010 Flash Crash.
    """
    print("-> Stress Tester: Simulating tail-risk scenarios.")

    if not state.draft_strategy:
        return {
            "stress_test_report": {
                "status": "error",
                "message": "No strategy to stress test.",
            }
        }

    # Gemini reasoning for non-linear risk assessment
    prompt = (
        "Analyze the following portfolio strategy against historical 'Black Swan' events: "
        "1. 2008 Financial Crisis. 2. 2020 COVID-19 Crash. 3. High Inflation/Interest Rate shock. "
        "Assess how the specific tickers and allocations would likely perform. "
        "Provide an estimated maximum drawdown and a resilience verdict."
    )

    try:
        llm_out = llm_provider.run_structured_chain(
            prompt_text=prompt,
            input_data=state.draft_strategy.model_dump(),
            output_schema=StressTestResult,
        )

        print(
            f"   [Stress Test] Scenario: {llm_out.scenario_name}. Resilient: {llm_out.is_resilient}"
        )

        return {"stress_test_report": llm_out.model_dump()}
    except Exception as e:
        logger.error(f"Stress Tester: Gemini call failed. Error: {str(e)}")
        # Default fallback
        return {
            "stress_test_report": {
                "scenario_name": "General Volatility Shock",
                "impact_assessment": "Unable to perform deep analysis. High-level caution advised.",
                "estimated_drawdown": 0.25,
                "is_resilient": False,
                "recommendations": ["Reduce leverage", "Increase cash buffer"],
            }
        }
