"""Chat turns: user right, assistant left — minimal chrome."""

from __future__ import annotations

import html

import streamlit as st


def render_chat_history(pairs: list[tuple[str, str]]) -> None:
    """User messages right; assistant markdown left."""
    if not pairs:
        return
    for user_text, assistant_text in pairs:
        _, right = st.columns([1, 4])
        with right:
            u = html.escape(user_text).replace("\n", "<br/>")
            st.markdown(
                f"<div style='text-align:right;margin:0.2rem 0 0.6rem 0;'><span style='display:inline-block;max-width:100%;padding:0.45rem 0.8rem;border-radius:1rem;background:#2a2a2a;border:1px solid #383838;font-size:0.9rem;line-height:1.45;color:#eee;'>{u}</span></div>",
                unsafe_allow_html=True,
            )
        left, _ = st.columns([5, 1])
        with left:
            st.markdown(assistant_text)
        st.markdown("")
