"""Minimal dark UI inspired by Claude web — typography-first, low chrome."""

from __future__ import annotations

import streamlit as st


def inject_claude_theme() -> None:
    st.markdown(
        """
<style>
  html, body, [class*="css"] {
    font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif !important;
  }

  .stApp {
    background: #1a1a1a !important;
    color: #ececec !important;
  }

  section[data-testid="stSidebar"] {
    background: #141414 !important;
    border-right: 1px solid #2a2a2a !important;
  }

  section[data-testid="stSidebar"] .block-container {
    padding-top: 1rem !important;
  }

  div[data-testid="stAppViewContainer"] .block-container {
    max-width: 42rem !important;
    padding-top: 1.5rem !important;
    padding-bottom: 3rem !important;
  }

  h1, h2, h3 { font-weight: 600 !important; letter-spacing: -0.02em !important; color: #f5f5f5 !important; }

  .stMarkdown p, .stMarkdown li { color: #d4d4d4 !important; line-height: 1.55 !important; }

  div[data-testid="stExpander"] {
    background: transparent !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 0.75rem !important;
  }

  div[data-baseweb="input"] input, textarea {
    background: #262626 !important;
    border: 1px solid #333 !important;
    border-radius: 0.75rem !important;
    color: #ececec !important;
  }

  div[data-baseweb="input"] input:focus, textarea:focus {
    border-color: #525252 !important;
    box-shadow: none !important;
  }

  form[data-testid="stForm"] {
    background: #222 !important;
    border: 1px solid #333 !important;
    border-radius: 1.25rem !important;
    padding: 0.35rem 0.5rem 0.5rem 0.5rem !important;
  }

  .stForm > div {
    gap: 0.35rem !important;
  }

  header[data-testid="stHeader"] {
    background: transparent !important;
  }

  .ea-muted { color: #888 !important; font-size: 0.85rem !important; }
</style>
        """,
        unsafe_allow_html=True,
    )


def title_bar() -> None:
    st.markdown(
        '<p style="font-size:1.35rem;font-weight:600;margin:0 0 0.25rem 0;color:#fafafa;">ErrandAgentic</p>'
        '<p class="ea-muted" style="margin:0 0 1.25rem 0;">Plan stops and routes with your local model.</p>',
        unsafe_allow_html=True,
    )
