import uuid
from core.graph import adk_app
from core.state import ADKState, UserRequest


def run_framework_demo():
    print("=== ADK Framework v3.0: Autonomous Agentic 'Brain' Demo ===")

    # 1. Initialize State with a User Request
    initial_state = ADKState(
        request=UserRequest(
            asset_class="Equities",
            risk_tolerance="Moderate",
            time_horizon="6-12 Months",
            additional_constraints="Focus on Tech sector with low volatility.",
        )
    ).model_dump()

    # 2. Execute the Graph
    print(f"\nStarting Execution Loop...")
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    # We use stream to see the node transitions
    for output in adk_app.stream(initial_state, config=config):
        # output is a dict where keys are node names and values are their return dicts
        for node_name, state_update in output.items():
            print(f"Finished Node: {node_name}")

    print("\n=== Execution Complete ===")
    # The final state is what we'd want to inspect
    # In a real scenario, we might pull it from a checkpointer or the last output
    # For this mock, we just know it reached the end.


if __name__ == "__main__":
    run_framework_demo()
