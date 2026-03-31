"""Stable anonymous user id for persisted memory (same machine, same checkout)."""

from __future__ import annotations

import uuid

from configs.settings import RUNTIME_DIR


def get_or_create_user_id() -> str:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    path = RUNTIME_DIR / "user_id.txt"
    if path.exists():
        uid = path.read_text(encoding="utf-8").strip()
        if uid:
            return uid
    uid = str(uuid.uuid4())
    path.write_text(uid, encoding="utf-8")
    return uid
