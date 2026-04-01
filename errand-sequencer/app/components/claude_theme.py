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
    color: #f0f0f0 !important;
  }

  section[data-testid="stSidebar"] {
    background: #161616 !important;
    border-right: 1px solid #3a3a3a !important;
    color: #eaeaea !important;
  }

  section[data-testid="stSidebar"] .block-container {
    padding-top: 1rem !important;
  }

  /* Sidebar: labels, captions, helper text */
  section[data-testid="stSidebar"] label p,
  section[data-testid="stSidebar"] label span,
  section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
  section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] span {
    color: #e4e4e4 !important;
  }

  section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p,
  section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] span,
  section[data-testid="stSidebar"] .stMarkdown p,
  section[data-testid="stSidebar"] small {
    color: #c8c8c8 !important;
  }

  div[data-testid="stAppViewContainer"] .block-container {
    max-width: 42rem !important;
    padding-top: 1.5rem !important;
    padding-bottom: 3rem !important;
  }

  h1, h2, h3 { font-weight: 600 !important; letter-spacing: -0.02em !important; color: #fafafa !important; }

  .stMarkdown p, .stMarkdown li { color: #e0e0e0 !important; line-height: 1.55 !important; }

  /* Markdown bold / emphasis (assistant replies use **text** — keep visible on dark bg) */
  .stMarkdown strong, .stMarkdown b {
    font-weight: 700 !important;
    color: #fafafa !important;
  }
  .stMarkdown em, .stMarkdown i:not(.ea-muted) {
    font-style: italic !important;
    color: #ececec !important;
  }

  /* Main-area captions (e.g. “Set a starting point…”) */
  div[data-testid="stAppViewContainer"] [data-testid="stCaptionContainer"] p,
  div[data-testid="stAppViewContainer"] [data-testid="stCaptionContainer"] span {
    color: #c4c4c4 !important;
  }

  div[data-testid="stExpander"] {
    background: #1e1e1e !important;
    border: 1px solid #404040 !important;
    border-radius: 0.75rem !important;
  }

  div[data-testid="stExpander"] details summary,
  div[data-testid="stExpander"] summary span {
    color: #ececec !important;
  }

  div[data-baseweb="input"] input,
  div[data-baseweb="textarea"] textarea,
  textarea {
    background: #2a2a2a !important;
    border: 1px solid #4a4a4a !important;
    border-radius: 0.75rem !important;
    color: #f5f5f5 !important;
  }

  div[data-baseweb="input"] input::placeholder,
  div[data-baseweb="textarea"] textarea::placeholder,
  textarea::placeholder {
    color: #b8b8b8 !important;
    opacity: 1 !important;
  }

  div[data-baseweb="input"] input:focus,
  div[data-baseweb="textarea"] textarea:focus,
  textarea:focus {
    border-color: #737373 !important;
    box-shadow: none !important;
  }

  form[data-testid="stForm"] {
    background: #242424 !important;
    border: 1px solid #454545 !important;
    border-radius: 1.25rem !important;
    padding: 0.35rem 0.5rem 0.5rem 0.5rem !important;
  }

  .stForm > div {
    gap: 0.35rem !important;
  }

  /* Primary actions stay readable */
  .stButton > button[kind="primary"] {
    font-weight: 600 !important;
  }

  /* Disabled submit: clearer than default faint grey */
  .stButton > button:disabled {
    color: #9ca3af !important;
    border-color: #4b5563 !important;
    background: #2d2d2d !important;
  }

  header[data-testid="stHeader"] {
    background: transparent !important;
  }

  .ea-muted { color: #bdbdbd !important; font-size: 0.9rem !important; }
</style>
        """,
        unsafe_allow_html=True,
    )


def title_bar() -> None:
    st.markdown(
        '<p style="font-size:1.35rem;font-weight:600;margin:0 0 0.25rem 0;color:#fafafa;">ErrandAgentic</p>'
        '<p class="ea-muted" style="margin:0 0 1.25rem 0;">Plan stops and routes with AWS Bedrock.</p>',
        unsafe_allow_html=True,
    )
