"""Tests for LangChain + Ollama orchestration."""

from __future__ import annotations

import os

import pytest

from agent.orchestrator import run_errand_agent_with_tools
from tools.langchain_tools import ERRAND_TOOLS


def test_errand_tools_registered():
    names = {t.name for t in ERRAND_TOOLS}
    assert names == {"get_travel_time", "get_directions", "get_hours", "get_weather"}


@pytest.mark.skipif(os.getenv("ERRAND_AGENT_INTEGRATION") != "1", reason="Set ERRAND_AGENT_INTEGRATION=1 for live Ollama")
def test_agent_runs_real_errand_list_with_tools():
    """Phase 2: model reasons over a realistic list and may call tools (needs Ollama + optional Maps key)."""
    prompt = """Today in Cambridge MA I need to:
- Mail a package at USPS near Harvard
- Pick up a prescription at CVS Harvard Square
- Groceries at Trader Joe's on Memorial Drive

What's a good order? If useful, check weather and whether CVS tends to be open afternoon, and travel time between Harvard area and Memorial Drive."""
    model = os.getenv("OLLAMA_MODEL") or "llama3.2:latest"
    reply = run_errand_agent_with_tools(prompt, model=model)
    assert len(reply.strip()) > 80
