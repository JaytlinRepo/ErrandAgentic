"""Central configuration: model names, DB paths, etc."""

from __future__ import annotations

import os
from pathlib import Path

_ENV_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _ENV_DIR / ".env"

try:
    from dotenv import load_dotenv

    if _ENV_FILE.exists():
        load_dotenv(_ENV_FILE)
except ImportError:
    pass

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:latest")

# Google Maps Platform (Places, Distance Matrix; Directions available for future use)
# Set in `.env` as GOOGLE_MAPS_API_KEY=... (never hard-code keys in source).
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
