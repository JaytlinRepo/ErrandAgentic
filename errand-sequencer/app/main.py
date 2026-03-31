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
from agent.user_identity import get_or_create_user_id
from app.components.chat_bubbles import render_chat_history
from app.components.claude_theme import inject_claude_theme, title_bar
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

_GEO_HTML = """
<script>
(function() {
  function go(params) {
    window.parent.location.replace(window.parent.location.pathname + "?" + params.toString());
  }
  if (!navigator.geolocation) {
    const p = new URLSearchParams(window.parent.location.search);
    p.set("geo_denied", "unsupported");
    go(p);
    return;
  }
  navigator.geolocation.getCurrentPosition(
    function(pos) {
      const p = new URLSearchParams(window.parent.location.search);
      p.delete("geo_denied");
      p.set("lat", String(pos.coords.latitude));
      p.set("lon", String(pos.coords.longitude));
      if (pos.coords.accuracy != null) p.set("acc", String(pos.coords.accuracy));
      go(p);
    },
    function() {
      const p = new URLSearchParams(window.parent.location.search);
      p.delete("lat"); p.delete("lon"); p.delete("acc");
      p.set("geo_denied", "1");
      go(p);
    },
    { enableHighAccuracy: true, timeout: 12000 }
  );
})();
</script>
"""


def main() -> None:
    st.set_page_config(page_title="ErrandAgentic", layout="wide", initial_sidebar_state="expanded")
    inject_claude_theme()

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "stops_for_session" not in st.session_state:
        st.session_state.stops_for_session = ""

    starting_location_note: str | None = None
    manual_start = ""
    model = OLLAMA_MODEL
    use_tools = True
    learn_memory = True

    with st.sidebar:
        if st.button("New chat", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.stops_for_session = ""
            st.session_state.pop("eat_last_food_pick", None)
            st.rerun()

        st.caption("Starting point")
        if st.button("Share location", use_container_width=True, help="Browser permission prompt"):
            components.html(_GEO_HTML, height=0)

        manual_start = st.text_input(
            "Start",
            value="",
            placeholder="ZIP, city, or address",
            key="sidebar_start_location",
            label_visibility="collapsed",
        ).strip()

        st.divider()
        with st.expander("Model & tools", expanded=False):
            model = st.text_input("Ollama model", value=model, help="Pulled in Ollama")
            st.caption(f"`{OLLAMA_HOST}`")
            use_tools = st.toggle("Maps & weather", value=use_tools)
            learn_memory = st.toggle("Remember preferences", value=learn_memory)
        user_id = get_or_create_user_id()

    qp = st.query_params
    lat = qp.get("lat")
    lon = qp.get("lon")
    acc = qp.get("acc")
    if lat and lon:
        try:
            starting_location_note = f"{float(lat):.6f},{float(lon):.6f}"
        except ValueError:
            st.sidebar.warning("Invalid coordinates in URL.")
    if manual_start:
        starting_location_note = manual_start

    has_location = bool((starting_location_note or "").strip())
    geo_denied = (qp.get("geo_denied") or "").strip()

    if has_location and starting_location_note:
        with st.sidebar:
            short = starting_location_note if len(starting_location_note) <= 36 else starting_location_note[:33] + "…"
            st.caption(f"Start: `{short}`")
            if acc and lat and lon:
                try:
                    st.caption(f"±{float(acc):.0f} m")
                except ValueError:
                    pass

    title_bar()

    if not has_location:
        if geo_denied == "1":
            st.warning(
                "Location was blocked. Use **Share location** in the sidebar and allow access, "
                "or type an address there."
            )
        elif geo_denied == "unsupported":
            st.warning("This browser has no geolocation. Type a start address in the sidebar.")
        else:
            st.caption("Set a starting point in the **sidebar** (share or type an address).")

    errands = st.session_state.stops_for_session
    errand_lines = extract_errand_lines(errands)
    food_candidates = [line for line in errand_lines if is_food_place(line)]
    eat_last = wants_eat_last(errands)
    last_food_place: str | None = None

    if eat_last and food_candidates:
        with st.expander("Eat last", expanded=len(food_candidates) > 1):
            if len(food_candidates) == 1:
                last_food_place = food_candidates[0]
                st.caption(f"Last stop: **{last_food_place}**")
            else:
                last_food_place = st.selectbox(
                    "Food stop last",
                    options=food_candidates,
                    index=len(food_candidates) - 1,
                    key="eat_last_food_pick",
                )
                st.caption("First reply uses the last food in your list until you change this.")
    elif eat_last and not food_candidates and errands.strip():
        with st.expander("Eat last"):
            st.caption("Add a restaurant name to your stops to use eat-last.")

    render_chat_history(st.session_state.chat_history)

    can_message = has_location

    with st.form("planner_chat", clear_on_submit=True):
        msg = st.text_area(
            "Message",
            height=120,
            placeholder=(
                "Stops and question in one message (e.g. Target, Ross, Starbucks — best order?), "
                "or reply here to continue."
            ),
            label_visibility="collapsed",
            disabled=not can_message,
        )
        submitted = st.form_submit_button("Send", type="primary", use_container_width=True, disabled=not can_message)

    incoming = None
    if submitted and msg and str(msg).strip():
        incoming = str(msg).strip()

    if incoming and can_message:
        if not st.session_state.stops_for_session.strip():
            first_lines = extract_errand_lines(incoming)
            if not first_lines:
                st.error("Add at least one stop (e.g. Target, Ross, Starbucks).")
                return
            st.session_state.stops_for_session = incoming.strip()

        errands = st.session_state.stops_for_session
        errand_lines = extract_errand_lines(errands)
        food_candidates = [line for line in errand_lines if is_food_place(line)]
        eat_last = wants_eat_last(errands)

        last_food_for_agent: str | None = None
        if eat_last and food_candidates:
            if len(food_candidates) == 1:
                last_food_for_agent = food_candidates[0]
            else:
                pick = st.session_state.get("eat_last_food_pick")
                last_food_for_agent = pick if pick in food_candidates else food_candidates[-1]

        prompt_text = with_start_location_context(errands, starting_location_note)
        prompt_text = with_food_preference_context(prompt_text, last_food_for_agent)
        prompt_text = with_unique_stop_constraint(prompt_text, errand_lines)
        prompt_text = with_planned_order_context(prompt_text, errand_lines, last_food_for_agent)
        prompt_text = with_eat_last_guardrail_context(
            prompt_text, wants_eat_last=eat_last, food_candidates=food_candidates
        )
        prompt_text = with_current_time_context(prompt_text)
        prior = list(st.session_state.chat_history)
        hist_transcript = ""
        for u, a in prior:
            hist_transcript += f"User: {u}\nAssistant: {a}\n\n"
        label = f"`{model}`…" if use_tools else f"`{model}`…"
        with st.spinner(label):
            try:
                if use_tools:
                    reply = run_errand_agent_with_tools(
                        prompt_text,
                        model=model or None,
                        chat_history=prior,
                        user_id=user_id,
                        persist_memory=learn_memory,
                        latest_user_message=incoming,
                    )
                else:
                    hist_transcript = f"{hist_transcript}User: {incoming}\n"
                    reply = generate_errand_response(
                        prompt_text,
                        model=model or None,
                        history_transcript=hist_transcript,
                    )
            except Exception as e:
                st.error("Could not reach Ollama.")
                st.code(str(e), language="text")
                return
        st.session_state.chat_history.append((incoming, reply))
        st.rerun()


if __name__ == "__main__":
    main()
