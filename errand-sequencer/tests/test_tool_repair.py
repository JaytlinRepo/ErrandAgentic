"""Tests for Ollama embedded tool JSON repair."""

from __future__ import annotations

from langchain_core.messages import AIMessage

from agent.tool_repair import (
    extract_embedded_tool_calls,
    inject_routing_origin,
    parse_default_origin_from_human_block,
    repair_ai_message_for_embedded_tools,
    strip_leaked_tool_json,
)


def test_parse_default_origin():
    h = "Starting location context for routing: 33.773,-84.665\n\nErrands:\nfoo"
    assert parse_default_origin_from_human_block(h) == "33.773,-84.665"


def test_inject_origin():
    args = {"destination": "x", "mode": "driving"}
    out = inject_routing_origin("get_directions", args, "33, -84")
    assert out["origin"] == "33, -84"


def test_inject_origin_force_first_leg_overwrites_wrong_origin():
    args = {"origin": "Waffle House", "destination": "Walmart", "mode": "driving"}
    out = inject_routing_origin("get_directions", args, "33.5, -84.3", force_first_leg=True)
    assert out["origin"] == "33.5, -84.3"
    assert out["destination"] == "Walmart"


def test_inject_origin_second_leg_keeps_model_origin():
    args = {"origin": "Waffle House", "destination": "Walmart", "mode": "driving"}
    out = inject_routing_origin("get_directions", args, "33.5, -84.3", force_first_leg=False)
    assert out["origin"] == "Waffle House"


def test_extract_embedded_tool_calls():
    text = (
        'Since you need food.\n\n'
        '{"name": "get_directions", "parameters": {"destination": "33.77,-84.66", "mode": "driving"}}'
    )
    calls, cleaned = extract_embedded_tool_calls(text)
    assert len(calls) == 1
    assert calls[0]["name"] == "get_directions"
    assert calls[0]["args"]["destination"] == "33.77,-84.66"
    assert "Since you need food" in cleaned
    assert "{" not in cleaned or "name" not in cleaned


def test_repair_ai_message():
    raw = AIMessage(
        content=(
            "I'll check.\n"
            '{"name": "get_directions", "parameters": {"destination": "1,2", "mode": "driving"}}'
        )
    )
    fixed = repair_ai_message_for_embedded_tools(raw)
    assert fixed.tool_calls
    assert fixed.tool_calls[0]["name"] == "get_directions"
    assert "{" not in (fixed.content or "")


def test_strip_leaked_tool_json():
    s = 'Done.\n\n{"name": "get_weather", "parameters": {"location": "Boston"}}'
    t = strip_leaked_tool_json(s)
    assert "{" not in t
    assert "Done" in t
