"""Print where Chroma data is stored and what collections exist (no secrets printed)."""

from __future__ import annotations

import argparse

from configs.settings import (
    CHROMA_DATABASE,
    CHROMA_DATABASE_DEFAULT,
    CHROMA_TENANT,
    RAG_CHROMA_DIR,
    RAG_COLLECTION,
    RAG_KIND_GENERAL,
    RAG_KIND_USER,
)
from rag.retriever import (
    chroma_connection_mode,
    get_collection,
    list_collection_names,
    reset_client_cache,
)


def main() -> None:
    p = argparse.ArgumentParser(description="Diagnose Chroma RAG connection")
    p.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear cached Chroma client before checking (use after editing .env)",
    )
    args = p.parse_args()
    if args.clear_cache:
        reset_client_cache()

    # Re-import settings after potential env changes in same shell
    from configs import settings as cfg

    key_set = bool(cfg.CHROMA_API_KEY)
    mode = chroma_connection_mode()

    print("=== Errand Sequencer — Chroma RAG diagnose ===\n")
    print(f"Connection mode: {mode}")
    print(f"CHROMA_API_KEY present: {key_set}" + (f" (length {len(cfg.CHROMA_API_KEY)})" if key_set else ""))
    eff_db = CHROMA_DATABASE or CHROMA_DATABASE_DEFAULT
    print(f"CHROMA_TENANT: {CHROMA_TENANT or '(not set — Cloud may fail)'}")
    print(f"CHROMA_DATABASE: {CHROMA_DATABASE or f'(using default {CHROMA_DATABASE_DEFAULT})'}")
    print(f"Effective Cloud database: {eff_db}")
    if key_set and CHROMA_TENANT:
        print("Cloud mode: tenant + database (database defaults to errand_rag if unset).")
    if mode == "local_persistent":
        print(f"Local data directory: {RAG_CHROMA_DIR.resolve()}")
        print("\nIf you expected Chroma Cloud: add CHROMA_API_KEY to errand-sequencer/.env")
        print("and run: python -m rag.ingest --reset")
    else:
        print("\nChroma Cloud: open https://www.trychroma.com/ → your org → pick the")
        print("Database that matches CHROMA_DATABASE (or the default for your API key).")
        print("Collections live *inside* that database — look for collection name below.")

    print(f"\nTarget collection name: {RAG_COLLECTION}")
    try:
        col = get_collection()
        n = col.count()
        print(f"Collection '{col.name}' document/chunk count: {n}")
        try:
            n_general = len((col.get(where={"kind": RAG_KIND_GENERAL}, include=[]) or {}).get("ids") or [])
            n_user = len((col.get(where={"kind": RAG_KIND_USER}, include=[]) or {}).get("ids") or [])
            print(f"  by metadata kind: general={n_general}  user={n_user}  (remainder may lack kind — re-ingest)")
        except Exception as ex:
            print(f"  (could not count by kind: {ex})")
    except Exception as e:
        print(f"Could not open collection: {e}")

    try:
        names = list_collection_names()
        print(f"Collections visible to this client: {names or '(none)'}")
    except Exception as e:
        print(f"Could not list collections: {e}")

    print("\n=== end ===")


if __name__ == "__main__":
    main()
