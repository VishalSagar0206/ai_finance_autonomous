from __future__ import annotations

from typing import Dict, Any
import logging

from core.config import config
from core.llm_provider import llm_provider
from core.state import ADKState, DraftStrategy

logger = logging.getLogger(__name__)


class EnsembleCommittee:
    """Builds style-specific strategies and a master CIO strategy."""

    @staticmethod
    def generate_style_strategy(state: ADKState, style: str) -> DraftStrategy | None:
        prompt = (
            f"You are a Senior Portfolio Manager specializing in {style} strategies. "
            "Analyze the provided AgentObservations and generate a style-specific portfolio."
        )
        try:
            return llm_provider.run_structured_chain(
                prompt_text=prompt,
                input_data=state.model_dump(include={"observations", "request"}),
                output_schema=DraftStrategy,
            )
        except Exception as exc:
            logger.error("Ensemble: %s strategy generation failed. Error: %s", style, exc)
            return None


def _clone_style(master: DraftStrategy, style: str, bias: float) -> DraftStrategy:
    allocations = dict(master.target_allocations)
    if "CASH" in allocations and len(allocations) > 1:
        # Minor deterministic style tilt without breaking total weight.
        non_cash = [t for t in allocations if t != "CASH"]
        target = non_cash[0]
        shift = min(0.05, allocations.get("CASH", 0.0)) * bias
        allocations[target] = round(allocations[target] + shift, 4)
        allocations["CASH"] = round(allocations["CASH"] - shift, 4)
    return DraftStrategy(
        strategy_id=f"{master.strategy_id}_{style.upper().replace(' ', '_')}",
        rationale=f"{style} committee view derived from the master allocation. {master.rationale}",
        parameters={**master.parameters, "committee_style": style},
        target_allocations=allocations,
    )


def ensemble_cio_agent(state: ADKState) -> Dict[str, Any]:
    """Chief Investment Officer agent for final strategy synthesis."""
    print("-> Ensemble CIO: Orchestrating the Strategy Committee.")

    if not config.has_live_llm():
        logger.warning("Ensemble: live LLM disabled. Using deterministic committee logic.")
        from agents.aggregator import strategy_generator_agent

        base = strategy_generator_agent(state)
        master = base.get("draft_strategy")
        if not master:
            return base
        sub_strategies = {
            "trend_following": _clone_style(master, "Trend Following", 1.0),
            "mean_reversion": _clone_style(master, "Mean Reversion", 0.0),
            "statistical_arbitrage": _clone_style(master, "Statistical Arbitrage", 0.0),
        }
        return {
            "draft_strategy": master,
            "ensemble_sub_strategies": sub_strategies,
        }

    styles = ["Trend Following", "Mean Reversion", "Statistical Arbitrage"]
    sub_strategies: Dict[str, DraftStrategy] = {}
    for style in styles:
        strat = EnsembleCommittee.generate_style_strategy(state, style)
        if strat:
            sub_strategies[style.replace(" ", "_").lower()] = strat

    prompt = (
        "You are the Chief Investment Officer. Synthesize the specialized strategies "
        "into one Master Strategy aligned with the macro context."
    )
    try:
        master_strategy = llm_provider.run_structured_chain(
            prompt_text=prompt,
            input_data={
                "sub_strategies": {k: v.model_dump() for k, v in sub_strategies.items()},
                "request": state.request.model_dump(),
            },
            output_schema=DraftStrategy,
        )
        return {"draft_strategy": master_strategy, "ensemble_sub_strategies": sub_strategies}
    except Exception as exc:
        logger.error("Ensemble CIO: master synthesis failed. Error: %s", exc)
        fallback = next(iter(sub_strategies.values()), None)
        return {"draft_strategy": fallback, "ensemble_sub_strategies": sub_strategies}
