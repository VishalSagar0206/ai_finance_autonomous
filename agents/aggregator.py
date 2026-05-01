from typing import Dict, Any
from core.state import ADKState, DraftStrategy
from core.llm_provider import llm_provider
import os
import logging

logger = logging.getLogger(__name__)

from tools.alpha_memory import alpha_memory


def strategy_generator_agent(state: ADKState) -> Dict[str, Any]:
    """
    LLM-powered Data Aggregator & Strategy Generator using Gemini and Alpha Memory.
    Synthesizes AgentObservations and Historical Memory from H-SSS into a coherent DraftStrategy.
    """
    print(f"-> Aggregator [Retry {state.current_retry}]: Generating Strategy.")

    # 1. Check for empty ticker list first - proactive defensive fallback
    tickers = state.request.tickers
    if not tickers:
        print("   [Aggregator] No tickers requested. Triggering defensive fallback.")
        return {
            "draft_strategy": DraftStrategy(
                strategy_id=f"DEFENSIVE_{state.current_retry}",
                rationale="No tickers provided in the request. Defaulting to Cash preserve.",
                parameters={"risk_mode": "extreme_defensive"},
                target_allocations={"CASH": 1.0},
            )
        }

    # 2. Query Alpha Memory for long-term learning
    query_text = f"Asset Class: {state.request.asset_class}, Risk: {state.request.risk_tolerance}, Tickers: {state.request.tickers}"
    historical_memory = alpha_memory.retrieve_similar_strategies(query_text)

    # 3. Check for successful ticker data before proceeding
    obs = state.observations

    def get_results(obj):
        if not obj: return {}
        if hasattr(obj, "results"): return obj.results
        if isinstance(obj, dict): return obj.get("results", {})
        return {}

    fund_results = get_results(obs.fundamental)
    quant_results = get_results(obs.quantitative)
    sent_results = get_results(obs.sentiment)

    def get_status(res):
        if isinstance(res, dict): return res.get("status")
        return getattr(res, "status", None)

    # A ticker is successful if any analyst completed it
    successful_tickers = [
        t for t in tickers if (
            get_status(fund_results.get(t)) == "completed" or 
            get_status(quant_results.get(t)) == "completed" or
            get_status(sent_results.get(t)) == "completed"
        )
    ]

    if not successful_tickers:
        print("   [Aggregator] No successful ticker data found. Triggering defensive fallback.")
        return {
            "draft_strategy": DraftStrategy(
                strategy_id=f"DEFENSIVE_{state.current_retry}",
                rationale="No valid market data retrieved for requested assets. Defaulting to Cash preserve.",
                parameters={"risk_mode": "extreme_defensive"},
                target_allocations={"CASH": 1.0},
            )
        }

    # 4. Path A: Mock Fallback (No API Key)
    if not os.environ.get("GOOGLE_API_KEY"):
        logger.warning("Aggregator: No API Key. Falling back to mock generator logic.")
        
        # Conflict Resolution in Mock
        ticker_scores = {}
        total_score = 0
        for t in successful_tickers:
            f_insight = fund_results.get(t, {}).get("insight", "").lower() if isinstance(fund_results.get(t), dict) else ""
            q_insight = quant_results.get(t, {}).get("insight", "").lower() if isinstance(quant_results.get(t), dict) else ""
            
            score = 2
            if "negative" in q_insight:
                score -= 2
            if score <= 1.1:
                ticker_scores[t] = 0
            else:
                ticker_scores[t] = score
                total_score += score

        if total_score == 0:
            return {
                "draft_strategy": DraftStrategy(
                    strategy_id=f"DEFENSIVE_{state.current_retry}",
                    rationale="Insufficient high-conviction signals. Falling back to cash.",
                    parameters={"risk_mode": "extreme_defensive"},
                    target_allocations={"CASH": 1.0},
                )
            }

        alloc = {t: round(s / total_score, 2) for t, s in ticker_scores.items() if s > 0}
        return {
            "draft_strategy": DraftStrategy(
                strategy_id=f"ALPHA_{state.current_retry}",
                rationale=f"Mock Fallback for {', '.join([t for t, s in ticker_scores.items() if s > 0])}.",
                parameters={"risk_mode": "moderate"},
                target_allocations=alloc,
            )
        }

    # 5. Path B: Real Gemini Call for Strategy Synthesis
    prompt = (
        "Synthesize the provided AgentObservations into a coherent investment strategy. "
        "Analyze Fundamental, Quantitative, and Sentiment signals to determine the best allocations. "
        f"HISTORICAL MEMORY (Past Strategies): {historical_memory}\n"
        "Use the memory to avoid past mistakes or double down on high-Sharpe setups. "
        "If feedback exists in 'feedback_loop', you MUST address it. "
        "The rationale must be professional and data-driven. "
        "The target_allocations must be a dictionary where keys are tickers (or 'CASH') and values are floats summing near 1.0."
    )
    try:
        # We pass the state as the primary input data for the LLM
        llm_strategy = llm_provider.run_structured_chain(
            prompt_text=prompt,
            input_data=state.model_dump(include={"observations", "request", "feedback_loop"}),
            output_schema=DraftStrategy,
        )
        return {"draft_strategy": llm_strategy}
    except Exception as e:
        logger.error(f"Aggregator: Gemini strategy generation failed. Error: {str(e)}")
        # Simple defensive fallback if the AI fails
        return {
            "draft_strategy": DraftStrategy(
                strategy_id="FALLBACK_EMERGENCY",
                rationale="System Error in AI strategy synthesis. Defaulting to Cash.",
                parameters={"risk_mode": "extreme_defensive"},
                target_allocations={"CASH": 1.0},
            )
        }
