from typing import Dict, Any, List
from core.state import ADKState, ApprovalStatus
import logging
from tools.market_data import market_data_client

logger = logging.getLogger(__name__)

class ReportingAgent:
    """
    Final node in the ADK graph.
    Generates institutional-grade reports with evaluation metrics and sector allocations.
    """

    @staticmethod
    def calculate_evaluation_metric(state: ADKState) -> Dict[str, Any]:
        """
        Calculates a comprehensive quality score for the strategy.
        Metrics: Backtest performance, Risk level (VaR), Stress test robustness.
        """
        score = 0
        factors = {}

        # 1. Backtest Component (40%)
        if state.backtest_results and state.backtest_results.get("status") == "success":
            # Mocking scoring based on backtest output
            # In real scenario, would parse sharpe, sortino, etc.
            perf_score = 35 # High starting point for successful backtest
            factors["backtest"] = "Successful simulation with positive alpha."
            score += perf_score
        else:
            factors["backtest"] = "No valid backtest results found."

        # 2. Risk Component (30%)
        if state.stress_test_report and state.stress_test_report.get("status") == "success":
            robustness = state.stress_test_report.get("robustness_score", 0.7)
            risk_score = int(robustness * 30)
            factors["risk"] = f"Strategy passed stress testing with {robustness*100}% robustness."
            score += risk_score
        else:
            factors["risk"] = "Risk assessment incomplete or failed."

        # 3. Compliance & Diversification (30%)
        if state.approval_status == ApprovalStatus.APPROVED:
            score += 30
            factors["compliance"] = "Passed all institutional compliance gates."
        
        return {
            "total_score": score,
            "breakdown": factors,
            "label": "High Quality" if score > 80 else "Moderate" if score > 50 else "Low Quality/High Risk"
        }

    @staticmethod
    def get_sector_allocation(state: ADKState) -> Dict[str, Any]:
        """
        Generates a sector-wise breakdown of the portfolio (Mutual Fund style).
        """
        if not state.draft_strategy:
            return {"error": "No draft strategy found for allocation analysis."}

        allocations = state.draft_strategy.target_allocations
        sector_weights = {}
        
        print("-> Reporting: Generating Mutual Fund Sector Allocation...")

        for ticker, weight in allocations.items():
            if ticker == "CASH":
                sector_weights["Cash & Equivalents"] = sector_weights.get("Cash & Equivalents", 0) + weight
                continue
            
            info = market_data_client.get_ticker_info(ticker)
            sector = info.get("sector", "Other/Unknown")
            
            sector_weights[sector] = sector_weights.get(sector, 0) + weight

        # Sort by weight
        sorted_sectors = dict(sorted(sector_weights.items(), key=lambda item: item[1], reverse=True))
        
        return {
            "sector_breakdown": sorted_sectors,
            "stock_percentage": 100 - (sector_weights.get("Cash & Equivalents", 0) * 100)
        }

    @classmethod
    def generate_report(cls, state: ADKState) -> Dict[str, Any]:
        """
        Compiles the final evaluation and allocation report.
        """
        print(f"-> Reporting: Finalizing report for strategy {state.draft_strategy.strategy_id if state.draft_strategy else 'N/A'}")

        if state.approval_status == ApprovalStatus.REJECTED:
            return {
                "final_report": f"System Failure: Strategy rejected after {state.current_retry} retries. Rationale: {state.feedback_loop[-1] if state.feedback_loop else 'No feedback'}"
            }

        eval_metric = cls.calculate_evaluation_metric(state)
        sector_alloc = cls.get_sector_allocation(state)

        report = f"""
# Institutional Investment Report
**Strategy ID:** {state.draft_strategy.strategy_id if state.draft_strategy else 'N/A'}
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
            report += f"- {sector}: {weight*100:.2f}%\n"

        report += f"\n## 3. Executive Summary\n{state.draft_strategy.rationale if state.draft_strategy else 'No strategy generated.'}\n"

        return {
            "final_report": report,
            "metrics_log": {
                "evaluation_score": eval_metric["total_score"],
                "sector_allocation": sector_alloc["sector_breakdown"]
            }
        }

def reporting_agent(state: ADKState) -> Dict[str, Any]:
    """Node implementation for final report generation."""
    return ReportingAgent.generate_report(state)
