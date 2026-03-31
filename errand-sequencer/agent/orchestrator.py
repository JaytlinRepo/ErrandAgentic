"""LangChain agent with Ollama and tool calling."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_ollama import ChatOllama

from agent.memory_extract import extract_preference_bullets
from agent.tool_repair import (
    inject_routing_origin,
    normalize_ai_text_content,
    parse_default_origin_from_human_block,
    repair_ai_message_for_embedded_tools,
    strip_leaked_tool_json,
)

_ROUTING_TOOL_NAMES = frozenset({"get_travel_time", "get_directions"})
from agent.prompts import (
    CONVERSATION_TURN_INSTRUCTION,
    RAG_KNOWLEDGE_INSTRUCTION,
    TOOL_AGENT_SYSTEM,
    USER_MEMORY_INSTRUCTION,
)
from configs.settings import (
    MAX_CHAT_HISTORY_TURNS,
    OLLAMA_HOST,
    OLLAMA_MODEL,
    RAG_ENABLED,
    USER_MEMORY_ENABLED,
    USER_MEMORY_EXTRACT_ENABLED,
)
from tools.langchain_tools import ERRAND_TOOLS

_MAX_TOOL_ROUNDS = 12


def _retrieve_knowledge_block(user_text: str) -> str:
    if not RAG_ENABLED:
        return ""
    try:
        from rag.retriever import retrieve_context

        return retrieve_context(user_text)
    except Exception:
        return ""


def _retrieve_user_memory_block(user_text: str, user_id: str | None) -> str:
    if not USER_MEMORY_ENABLED or not (user_id or "").strip():
        return ""
    try:
        from rag.retriever import retrieve_user_memory

        return retrieve_user_memory(user_text, user_id.strip())
    except Exception:
        return ""


def _build_system_prompt(
    *,
    include_rag: bool,
    include_user_memory: bool,
    include_conversation: bool,
) -> str:
    parts: list[str] = [TOOL_AGENT_SYSTEM]
    if include_rag:
        parts.append(RAG_KNOWLEDGE_INSTRUCTION)
    if include_user_memory:
        parts.append(USER_MEMORY_INSTRUCTION)
    if include_conversation:
        parts.append(CONVERSATION_TURN_INSTRUCTION)
    return "\n\n".join(parts)


def _maybe_persist_user_insights(
    *,
    model: str,
    user_message: str,
    assistant_reply: str,
    user_id: str | None,
    persist_memory: bool,
) -> None:
    if (
        not persist_memory
        or not USER_MEMORY_ENABLED
        or not USER_MEMORY_EXTRACT_ENABLED
        or not (user_id or "").strip()
    ):
        return
    base = OLLAMA_HOST.rstrip("/")
    llm = ChatOllama(model=model, base_url=base, temperature=0)
    try:
        bullets = extract_preference_bullets(llm, user_message, assistant_reply)
        if not bullets:
            return
        from rag.retriever import upsert_user_memory_texts

        upsert_user_memory_texts(bullets, user_id.strip())
    except Exception:
        pass


def run_errand_agent_with_tools(
    errand_list: str,
    *,
    model: str | None = None,
    chat_history: list[tuple[str, str]] | None = None,
    user_id: str | None = None,
    persist_memory: bool = True,
    latest_user_message: str | None = None,
) -> str:
    """Run the chat model with Maps/weather tools; optional multi-turn history and Chroma user memory."""
    model = model or OLLAMA_MODEL
    base = OLLAMA_HOST.rstrip("/")
    llm = ChatOllama(model=model, base_url=base, temperature=0)
    llm_with_tools = llm.bind_tools(ERRAND_TOOLS)
    tool_map = {t.name: t for t in ERRAND_TOOLS}

    history = list(chat_history or [])
    if len(history) > MAX_CHAT_HISTORY_TURNS:
        history = history[-MAX_CHAT_HISTORY_TURNS :]

    user_block = errand_list.strip() if errand_list else "(no errands listed)"
    rag_block = _retrieve_knowledge_block(user_block)
    mem_block = _retrieve_user_memory_block(user_block, user_id)
    include_rag = bool(rag_block.strip())
    include_user_memory = bool(mem_block.strip())
    include_conversation = bool(history)

    human_parts: list[str] = []
    if rag_block.strip():
        human_parts.append("Knowledge excerpts (from local knowledge base):\n" + rag_block.strip())
    if mem_block.strip():
        human_parts.append("Saved preferences from past sessions:\n" + mem_block.strip())
    human_parts.append("My errands:\n" + user_block)
    human_content = "\n\n".join(human_parts)
    default_origin = parse_default_origin_from_human_block(human_content)

    messages: list = [
        SystemMessage(
            content=_build_system_prompt(
                include_rag=include_rag,
                include_user_memory=include_user_memory,
                include_conversation=include_conversation,
            )
        ),
    ]
    for usr, ast in history:
        messages.append(HumanMessage(content=usr))
        messages.append(AIMessage(content=ast))
    messages.append(HumanMessage(content=human_content))

    ai: AIMessage = llm_with_tools.invoke(messages)
    ai = normalize_ai_text_content(ai)
    ai = repair_ai_message_for_embedded_tools(ai)
    messages.append(ai)

    rounds = 0
    while getattr(ai, "tool_calls", None) and rounds < _MAX_TOOL_ROUNDS:
        rounds += 1
        routing_idx = 0
        for tc in ai.tool_calls:
            name = tc.get("name")
            args = tc.get("args") or {}
            force_first = False
            if name in _ROUTING_TOOL_NAMES and (default_origin or "").strip():
                routing_idx += 1
                if routing_idx == 1:
                    force_first = True
            args = inject_routing_origin(name, args, default_origin, force_first_leg=force_first)
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
        ai = normalize_ai_text_content(ai)
        ai = repair_ai_message_for_embedded_tools(ai)
        messages.append(ai)

    if getattr(ai, "tool_calls", None):
        reply = (
            (ai.content or "").strip()
            or "The model kept requesting tools without a final summary; try a smaller question or another model."
        )
    else:
        reply = (ai.content or "").strip()
    reply = strip_leaked_tool_json(reply)

    extract_msg = (latest_user_message or "").strip() or user_block[:2000]
    _maybe_persist_user_insights(
        model=model,
        user_message=extract_msg,
        assistant_reply=reply,
        user_id=user_id,
        persist_memory=persist_memory,
    )
    return reply
