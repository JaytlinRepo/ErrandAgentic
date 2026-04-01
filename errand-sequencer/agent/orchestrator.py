"""LangChain agent with AWS Bedrock (Converse) and tool calling."""

from __future__ import annotations

import time

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

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
from configs.ml_tracker import get_mlflow_tracker
from configs.settings import (
    AWS_DEFAULT_REGION,
    BEDROCK_AGENT_MODEL_ID,
    MAX_CHAT_HISTORY_TURNS,
    RAG_ENABLED,
    USER_MEMORY_ENABLED,
    USER_MEMORY_EXTRACT_ENABLED,
)
from tools.langchain_tools import ERRAND_TOOLS

_MAX_TOOL_ROUNDS = 12


def _stringify_message_content(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(content or "")


def _text_from_ai_message(msg: AIMessage) -> str:
    return _stringify_message_content(getattr(msg, "content", ""))


def _messages_preview(messages: list, max_chars: int = 48000) -> str:
    parts: list[str] = []
    for m in messages:
        label = type(m).__name__.replace("Message", "")
        parts.append(f"--- {label} ---\n{_stringify_message_content(getattr(m, 'content', ''))}")
    out = "\n\n".join(parts)
    return out[:max_chars]


def _tokens_from_ai_message(msg: AIMessage) -> tuple[int, int]:
    um = getattr(msg, "usage_metadata", None)
    if isinstance(um, dict):
        return int(um.get("input_tokens") or 0), int(um.get("output_tokens") or 0)
    return 0, 0


def _log_converse_round(
    *,
    tracker,
    model_id: str,
    messages: list,
    ai: AIMessage,
    latency_ms: float,
) -> float:
    in_t, out_t = _tokens_from_ai_message(ai)
    tool_calls = getattr(ai, "tool_calls", None) or []
    tools_used = [
        str(tc.get("name"))
        for tc in tool_calls
        if isinstance(tc, dict) and tc.get("name")
    ]
    tracker.log_model_call(
        model_type="agent_converse",
        model_id=model_id,
        prompt=_messages_preview(messages),
        response=_text_from_ai_message(ai)[:50000],
        input_tokens=in_t,
        output_tokens=out_t,
        latency_ms=latency_ms,
        tools_used=tools_used or None,
    )
    return tracker.estimate_cost(model_id, in_t, out_t)


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
    try:
        bullets = extract_preference_bullets(user_message, assistant_reply)
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
    model = model or BEDROCK_AGENT_MODEL_ID
    llm = ChatBedrockConverse(
        model=model,
        region_name=AWS_DEFAULT_REGION,
        temperature=0,
    )
    llm_with_tools = llm.bind_tools(ERRAND_TOOLS)
    tool_map = {t.name: t for t in ERRAND_TOOLS}

    history = list(chat_history or [])
    if len(history) > MAX_CHAT_HISTORY_TURNS:
        history = history[-MAX_CHAT_HISTORY_TURNS :]

    user_block = errand_list.strip() if errand_list else "(no errands listed)"
    tracker = get_mlflow_tracker()
    raw_for_log = (errand_list or "").strip() or user_block

    with tracker.chat_session_context(raw_user_input=raw_for_log):
        rag_block = _retrieve_knowledge_block(user_block)
        mem_block = _retrieve_user_memory_block(user_block, user_id)
        include_rag = bool(rag_block.strip())
        include_user_memory = bool(mem_block.strip())
        include_conversation = bool(history)

        human_parts: list[str] = []
        if rag_block.strip():
            human_parts.append(
                "Knowledge excerpts (from local knowledge base):\n" + rag_block.strip()
            )
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

        session_cost = 0.0

        t0 = time.perf_counter()
        ai: AIMessage = llm_with_tools.invoke(messages)
        lat0 = (time.perf_counter() - t0) * 1000.0
        ai = normalize_ai_text_content(ai)
        ai = repair_ai_message_for_embedded_tools(ai)
        session_cost += _log_converse_round(
            tracker=tracker,
            model_id=model,
            messages=messages,
            ai=ai,
            latency_ms=lat0,
        )
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
            t1 = time.perf_counter()
            ai = llm_with_tools.invoke(messages)
            lat1 = (time.perf_counter() - t1) * 1000.0
            ai = normalize_ai_text_content(ai)
            ai = repair_ai_message_for_embedded_tools(ai)
            session_cost += _log_converse_round(
                tracker=tracker,
                model_id=model,
                messages=messages,
                ai=ai,
                latency_ms=lat1,
            )
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
            user_message=extract_msg,
            assistant_reply=reply,
            user_id=user_id,
            persist_memory=persist_memory,
        )
        errand_lines = [ln.strip() for ln in user_block.splitlines() if ln.strip()]
        if not errand_lines:
            errand_lines = [user_block[:500]]
        tracker.finalize_chat_session(
            full_human_message=human_content,
            errands=errand_lines[:50],
            result=reply,
            total_cost=session_cost,
        )
        return reply
