"""LangChain agent with Ollama and tool calling."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_ollama import ChatOllama

from agent.prompts import TOOL_AGENT_SYSTEM
from configs.settings import OLLAMA_HOST, OLLAMA_MODEL
from tools.langchain_tools import ERRAND_TOOLS

_MAX_TOOL_ROUNDS = 12


def run_errand_agent_with_tools(errand_list: str, *, model: str | None = None) -> str:
    """Run the chat model with Maps/weather tools bound; return the final assistant text."""
    model = model or OLLAMA_MODEL
    base = OLLAMA_HOST.rstrip("/")
    llm = ChatOllama(model=model, base_url=base, temperature=0)
    llm_with_tools = llm.bind_tools(ERRAND_TOOLS)
    tool_map = {t.name: t for t in ERRAND_TOOLS}

    user_block = errand_list.strip() if errand_list else "(no errands listed)"
    messages: list = [
        SystemMessage(content=TOOL_AGENT_SYSTEM),
        HumanMessage(content=f"My errands:\n{user_block}"),
    ]

    ai: AIMessage = llm_with_tools.invoke(messages)
    messages.append(ai)

    rounds = 0
    while getattr(ai, "tool_calls", None) and rounds < _MAX_TOOL_ROUNDS:
        rounds += 1
        for tc in ai.tool_calls:
            name = tc.get("name")
            args = tc.get("args") or {}
            tid = tc.get("id") or ""
            tool = tool_map.get(name)
            if tool is None:
                out = f"Unknown tool: {name}"
            else:
                try:
                    out = tool.invoke(args)
                except Exception as e:
                    out = f"Error running {name}: {e}"
            messages.append(ToolMessage(content=str(out), tool_call_id=tid))
        ai = llm_with_tools.invoke(messages)
        messages.append(ai)

    if getattr(ai, "tool_calls", None):
        return (
            (ai.content or "").strip()
            or "The model kept requesting tools without a final summary; try a smaller question or another model."
        )
    return (ai.content or "").strip()
