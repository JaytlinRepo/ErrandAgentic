"""Ollama sometimes emits tool calls as JSON inside message text instead of structured tool_calls."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from langchain_core.messages import AIMessage


def _stringify_message_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text" and "text" in block:
                parts.append(str(block["text"]))
            elif isinstance(block, dict) and "text" in block:
                parts.append(str(block["text"]))
            else:
                parts.append(str(block))
        return "\n".join(parts)
    return str(content)


def normalize_ai_text_content(ai: AIMessage) -> AIMessage:
    """Ensure .content is a plain string for JSON repair and display."""
    if isinstance(ai.content, str):
        return ai
    return AIMessage(
        content=_stringify_message_content(ai.content),
        tool_calls=getattr(ai, "tool_calls", None) or [],
        id=getattr(ai, "id", None),
    )

_ROUTING_TOOLS = frozenset({"get_travel_time", "get_directions"})


def parse_default_origin_from_human_block(human_block: str) -> str | None:
    """Read coordinates or address from guardrail 'Starting location context for routing:' line."""
    if not human_block:
        return None
    m = re.search(
        r"Starting location context for routing:\s*([^\n]+)",
        human_block,
        flags=re.IGNORECASE,
    )
    if not m:
        return None
    s = m.group(1).strip()
    return s or None


def inject_routing_origin(
    tool_name: str,
    args: dict[str, Any],
    default_origin: str | None,
) -> dict[str, Any]:
    """Fill missing origin for Distance Matrix / Directions when the user shared a start location."""
    if tool_name not in _ROUTING_TOOLS or not (default_origin or "").strip():
        return args
    out = dict(args)
    o = out.get("origin")
    if o is None or (isinstance(o, str) and not o.strip()):
        out["origin"] = default_origin.strip()
    return out


def strip_leaked_tool_json(content: str) -> str:
    """Remove JSON objects that look like tool invocations from visible assistant text."""
    if not content:
        return content
    out: list[str] = []
    start = 0
    while start < len(content):
        idx = content.find('{"name"', start)
        if idx == -1:
            out.append(content[start:])
            break
        out.append(content[start:idx])
        dec = json.JSONDecoder()
        try:
            obj, end = dec.raw_decode(content[idx:])
            if isinstance(obj, dict) and str(obj.get("name", "")).startswith("get_"):
                start = idx + end
                while start < len(content) and content[start] in "\n \t\r":
                    start += 1
                continue
        except json.JSONDecodeError:
            pass
        out.append(content[idx])
        start = idx + 1
    return "".join(out).strip()


def _normalize_args(raw: dict[str, Any]) -> dict[str, Any]:
    inner = raw.get("parameters") or raw.get("args")
    if isinstance(inner, dict):
        return dict(inner)
    return {k: v for k, v in raw.items() if k not in ("name", "type")}


def extract_embedded_tool_calls(content: str) -> tuple[list[dict[str, Any]], str]:
    """Parse tool-like JSON blobs from model text; return LangChain-style tool_calls and cleaned text."""
    if not content or '{"name"' not in content:
        return [], content
    found: list[dict[str, Any]] = []
    segments: list[tuple[int, int]] = []
    start = 0
    while start < len(content):
        idx = content.find('{"name"', start)
        if idx == -1:
            break
        dec = json.JSONDecoder()
        try:
            obj, end = dec.raw_decode(content[idx:])
        except json.JSONDecodeError:
            start = idx + 1
            continue
        if not (
            isinstance(obj, dict)
            and isinstance(obj.get("name"), str)
            and obj["name"].startswith("get_")
        ):
            start = idx + 1
            continue
        name = obj["name"]
        args = _normalize_args(obj)
        tid = f"embedded_{uuid.uuid4().hex[:16]}"
        found.append({"name": name, "args": args, "id": tid, "type": "tool_call"})
        segments.append((idx, idx + end))
        start = idx + end

    if not found:
        return [], content

    cleaned_parts: list[str] = []
    last = 0
    for a, b in segments:
        cleaned_parts.append(content[last:a])
        last = b
    cleaned_parts.append(content[last:])
    cleaned = "".join(cleaned_parts).strip()
    return found, cleaned


def repair_ai_message_for_embedded_tools(ai: AIMessage) -> AIMessage:
    """If the model put tool JSON in content but left tool_calls empty, fix the AIMessage."""
    existing = getattr(ai, "tool_calls", None) or []
    if existing:
        return ai
    content = _stringify_message_content(ai.content)
    if '{"name"' not in content:
        return ai
    calls, cleaned = extract_embedded_tool_calls(content)
    if not calls:
        return ai
    return AIMessage(
        content=cleaned or "",
        tool_calls=calls,
        id=getattr(ai, "id", None),
    )
