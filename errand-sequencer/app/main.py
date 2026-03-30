"""Streamlit entry point for Errand Sequencer."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from agent.ollama_client import generate_errand_response
from agent.orchestrator import run_errand_agent_with_tools
from app.components.errand_input import errand_text_area
from configs.settings import OLLAMA_HOST, OLLAMA_MODEL


def main() -> None:
    st.set_page_config(page_title="Errand Sequencer", layout="centered")
    st.title("Errand Sequencer")
    st.caption("Runs against your local Ollama server.")

    with st.sidebar:
        st.header("Model")
        model = st.text_input("Ollama model name", value=OLLAMA_MODEL, help="Must be pulled in Ollama first.")
        st.caption(f"API: `{OLLAMA_HOST}`")
        use_tools = st.checkbox(
            "Use real-world tools (LangChain + Maps + weather)",
            value=True,
            help="Calls get_travel_time, get_directions, get_hours, get_weather when the model chooses.",
        )

    errands = errand_text_area()
    submit = st.button("Get suggestions", type="primary", disabled=not errands.strip())

    if submit:
        label = f"Asking `{model}` with tools…" if use_tools else f"Asking `{model}`…"
        with st.spinner(label):
            try:
                if use_tools:
                    reply = run_errand_agent_with_tools(errands, model=model or None)
                else:
                    reply = generate_errand_response(errands, model=model or None)
            except Exception as e:
                st.error("Could not reach Ollama or the model failed.")
                st.code(str(e), language="text")
                st.info("Ensure Ollama is running (`ollama serve`) and the model is installed (`ollama pull llama3.2`).")
                return
        st.subheader("Suggestion")
        st.write(reply)


if __name__ == "__main__":
    main()
