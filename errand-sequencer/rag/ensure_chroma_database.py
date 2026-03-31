"""Create Chroma Cloud database if missing (REST). Run once per tenant."""

from __future__ import annotations

import argparse
import sys

import httpx

from configs.settings import (
    CHROMA_API_KEY,
    CHROMA_DATABASE_DEFAULT,
    CHROMA_TENANT,
)

CLOUD_API = "https://api.trychroma.com/api/v2"


def ensure_database(name: str | None = None) -> int:
    if not CHROMA_API_KEY or not CHROMA_TENANT:
        print("Set CHROMA_API_KEY and CHROMA_TENANT in .env", file=sys.stderr)
        return 1
    name = name or CHROMA_DATABASE_DEFAULT
    h = {"X-Chroma-Token": CHROMA_API_KEY, "Content-Type": "application/json"}
    list_url = f"{CLOUD_API}/tenants/{CHROMA_TENANT}/databases"
    r = httpx.get(list_url, headers=h, timeout=30)
    r.raise_for_status()
    existing = {d["name"] for d in r.json()}
    if name in existing:
        print(f"Database already exists: {name}")
        return 0
    cr = httpx.post(list_url, headers=h, json={"name": name}, timeout=30)
    cr.raise_for_status()
    print(f"Created database: {name}")
    return 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--name", default=None, help="Database name (default: CHROMA_DATABASE_DEFAULT)")
    args = p.parse_args()
    raise SystemExit(ensure_database(args.name))


if __name__ == "__main__":
    main()
