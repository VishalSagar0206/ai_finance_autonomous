from typing import Dict, Any, List
from core.state import ADKState, DraftStrategy
from core.llm_provider import llm_provider
import logging
import os

logger = logging.getLogger(__name__)


class EnsembleCommittee:
    """
    Orchestrates multiple investment styles (Trend, Mean-Reversion, Arb)
    and synthesizes them into a single high-conviction portfolio.
    """

    @staticmethod
    def generate_style_strategy(state: ADKState, style: str) -> DraftStrategy:
        """Generates a strategy focused on a specific investment style."""
        prompt = (
            f"You are a Senior Portfolio Manager specializing in {style} strategies. "
            "Analyze the provided AgentObservations and generate a style-specific portfolio. "
            "Ensure the target_allocations reflect your specialized style."
        )
        try:
            return llm_provider.run_structured_chain(
                prompt_text=prompt,
                input_data=state.model_dump(include={"observations", "request"}),
                output_schema=DraftStrategy,
            )
        except Exception as e:
            logger.error(
                f"Ensemble: {style} strategy generation failed. Error: {str(e)}"
            )
            return None


def ensemble_cio_agent(state: ADKState) -> Dict[str, Any]:
    """
    The 'Chief Investment Officer' Agent.
    Orchestrates parallel styles and builds an ensemble strategy.
    """
    print("-> Ensemble CIO: Orchestrating the Strategy Committee.")

    if not os.environ.get("GOOGLE_API_KEY"):
        logger.warning("Ensemble: No API Key. Falling back to simple aggregation.")
        from agents.aggregator import strategy_generator_agent

        return strategy_generator_agent(state)

    # 1. Parallel Generation (Simulated here for simplicity, real LangGraph would fan-out)
    styles = ["Trend Following", "Mean Reversion", "Statistical Arbitrage"]
    sub_strategies = {}

    for style in styles:
        strat = EnsembleCommittee.generate_style_strategy(state, style)
        if strat:
            sub_strategies[style.replace(" ", "_").lower()] = strat

    # 2. CIO Synthesis
    prompt = (
        "You are the Chief Investment Officer. You have received three specialized strategies from your team. "
        "Synthesize these into a single Master Strategy. "
        "Weigh the strategies based on their logical consistency and alignment with the Macro Context."
    )

    try:
        master_strategy = llm_provider.run_structured_chain(
            prompt_text=prompt,
            input_data={
                "sub_strategies": {
                    k: v.model_dump() for k, v in sub_strategies.items()
                },
                "request": state.request.model_dump(),
            },
            output_schema=DraftStrategy,
        )
        return {
            "draft_strategy": master_strategy,
            "ensemble_sub_strategies": sub_strategies,
        }
    except Exception as e:
        logger.error(f"Ensemble CIO: Master synthesis failed. Error: {str(e)}")
        # Fallback to the first available sub-strategy or cash
        fallback = list(sub_strategies.values())[0] if sub_strategies else None
        return {"draft_strategy": fallback}
