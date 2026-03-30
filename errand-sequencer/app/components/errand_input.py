"""Errand list input UI."""

import streamlit as st


def errand_text_area(label: str = "Your errands", *, key: str = "errand_list") -> str:
    """Multi-line input for errands (e.g. one per line)."""
    return st.text_area(
        label,
        height=220,
        placeholder="Post office\nGrocery store\nPick up dry cleaning",
        key=key,
    )
