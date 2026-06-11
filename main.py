import uuid
from core.graph import adk_app
from core.state import ADKState, UserRequest


def run_framework_demo(auto_approve: bool = True):
    print("=== ADK Framework v4.0: Autonomous Agentic Trading Demo ===")

    initial_state = ADKState(
        request=UserRequest(
            asset_class="Equities",
            risk_tolerance="Moderate",
            time_horizon="6-12 Months",
            additional_constraints="Focus on Tech sector with low volatility.",
            tickers=["AAPL", "MSFT"],
        )
    ).model_dump()

    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    print("\nStarting analysis loop...")
    for output in adk_app.stream(initial_state, config=config):
        for node_name in output:
            print(f"Finished Node: {node_name}")

    snapshot = adk_app.get_state(config)
    if "execution" in snapshot.next:
        print("\nHITL checkpoint reached before execution.")
        if auto_approve:
            print("Auto-approving demo execution so every agent runs end-to-end...")
            for output in adk_app.stream(None, config=config):
                for node_name in output:
                    print(f"Finished Node: {node_name}")
        else:
            print("Pass auto_approve=True or call adk_app.invoke(None, config=config) to resume.")

    final_state = adk_app.get_state(config).values
    print("\n=== Execution Complete ===")
    print(final_state.get("final_report") or "No final report generated.")
    return final_state


if __name__ == "__main__":
    run_framework_demo()
