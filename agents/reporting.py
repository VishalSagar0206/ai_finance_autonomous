from __future__ import annotations

from typing import Dict, Any
import logging

from core.state import ADKState, ApprovalStatus
from tools.market_data import market_data_client

logger = logging.getLogger(__name__)


class ReportingAgent:
    """Final reporting node for strategy quality and allocation analysis."""

    @staticmethod
    def calculate_evaluation_metric(state: ADKState) -> Dict[str, Any]:
        score = 0
        factors: Dict[str, str] = {}

        if state.backtest_results and state.backtest_results.get("status") == "success":
            sharpe = float(state.backtest_results.get("sharpe_ratio", 0.0) or 0.0)
            perf_score = min(40, 25 + int(max(0.0, sharpe) * 8))
            factors["backtest"] = f"Successful simulation with Sharpe {sharpe:.2f}."
            score += perf_score
        else:
            factors["backtest"] = "No valid backtest results found."

        if state.stress_test_report and state.stress_test_report.get("status") == "success":
            robustness = float(state.stress_test_report.get("robustness_score", 0.7) or 0.7)
            factors["risk"] = f"Strategy passed stress testing with {robustness * 100:.1f}% robustness."
            score += int(robustness * 30)
        else:
            factors["risk"] = "Risk assessment incomplete or failed."

        if state.approval_status == ApprovalStatus.APPROVED:
            score += 30
            factors["compliance"] = "Passed all institutional compliance gates."
        else:
            factors["compliance"] = "Did not pass compliance/risk approval."

        return {
            "total_score": min(score, 100),
            "breakdown": factors,
            "label": "High Quality" if score > 80 else "Moderate" if score > 50 else "Low Quality/High Risk",
        }

    @staticmethod
    def get_sector_allocation(state: ADKState) -> Dict[str, Any]:
        if not state.draft_strategy:
            return {"sector_breakdown": {}, "stock_percentage": 0.0}

        allocations = state.draft_strategy.target_allocations
        sector_weights: Dict[str, float] = {}
        print("-> Reporting: Generating Mutual Fund Sector Allocation...")

        for ticker, weight in allocations.items():
            if ticker == "CASH":
                sector_weights["Cash & Equivalents"] = sector_weights.get("Cash & Equivalents", 0.0) + float(weight)
                continue
            info = market_data_client.get_ticker_info(ticker)
            sector = info.get("sector") or "Other/Unknown"
            sector_weights[sector] = sector_weights.get(sector, 0.0) + float(weight)

        sorted_sectors = dict(sorted(sector_weights.items(), key=lambda item: item[1], reverse=True))
        stock_percentage = 100.0 - (sector_weights.get("Cash & Equivalents", 0.0) * 100.0)
        return {"sector_breakdown": sorted_sectors, "stock_percentage": stock_percentage}

    @classmethod
    def generate_report(cls, state: ADKState) -> Dict[str, Any]:
        print(
            f"-> Reporting: Finalizing report for strategy "
            f"{state.draft_strategy.strategy_id if state.draft_strategy else 'N/A'}"
        )

        if state.approval_status == ApprovalStatus.REJECTED:
            return {
                "final_report": (
                    f"System Failure: Strategy rejected after {state.current_retry} retries. "
                    f"Rationale: {state.feedback_loop[-1] if state.feedback_loop else 'No feedback'}"
                ),
                "execution_logs": state.execution_logs or [],
                "backtest_results": state.backtest_results or {},
                "metrics_log": {"execution_logs": state.execution_logs or []},
            }

        eval_metric = cls.calculate_evaluation_metric(state)
        sector_alloc = cls.get_sector_allocation(state)
        strategy_id = state.draft_strategy.strategy_id if state.draft_strategy else "N/A"
        rationale = state.draft_strategy.rationale if state.draft_strategy else "No strategy generated."

        report = f"""
# Institutional Investment Report
Success: Alpha strategy completed all configured agent stages.

**Strategy ID:** {strategy_id}
**Investor Profile:** {state.request.investor_type.value}

## 1. Evaluation Metric
**Overall Score: {eval_metric['total_score']}/100 ({eval_metric['label']})**
- **Backtest:** {eval_metric['breakdown'].get('backtest')}
- **Risk/Stress:** {eval_metric['breakdown'].get('risk')}
- **Compliance:** {eval_metric['breakdown'].get('compliance')}

## 2. Portfolio Allocation (Sector View)
**Stock Allocation:** {sector_alloc.get('stock_percentage', 0):.2f}%
**Cash Allocation:** {100 - sector_alloc.get('stock_percentage', 0):.2f}%

### Sector Breakdown:
"""
        for sector, weight in sector_alloc.get("sector_breakdown", {}).items():
            report += f"- {sector}: {weight * 100:.2f}%\n"

        report += f"\n## 3. Executive Summary\n{rationale}\n"

        return {
            "final_report": report,
            "metrics_log": {
                "evaluation_score": eval_metric["total_score"],
                "sector_allocation": sector_alloc.get("sector_breakdown", {}),
                "execution_logs": state.execution_logs or [],
            },
            "execution_logs": state.execution_logs or [],
            "backtest_results": state.backtest_results or {},
        }


def reporting_agent(state: ADKState) -> Dict[str, Any]:
    return ReportingAgent.generate_report(state)
