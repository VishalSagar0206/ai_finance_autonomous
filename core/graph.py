from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Iterator, Optional, Tuple
import uuid

from core.state import (
    ADKState,
    UserRequest,
    MarketContext,
    AgentObservations,
    PortfolioState,
    DiscoveredSignals,
    DraftStrategy,
    ApprovalStatus,
    merge_observations,
)

from agents.planner import planner_agent as planner_node
from agents.ensemble import ensemble_cio_agent as aggregator_generator_node
from agents.critic import multi_factor_critic_agent as critic_node
from agents.stress_tester import stress_tester_agent as stress_tester_node
from agents.meta_monitor import meta_reflective_agent as meta_reflective_node
from agents.fan_out.fundamental import fundamental_analyst_agent as fundamental_node
from agents.fan_out.quantitative import quantitative_analyst_agent as quantitative_node
from agents.fan_out.sentiment import sentiment_analyst_agent as sentiment_node
from agents.coder import coder_agent as coder_node
from agents.execution import execution_agent as execution_node
from agents.reporting import reporting_agent as reporting_node
from agents.optimizer import optimizer_agent as optimizer_node


# --- Mock nodes retained from the original graph ---
def alternative_node(state: ADKState) -> Dict[str, Any]:
    print("   -> [Parallel] Alternative Data checking satellite/foot traffic.")
    return {"observations": {"alternative": {"insight": "High retail traffic", "status": "completed"}}}


def macroeconomic_node(state: ADKState) -> Dict[str, Any]:
    print("   -> [Parallel] Macroeconomic parsing global yield curves.")
    return {"observations": {"macroeconomic": {"insight": "Fed dovish tilt", "status": "completed"}}}


# --- Conditional routing ---
def critic_routing(state: ADKState) -> str:
    if state.approval_status == ApprovalStatus.APPROVED:
        return "stress_tester"
    if state.current_retry >= state.max_retries:
        print("   [Routing] MAX RETRIES EXCEEDED. Abandoning strategy.")
        return "reporting"
    return "optimizer"


def coder_routing(state: ADKState) -> str:
    results = state.backtest_results or {}
    if results.get("status") == "success":
        return "critic"
    if state.backtest_attempts < state.max_backtest_retries:
        print(
            f"   [Routing] Backtest failed. Retrying "
            f"(Attempt {state.backtest_attempts}/{state.max_backtest_retries})."
        )
        return "coder"
    print("   [Routing] Backtest failed repeatedly. Routing to Reporting.")
    return "reporting"


@dataclass
class StateSnapshot:
    values: Dict[str, Any]
    next: Tuple[str, ...] = ()


class LocalADKApp:
    """Small graph runner compatible with the subset of LangGraph used here.

    It keeps the project runnable in offline/demo environments where LangGraph,
    PostgreSQL checkpointers, and cloud services are not installed.
    """

    def __init__(self) -> None:
        self._threads: Dict[str, tuple[ADKState, Tuple[str, ...]]] = {}

    def _thread_id(self, config: Optional[Dict[str, Any]]) -> str:
        configurable = (config or {}).get("configurable", {})
        return str(configurable.get("thread_id") or "default")

    @staticmethod
    def _coerce_state(value: Any) -> ADKState:
        if isinstance(value, ADKState):
            return value.model_copy(deep=True)
        if isinstance(value, dict):
            return ADKState.model_validate(value)
        raise TypeError("Initial graph input must be an ADKState or ADKState-compatible dict.")

    @staticmethod
    def _values(state: ADKState) -> Dict[str, Any]:
        return {name: getattr(state, name) for name in ADKState.model_fields}

    def _save(self, thread_id: str, state: ADKState, next_nodes: Tuple[str, ...] = ()) -> None:
        self._threads[thread_id] = (state.model_copy(deep=True), tuple(next_nodes))

    def get_state(self, config: Optional[Dict[str, Any]] = None) -> StateSnapshot:
        thread_id = self._thread_id(config)
        state, next_nodes = self._threads.get(
            thread_id,
            (ADKState(request=UserRequest(asset_class="Equities", risk_tolerance="Moderate", time_horizon="1y")), ()),
        )
        return StateSnapshot(values=self._values(state), next=next_nodes)

    def _apply_update(self, state: ADKState, update: Dict[str, Any]) -> None:
        for key, value in (update or {}).items():
            if key == "request":
                state.request = value if isinstance(value, UserRequest) else UserRequest.model_validate(value)
            elif key == "context":
                state.context = value if isinstance(value, MarketContext) else MarketContext.model_validate(value)
            elif key == "observations":
                state.observations = merge_observations(state.observations, value)
            elif key == "signals":
                state.signals = value if isinstance(value, DiscoveredSignals) else DiscoveredSignals.model_validate(value)
            elif key == "portfolio":
                state.portfolio = value if isinstance(value, PortfolioState) else PortfolioState.model_validate(value)
            elif key == "draft_strategy":
                if value is None:
                    state.draft_strategy = None
                else:
                    state.draft_strategy = value if isinstance(value, DraftStrategy) else DraftStrategy.model_validate(value)
            elif key == "approval_status":
                state.approval_status = value if isinstance(value, ApprovalStatus) else ApprovalStatus(value)
            elif key == "feedback_loop":
                if isinstance(value, list):
                    state.feedback_loop = list(state.feedback_loop or []) + value
                else:
                    state.feedback_loop = list(state.feedback_loop or []) + [str(value)]
            elif key == "execution_logs":
                state.execution_logs = list(value or [])
            elif key == "metrics_log":
                state.metrics_log = dict(value or {})
            elif key == "ensemble_sub_strategies":
                converted = {}
                for name, strategy in (value or {}).items():
                    converted[name] = strategy if isinstance(strategy, DraftStrategy) else DraftStrategy.model_validate(strategy)
                state.ensemble_sub_strategies = converted
            elif key == "system_instructions":
                merged = dict(state.system_instructions or {})
                merged.update(value or {})
                state.system_instructions = merged
            elif hasattr(state, key):
                setattr(state, key, value)

    def _run_node(self, state: ADKState, name: str, func) -> Dict[str, Any]:
        update = func(state)
        self._apply_update(state, update)
        return update

    def _run_analysis_until_interrupt_or_end(
        self, state: ADKState, start_node: str
    ) -> Iterator[Dict[str, Dict[str, Any]]]:
        node = start_node
        while True:
            if node == "planner":
                yield {"planner": self._run_node(state, "planner", planner_node)}
                for name, func in (
                    ("fundamental", fundamental_node),
                    ("quantitative", quantitative_node),
                    ("alternative", alternative_node),
                    ("macroeconomic", macroeconomic_node),
                    ("sentiment", sentiment_node),
                ):
                    yield {name: self._run_node(state, name, func)}
                node = "aggregator"
                continue

            if node == "aggregator":
                yield {"aggregator": self._run_node(state, "aggregator", aggregator_generator_node)}
                node = "coder"
                continue

            if node == "coder":
                yield {"coder": self._run_node(state, "coder", coder_node)}
                route = coder_routing(state)
                if route == "coder":
                    node = "coder"
                    continue
                if route == "reporting":
                    if state.approval_status != ApprovalStatus.APPROVED:
                        state.approval_status = ApprovalStatus.REJECTED
                        if not state.feedback_loop:
                            state.feedback_loop = ["Backtest failed repeatedly."]
                    node = "reporting"
                    continue
                node = "critic"
                continue

            if node == "critic":
                yield {"critic": self._run_node(state, "critic", critic_node)}
                route = critic_routing(state)
                if route == "stress_tester":
                    node = "stress_tester"
                elif route == "optimizer":
                    node = "optimizer"
                else:
                    node = "reporting"
                continue

            if node == "optimizer":
                yield {"optimizer": self._run_node(state, "optimizer", optimizer_node)}
                node = "meta_reflective"
                continue

            if node == "meta_reflective":
                yield {"meta_reflective": self._run_node(state, "meta_reflective", meta_reflective_node)}
                node = "aggregator"
                continue

            if node == "stress_tester":
                yield {"stress_tester": self._run_node(state, "stress_tester", stress_tester_node)}
                # Mimic interrupt_before=["execution"]
                return

            if node == "reporting":
                yield {"reporting": self._run_node(state, "reporting", reporting_node)}
                return

            raise RuntimeError(f"Unknown graph node: {node}")

    def _run_execution_to_end(self, state: ADKState) -> Iterator[Dict[str, Dict[str, Any]]]:
        yield {"execution": self._run_node(state, "execution", execution_node)}
        yield {"reporting": self._run_node(state, "reporting", reporting_node)}

    def stream(self, input_state: Any, config: Optional[Dict[str, Any]] = None) -> Iterator[Dict[str, Dict[str, Any]]]:
        thread_id = self._thread_id(config)
        if input_state is None:
            if thread_id not in self._threads:
                raise RuntimeError("Cannot resume graph; no checkpoint exists for this thread_id.")
            state, next_nodes = self._threads[thread_id]
            if not next_nodes:
                return
            start_node = next_nodes[0]
        else:
            state = self._coerce_state(input_state)
            start_node = "planner"

        if start_node == "execution":
            for event in self._run_execution_to_end(state):
                yield event
            self._save(thread_id, state, ())
            return

        for event in self._run_analysis_until_interrupt_or_end(state, start_node):
            yield event

        # Interrupt if the analysis reached stress_tester and approval is pending execution.
        if state.approval_status == ApprovalStatus.APPROVED and state.stress_test_report and not state.final_report:
            self._save(thread_id, state, ("execution",))
        else:
            self._save(thread_id, state, ())

    def invoke(self, input_state: Any, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        for _ in self.stream(input_state, config=config):
            pass
        return self.get_state(config).values

    async def astream(self, input_state: Any, config: Optional[Dict[str, Any]] = None):
        for event in self.stream(input_state, config=config):
            yield event


# Compiled application object used by CLI, API, UI, and tests.
adk_app = LocalADKApp()
