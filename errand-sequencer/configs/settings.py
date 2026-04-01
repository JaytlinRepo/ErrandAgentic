"""Central configuration: model names, DB paths, etc."""

from __future__ import annotations

import os
from pathlib import Path

_ENV_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _ENV_DIR / ".env"

try:
    from dotenv import load_dotenv

    if _ENV_FILE.exists():
        # Prefer values from `.env` so local keys win over empty shell vars.
        load_dotenv(_ENV_FILE, override=True)
except ImportError:
    pass

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:latest")

# AWS Bedrock — InvokeModel (e.g. Llama 3) for simple chat + memory extraction
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "meta.llama3-8b-instruct-v1:0")
# Converse API + tool use (Llama 3 8B does not support tools; default to Claude Haiku)
# Use inference profile ID (us.*) for Converse; base anthropic.* id often rejects on-demand.
BEDROCK_AGENT_MODEL_ID = os.environ.get(
    "BEDROCK_AGENT_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0"
)
AWS_DEFAULT_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

# MLflow Layer 2 — see configs/ml_tracker.py. Default store: SQLite at data/mlflow/tracking.db
# (enables MLflow Overview). Override with MLFLOW_TRACKING_URI; toggle MLFLOW_ENABLED, MLFLOW_LOG_RAG.

# Google Maps Platform (Places, Distance Matrix; Directions available for future use)
# Set in `.env` as GOOGLE_MAPS_API_KEY=... (never hard-code keys in source).
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()

# RAG (Chroma + sentence-transformers)
_RAG_ROOT = _ENV_DIR / "data"
RAG_RAW_DIR = Path(os.environ.get("RAG_RAW_DIR", str(_RAG_ROOT / "raw")))
# Local disk path: CHROMA_DB_PATH wins (alias), else RAG_CHROMA_DIR, else data/chroma_db/
RAG_CHROMA_DIR = Path(
    os.environ.get("CHROMA_DB_PATH")
    or os.environ.get("RAG_CHROMA_DIR", str(_RAG_ROOT / "chroma_db"))
)
RAG_COLLECTION = os.environ.get("RAG_COLLECTION", "errand_knowledge")
# One collection; chunk metadata distinguishes curated knowledge vs per-user memory.
RAG_KIND_GENERAL = "general"
RAG_KIND_USER = "user"
RAG_EMBEDDING_MODEL = os.environ.get(
    "RAG_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
RAG_TOP_K = int(os.environ.get("RAG_TOP_K", "5"))
RAG_CHUNK_SIZE = int(os.environ.get("RAG_CHUNK_SIZE", "600"))
RAG_CHUNK_OVERLAP = int(os.environ.get("RAG_CHUNK_OVERLAP", "120"))
RAG_ENABLED = os.environ.get("RAG_ENABLED", "true").lower() in ("1", "true", "yes")

# Cross-session user memory (Chroma kind=user); retrieve + optional post-turn extraction.
USER_MEMORY_ENABLED = os.environ.get("USER_MEMORY_ENABLED", "true").lower() in ("1", "true", "yes")
USER_MEMORY_EXTRACT_ENABLED = os.environ.get("USER_MEMORY_EXTRACT_ENABLED", "true").lower() in (
    "1",
    "true",
    "yes",
)
MAX_CHAT_HISTORY_TURNS = int(os.environ.get("MAX_CHAT_HISTORY_TURNS", "10"))
RUNTIME_DIR = Path(os.environ.get("RUNTIME_DIR", str(_ENV_DIR / "data" / "runtime")))

# Chroma Cloud vs local disk — set CHROMA_MODE=cloud (recommended with Cloud) or local.
# If CHROMA_MODE is unset, falls back to legacy: Cloud when CHROMA_API_KEY is set, else local.
CHROMA_API_KEY = (
    os.environ.get("CHROMA_API_KEY", "").strip()
    or os.environ.get("CHROMA_CLOUD_API_KEY", "").strip()
)
CHROMA_TENANT = os.environ.get("CHROMA_TENANT", "").strip() or None
# Chroma Cloud requires a database under your tenant (create in console or `python -m rag.ensure_chroma_database`).
CHROMA_DATABASE = os.environ.get("CHROMA_DATABASE", "").strip() or None
# Used when CHROMA_API_KEY + CHROMA_TENANT are set but CHROMA_DATABASE is omitted (matches auto-created DB).
CHROMA_DATABASE_DEFAULT = os.environ.get("CHROMA_DATABASE_DEFAULT", "errand_rag").strip()

_chroma_mode_raw = os.environ.get("CHROMA_MODE", "").strip().lower()
if _chroma_mode_raw in ("cloud", "1", "true", "yes"):
    CHROMA_USE_CLOUD = True
elif _chroma_mode_raw in ("local", "disk", "persistent", "0", "false", "no"):
    CHROMA_USE_CLOUD = False
else:
    CHROMA_USE_CLOUD = bool(CHROMA_API_KEY)
