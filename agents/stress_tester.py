from __future__ import annotations

from typing import Dict, Any, List
import logging

from pydantic import BaseModel, Field

from core.config import config
from core.llm_provider import llm_provider
from core.state import ADKState

logger = logging.getLogger(__name__)


class StressTestResult(BaseModel):
    scenario_name: str
    impact_assessment: str
    estimated_drawdown: float = Field(description="Projected drawdown from 0.0 to 1.0 under this shock.")
    is_resilient: bool
    recommendations: List[str]


def _offline_stress_report(state: ADKState) -> Dict[str, Any]:
    allocations = state.draft_strategy.target_allocations if state.draft_strategy else {}
    cash_weight = float(allocations.get("CASH", 0.0))
    equity_weight = max(0.0, 1.0 - cash_weight)
    high_vol = any(ticker in {"TSLA", "NVDA"} for ticker in allocations)
    estimated_drawdown = min(0.35, 0.08 + equity_weight * (0.12 + (0.08 if high_vol else 0.0)))
    is_resilient = estimated_drawdown <= 0.25
    robustness = max(0.55, min(0.98, 1.0 - estimated_drawdown))
    return {
        "status": "success",
        "scenario_name": "Deterministic 2008/COVID/Rate Shock Composite",
        "impact_assessment": (
            "Offline stress model projects manageable drawdown under diversified allocations."
            if is_resilient
            else "Offline stress model flags elevated drawdown risk; risk buffers are recommended."
        ),
        "estimated_drawdown": round(estimated_drawdown, 4),
        "is_resilient": is_resilient,
        "robustness_score": round(robustness, 4),
        "recommendations": ["Maintain stop-loss discipline", "Keep cash buffer", "Rebalance after volatility spikes"],
    }


def stress_tester_agent(state: ADKState) -> Dict[str, Any]:
    """Simulate tail-risk scenarios for the proposed portfolio."""
    print("-> Stress Tester: Simulating tail-risk scenarios.")

    if not state.draft_strategy:
        return {"stress_test_report": {"status": "error", "message": "No strategy to stress test."}}

    if not config.has_live_llm():
        return {"stress_test_report": _offline_stress_report(state)}

    prompt = (
        "Analyze the portfolio strategy against historical Black Swan events: "
        "2008 Financial Crisis, 2020 COVID-19 Crash, and high inflation/rate shock. "
        "Provide an estimated maximum drawdown and resilience verdict."
    )
    try:
        llm_out = llm_provider.run_structured_chain(
            prompt_text=prompt,
            input_data=state.draft_strategy.model_dump(),
            output_schema=StressTestResult,
        )
        result = llm_out.model_dump()
        result.setdefault("status", "success")
        result.setdefault("robustness_score", max(0.0, 1.0 - float(result.get("estimated_drawdown", 0.25))))
        print(f"   [Stress Test] Scenario: {llm_out.scenario_name}. Resilient: {llm_out.is_resilient}")
        return {"stress_test_report": result}
    except Exception as exc:
        logger.error("Stress Tester: Gemini call failed. Error: %s", exc)
        return {"stress_test_report": _offline_stress_report(state)}
