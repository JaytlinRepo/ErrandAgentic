"""Streamlit entry point for Errand Sequencer."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st
import streamlit.components.v1 as components

from agent.ollama_client import generate_errand_response
from agent.orchestrator import run_errand_agent_with_tools
from app.components.errand_input import errand_text_area
from configs.settings import OLLAMA_HOST, OLLAMA_MODEL
from guardrails import (
    extract_errand_lines,
    is_food_place,
    wants_eat_last,
    with_current_time_context,
    with_eat_last_guardrail_context,
    with_food_preference_context,
    with_planned_order_context,
    with_start_location_context,
    with_unique_stop_constraint,
)


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
        st.divider()
        st.subheader("Starting location")
        starting_location_note: str | None = None
        st.caption("Click to request location. Your browser will show a native Yes/No permission prompt.")
        if st.button("Share current location"):
            components.html(
                """
                <script>
                (function() {
                  if (!navigator.geolocation) {
                    alert("Geolocation is not supported in this browser.");
                    return;
                  }
                  navigator.geolocation.getCurrentPosition(
                    function(pos) {
                      const p = new URLSearchParams(window.parent.location.search);
                      p.set("lat", String(pos.coords.latitude));
                      p.set("lon", String(pos.coords.longitude));
                      if (pos.coords.accuracy != null) {
                        p.set("acc", String(pos.coords.accuracy));
                      }
                      const next = window.parent.location.pathname + "?" + p.toString();
                      window.parent.location.replace(next);
                    },
                    function(err) {
                      alert("Location permission denied or unavailable: " + err.message);
                    },
                    { enableHighAccuracy: true, timeout: 12000 }
                  );
                })();
                </script>
                """,
                height=0,
            )
        qp = st.query_params
        lat = qp.get("lat")
        lon = qp.get("lon")
        acc = qp.get("acc")
        if lat and lon:
            try:
                starting_location_note = f"{float(lat):.6f},{float(lon):.6f}"
                st.caption(f"Using current coordinates: `{starting_location_note}`")
                if acc:
                    st.caption(f"Reported accuracy: ~{float(acc):.0f} meters")
            except ValueError:
                st.warning("Could not parse location values from URL parameters.")
        manual_start = st.text_input(
            "Or enter a custom start location",
            value="",
            placeholder="e.g., 02139 or 77 Massachusetts Ave, Cambridge MA",
        ).strip()
        if manual_start:
            starting_location_note = manual_start

    with st.expander("Example: weather + drive time (good for testing tools)"):
        st.markdown(
            "Paste something like this when **Use real-world tools** is on — the model should call "
            "`get_weather` and `get_travel_time` and cite numbers:\n\n"
            "_I’m in Cambridge, MA. What’s the weather here? How long is the drive from "
            "Harvard Square to Trader Joe’s on Memorial Drive? Suggest an errand order._"
        )

    errands = errand_text_area()
    errand_lines = extract_errand_lines(errands)
    food_candidates = [line for line in errand_lines if is_food_place(line)]
    eat_last = wants_eat_last(errands)
    last_food_place: str | None = None
    if eat_last and len(food_candidates) == 1:
        # One clear food stop: enforce it as last automatically.
        last_food_place = food_candidates[0]
        st.info(f'Applying preference: "{last_food_place}" will be the final stop.')
    elif eat_last and len(food_candidates) >= 2:
        st.info("You listed multiple food places and said you want to eat last.")
        last_food_place = st.selectbox(
            "Which food place should be last?",
            options=food_candidates,
            help="This is enforced as a hard preference in the planning prompt.",
        )
    elif eat_last and len(food_candidates) == 0:
        st.warning(
            "No restaurant/food stop detected in the errand list. "
            "Add one (e.g. McDonalds) if you want 'eat last' enforced."
        )
    submit = st.button("Get suggestions", type="primary", disabled=not errands.strip())

    if submit:
        prompt_text = with_start_location_context(errands, starting_location_note)
        prompt_text = with_food_preference_context(prompt_text, last_food_place)
        prompt_text = with_unique_stop_constraint(prompt_text, errand_lines)
        prompt_text = with_planned_order_context(prompt_text, errand_lines, last_food_place)
        prompt_text = with_eat_last_guardrail_context(
            prompt_text, wants_eat_last=eat_last, food_candidates=food_candidates
        )
        prompt_text = with_current_time_context(prompt_text)
        label = f"Asking `{model}` with tools…" if use_tools else f"Asking `{model}`…"
        with st.spinner(label):
            try:
                if use_tools:
                    reply = run_errand_agent_with_tools(prompt_text, model=model or None)
                else:
                    reply = generate_errand_response(prompt_text, model=model or None)
            except Exception as e:
                st.error("Could not reach Ollama or the model failed.")
                st.code(str(e), language="text")
                st.info("Ensure Ollama is running (`ollama serve`) and the model is installed (`ollama pull llama3.2`).")
                return
        st.subheader("Suggestion")
        st.write(reply)


if __name__ == "__main__":
    main()
