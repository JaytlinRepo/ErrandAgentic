"""Errand list input UI."""

import streamlit as st


def errand_text_area(
    label: str = "Your errands",
    *,
    key: str = "errand_list",
    height: int = 120,
    placeholder: str | None = None,
) -> str:
    """Multi-line input for errands (lines or paragraph)."""
    ph = placeholder or (
        "One per line, or a short paragraph (e.g. Target, then Ross, then Starbucks).\n"
        "Stops are parsed automatically."
    )
    return st.text_area(label, height=height, placeholder=ph, key=key)
