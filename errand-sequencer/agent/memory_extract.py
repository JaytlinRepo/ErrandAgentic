"""Extract short preference bullets from a turn for user-memory upsert."""

from __future__ import annotations

from agent.llm import BedrockLLM


def extract_preference_bullets(
    user_message: str,
    assistant_reply: str,
) -> list[str]:
    """Return 0–5 standalone lines suitable for embedding; empty if nothing to save."""
    user_message = (user_message or "").strip()
    assistant_reply = (assistant_reply or "").strip()
    if not user_message and not assistant_reply:
        return []
    prompt = f"""Extract zero to five short, standalone facts about the USER's standing preferences for errands (stores, timing, parking, dietary restrictions, places to avoid). Ignore generic routing advice. One fact per line; no bullets or numbers.
If nothing is worth remembering for future sessions, reply with exactly: NONE

User message:
{user_message[:1800]}

Assistant reply:
{assistant_reply[:1800]}
"""
    llm = BedrockLLM()
    text = (llm.query(prompt, max_tokens=256) or "").strip()
    if not text:
        return []
    first = text.splitlines()[0].strip().upper()
    if first == "NONE" or first.startswith("NONE"):
        return []
    out: list[str] = []
    for line in text.splitlines():
        s = line.strip().lstrip("-•*").strip()
        if not s or s.upper() == "NONE":
            continue
        if len(s) > 8:
            out.append(s)
    return out[:5]
