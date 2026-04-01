"""Load project .env before tests (API keys, etc.)."""

import os

# Avoid writing MLflow runs during unit tests unless explicitly enabled.
os.environ.setdefault("MLFLOW_ENABLED", "false")

import configs.settings  # noqa: F401
