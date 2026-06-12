import os
import pytest


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


RUN_LIVE_TESTS = _truthy(os.getenv("RUN_LIVE_TESTS"))

if RUN_LIVE_TESTS:
    os.environ["ADK_LIVE_MODE"] = "1"

    # Keep live Gemini for reasoning, but keep backtest code execution deterministic
    # unless you are specifically testing Gemini-generated executable code.
    os.environ.setdefault("ADK_LIVE_BACKTEST_CODEGEN", "0")
    os.environ.setdefault("GEMINI_MODEL", "gemini-2.5-flash")
else:
    # Normal pytest should be deterministic.
    os.environ["ADK_LIVE_MODE"] = "0"
    os.environ["ADK_LIVE_BACKTEST_CODEGEN"] = "0"


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "live: tests that call real external APIs such as Gemini, market data, or broker APIs",
    )
    config.addinivalue_line(
        "markers",
        "integration: multi-agent integration tests",
    )


def pytest_collection_modifyitems(config, items):
    if RUN_LIVE_TESTS:
        return

    skip_live = pytest.mark.skip(
        reason="Live test skipped. Set RUN_LIVE_TESTS=1 and ADK_LIVE_MODE=1 to run it."
    )

    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)
