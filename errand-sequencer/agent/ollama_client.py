"""Ollama chat client for errand sequencing."""

from __future__ import annotations

import ollama

from configs.settings import OLLAMA_HOST, OLLAMA_MODEL

SYSTEM = """You are a helpful assistant that helps users organize and sequence errands.
Be concise. When the user lists errands, acknowledge them and suggest a sensible order or \
next steps in plain language. If the list is empty, ask them to add errands."""


def generate_errand_response(errand_list: str, *, model: str | None = None) -> str:
    """Send errands to the local LLM and return the assistant reply."""
    model = model or OLLAMA_MODEL
    client = ollama.Client(host=OLLAMA_HOST)
    text = errand_list.strip() if errand_list else ""
    user_msg = "My errands:\n" + text if text else "I have not listed any errands yet."
    resp = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_msg},
        ],
    )
    return resp["message"]["content"]
