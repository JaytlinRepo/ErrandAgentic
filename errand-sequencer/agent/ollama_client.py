from __future__ import annotations

from agent.llm import BedrockLLM
from configs.settings import BEDROCK_MODEL_ID

SYSTEM = """You are a helpful assistant that helps users organize and sequence errands.
Be concise. When the user lists errands, acknowledge them and suggest a sensible order or \
next steps in plain language. If the list is empty, ask them to add errands."""


def generate_errand_response(
    errand_list: str,
    *,
    model: str | None = None,
    history_transcript: str = "",
) -> str:
    """Send errands to Bedrock and return the assistant reply."""
    llm = BedrockLLM(model_id=model or BEDROCK_MODEL_ID)
    text = errand_list.strip() if errand_list else ""
    user_msg = "My errands:\n" + text if text else "I have not listed any errands yet."
    if (history_transcript or "").strip():
        user_msg = f"Prior conversation:\n{history_transcript.strip()}\n\n{user_msg}"
    prompt = f"{SYSTEM}\n\n{user_msg}"
    return llm.query(prompt, max_tokens=512).strip()
