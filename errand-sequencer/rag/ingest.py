"""Chunk raw markdown, embed, and persist to ChromaDB."""

from __future__ import annotations

import argparse
from pathlib import Path

from configs.settings import (
    RAG_CHUNK_OVERLAP,
    RAG_CHUNK_SIZE,
    RAG_COLLECTION,
    RAG_EMBEDDING_MODEL,
    RAG_KIND_GENERAL,
    RAG_RAW_DIR,
)
from rag.chunker import chunk_file
from rag.embedder import embed_texts
from rag.retriever import (
    chroma_connection_mode,
    get_collection,
    reset_client_cache,
    reset_collection,
    stable_chunk_id,
)


def ingest_raw_dir(
    raw_dir: Path | None = None,
    *,
    pattern: str = "**/*.md",
    reset: bool = False,
) -> int:
    raw_dir = raw_dir or RAG_RAW_DIR
    paths = sorted(raw_dir.glob(pattern))
    if not paths:
        return 0

    reset_client_cache()
    if reset:
        reset_collection()
    mode = chroma_connection_mode()
    if mode == "chroma_cloud":
        print("Ingest target: Chroma Cloud (CHROMA_API_KEY is set).")
    else:
        print(f"Ingest target: local persistent Chroma at {RAG_CHROMA_DIR.resolve()}")
    col = get_collection()

    all_chunks: list = []
    for path in paths:
        all_chunks.extend(
            chunk_file(
                str(path),
                max_chars=RAG_CHUNK_SIZE,
                overlap=RAG_CHUNK_OVERLAP,
            )
        )
    if not all_chunks:
        return 0

    ids = [stable_chunk_id(c.source, c.chunk_index, c.text) for c in all_chunks]
    texts = [c.text for c in all_chunks]
    metadatas: list[dict[str, str | int]] = [
        {"kind": RAG_KIND_GENERAL, "source": c.source, "chunk_index": c.chunk_index}
        for c in all_chunks
    ]
    embs = embed_texts(texts, model_name=RAG_EMBEDDING_MODEL)

    # Upsert in batches for large corpora
    batch = 64
    for i in range(0, len(ids), batch):
        col.upsert(
            ids=ids[i : i + batch],
            embeddings=embs[i : i + batch],
            documents=texts[i : i + batch],
            metadatas=metadatas[i : i + batch],
        )
    return len(ids)


def main() -> None:
    p = argparse.ArgumentParser(description="Ingest markdown into Chroma for RAG")
    p.add_argument("--raw-dir", type=Path, default=None)
    p.add_argument("--reset", action="store_true", help="Clear collection before ingest")
    args = p.parse_args()
    n = ingest_raw_dir(args.raw_dir, reset=args.reset)
    print(f"Ingested {n} chunks into collection '{RAG_COLLECTION}'.")


if __name__ == "__main__":
    main()
