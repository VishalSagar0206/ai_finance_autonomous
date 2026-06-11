from __future__ import annotations

from typing import Dict, Any, Iterable
import logging

from core.config import config
from core.llm_provider import llm_provider
from core.state import ADKState, DraftStrategy
from tools.alpha_memory import alpha_memory
from tools.market_data import MarketDataClient

logger = logging.getLogger(__name__)


def _as_dict(obj: Any) -> Dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return getattr(obj, "__dict__", {}) or {}


def _results_from_observation(obj: Any) -> Dict[str, Any]:
    data = _as_dict(obj)
    return data.get("results", {}) if isinstance(data, dict) else {}


def _status(item: Any) -> str | None:
    data = _as_dict(item)
    return data.get("status") if isinstance(data, dict) else None


def _insight(item: Any) -> str:
    data = _as_dict(item)
    return str(data.get("insight", "")) if isinstance(data, dict) else ""


def _normalize_allocations(scores: Dict[str, float]) -> Dict[str, float]:
    positive = {ticker: score for ticker, score in scores.items() if score > 0}
    total = sum(positive.values())
    if total <= 0:
        return {"CASH": 1.0}
    allocations = {ticker: round(score / total, 4) for ticker, score in positive.items()}
    # Correct rounding drift on the largest position.
    drift = round(1.0 - sum(allocations.values()), 4)
    if allocations and abs(drift) > 0:
        largest = max(allocations, key=allocations.get)
        allocations[largest] = round(allocations[largest] + drift, 4)
    return allocations


def _defensive_strategy(state: ADKState, reason: str) -> Dict[str, Any]:
    return {
        "draft_strategy": DraftStrategy(
            strategy_id=f"DEFENSIVE_{state.current_retry}",
            rationale=f"Insufficient agent data: {reason}. Defaulting to cash preservation.",
            parameters={"risk_mode": "extreme_defensive"},
            target_allocations={"CASH": 1.0},
        ),
        "ensemble_sub_strategies": {},
    }


def strategy_generator_agent(state: ADKState) -> Dict[str, Any]:
    """Aggregate analyst outputs into a draft strategy."""
    print(f"-> Aggregator [Retry {state.current_retry}]: Generating Strategy.")

    requested = state.request.tickers or []
    if not requested:
        print("   [Aggregator] No tickers requested. Triggering defensive fallback.")
        return _defensive_strategy(state, "no tickers were provided")

    formatted_requested = [MarketDataClient._format_ticker(t) for t in requested if t != "CASH"]
    query_text = (
        f"Asset Class: {state.request.asset_class}, Risk: {state.request.risk_tolerance}, "
        f"Tickers: {formatted_requested}"
    )
    historical_memory = alpha_memory.retrieve_similar_strategies(query_text)

    obs = state.observations
    fund_results = _results_from_observation(getattr(obs, "fundamental", None))
    quant_results = _results_from_observation(getattr(obs, "quantitative", None))
    sent_results = _results_from_observation(getattr(obs, "sentiment", None))

    successful_tickers = []
    for ticker in formatted_requested:
        if (
            _status(fund_results.get(ticker)) == "completed"
            or _status(quant_results.get(ticker)) == "completed"
            or _status(sent_results.get(ticker)) == "completed"
        ):
            successful_tickers.append(ticker)

    if not successful_tickers:
        print("   [Aggregator] No successful ticker data found. Triggering defensive fallback.")
        return _defensive_strategy(state, "no analyst returned completed market data")

    if not config.has_live_llm():
        logger.warning("Aggregator: live LLM disabled. Using deterministic generator logic.")
        ticker_scores: Dict[str, float] = {}
        conservative = "conservative" in state.request.risk_tolerance.lower() or "low" in state.request.risk_tolerance.lower()

        for ticker in successful_tickers:
            f_insight = _insight(fund_results.get(ticker)).lower()
            q_insight = _insight(quant_results.get(ticker)).lower()
            s_insight = _insight(sent_results.get(ticker)).lower()
            quant_metrics = _as_dict(_as_dict(quant_results.get(ticker)).get("metrics", {}))

            score = 2.0
            if "excellent" in f_insight or "attractive" in f_insight:
                score += 0.5
            if "strong positive" in q_insight or "bullish" in s_insight:
                score += 0.5
            if "significant negative" in q_insight:
                score = 0.0
            elif "negative" in q_insight or "bearish" in s_insight:
                score -= 3.0

            volatility = float(quant_metrics.get("volatility_std") or 0.0)
            if conservative and (ticker in {"TSLA", "NVDA"} or volatility > 0.025):
                score *= 0.5

            ticker_scores[ticker] = max(score, 0.0)

        allocations = _normalize_allocations(ticker_scores)
        if allocations == {"CASH": 1.0}:
            return _defensive_strategy(state, "signals were low conviction after conflict resolution")

        risk_mode = "conservative_defensive" if conservative else "moderate"
        memory_note = " Historical memory was checked." if historical_memory else ""
        return {
            "draft_strategy": DraftStrategy(
                strategy_id=f"ALPHA_{state.current_retry}",
                rationale=(
                    f"Deterministic {risk_mode} aggregation for {', '.join(allocations.keys())}."
                    f" Analyst signals were cross-checked across fundamentals, quant, and sentiment.{memory_note}"
                ),
                parameters={"risk_mode": risk_mode, "source": "offline_deterministic"},
                target_allocations=allocations,
            )
        }

    prompt = (
        "Synthesize the provided AgentObservations into a coherent investment strategy. "
        "Analyze Fundamental, Quantitative, and Sentiment signals to determine allocations. "
        f"HISTORICAL MEMORY (Past Strategies): {historical_memory}\n"
        "Use the memory to avoid past mistakes or double down on high-Sharpe setups. "
        "If feedback exists in feedback_loop, address it. "
        "Allocations must sum near 1.0."
    )
    try:
        llm_strategy = llm_provider.run_structured_chain(
            prompt_text=prompt,
            input_data=state.model_dump(include={"observations", "request", "feedback_loop"}),
            output_schema=DraftStrategy,
        )
        return {"draft_strategy": llm_strategy}
    except Exception as exc:
        logger.error("Aggregator: Gemini strategy generation failed. Error: %s", exc)
        return _defensive_strategy(state, "AI strategy synthesis failed")
