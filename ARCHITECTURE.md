# ADK v4.0 Architectural Design

## 1. Hierarchical Shared Session State (H-SSS)
The backbone of ADK is a centralized, Pydantic-enforced state object. This ensures 100% data integrity as information passes through parallel and cyclic nodes.

- **Request**: User intent and constraints.
- **Observations**: Multi-agent analytical outputs (Fundamental, Quant, Sentiment).
- **Alpha Memory**: Retrieved context from past successful runs.
- **Feedback Loop**: Recursive critiques from the Multi-Factor Critic.

## 2. LangGraph Orchestration
The framework uses a Cyclic Directed Acyclic Graph (DAG) pattern:

```text
[Planner] -> [Analysts (Fan-out)] -> [Ensemble CIO] -> [Critic] --(Reject)--> [Optimizer] -> [Meta-Reflector] --|
                                         |                                                               |
                                         |---(Approve)--> [Stress Tester] -> [Quant Coder] --(Error)-----|
                                                                              |
                                                                         (Success)
                                                                              |
                                                                        [HITL Interrupt]
                                                                              |
                                                                        [Execution Agent] -> [Reporting]
```

## 3. High-Intelligence Nodes
- **Gemini 3.1 Pro Preview**: Serves as the primary reasoning engine for non-linear decision making (Planning, Synthesis, Critique).
- **ChromaDB**: Provides semantic retrieval for Alpha Memory.
- **Local Sandbox**: An isolated subprocess environment for executing generated Python code safely.

## 4. Conflict Resolution Engine
Located within the `Ensemble CIO`, this rule-based and AI-driven engine weights signals from analysts. If signals are contradictory (e.g., Bullish Fundamental vs. Bearish Quant), the system dynamically reduces the ticker's allocation to zero to prioritize capital preservation.
