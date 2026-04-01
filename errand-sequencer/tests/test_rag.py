"""Tests for RAG chunking and (optional) Chroma ingest."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest

from rag.chunker import chunk_text


def run_chroma_cloud_smoke() -> None:
    """Same client path as Streamlit + ingest; run: ``python tests/test_rag.py`` from errand-sequencer."""
    from configs.settings import CHROMA_USE_CLOUD, RAG_COLLECTION
    from rag.retriever import get_collection, reset_client_cache, retrieve_context

    print("=== Chroma smoke (via rag.retriever) ===\n")
    if not CHROMA_USE_CLOUD:
        print("CHROMA_USE_CLOUD is False. Set CHROMA_MODE=cloud and credentials in .env")
        raise SystemExit(1)
    reset_client_cache()
    col = get_collection()
    n = col.count()
    print(f"Connected successfully")
    print(f"Collection: {RAG_COLLECTION}")
    print(f"Total chunks: {n}\n")
    q = "Costco on a Saturday morning"
    ctx = retrieve_context(q)
    print(f"Test query: {q!r}")
    print(f"retrieve_context length: {len(ctx)} chars\n")
    for i, para in enumerate(ctx.split("\n\n")[:3], start=1):
        print(f"  [{i}] {para[:220].replace(chr(10), ' ')}...")
    if not ctx.strip():
        print("(empty — run: python rag/ingest.py --reset)")
        raise SystemExit(1)


def test_chunker_splits_paragraphs():
    text = "A\n\nB\n\n" + "x" * 800
    chunks = chunk_text(text, source="test.md", max_chars=300, overlap=50)
    assert len(chunks) >= 2
    assert all(c.source == "test.md" for c in chunks)


@pytest.mark.skipif(
    os.getenv("CHROMA_CLOUD_CHECK") != "1",
    reason="Set CHROMA_CLOUD_CHECK=1 for Chroma Cloud smoke (needs CHROMA_MODE=cloud + .env)",
)
def test_chroma_cloud_connection_and_retrieval():
    from configs.settings import CHROMA_USE_CLOUD
    from rag.retriever import reset_client_cache, get_collection, retrieve_context

    assert CHROMA_USE_CLOUD, "Set CHROMA_MODE=cloud"
    reset_client_cache()
    assert get_collection().count() > 0
    assert len(retrieve_context("Costco on a Saturday morning")) > 20


@pytest.mark.skipif(
    os.getenv("RAG_INTEGRATION") != "1",
    reason="Set RAG_INTEGRATION=1 to run ingest/retrieve against real Chroma + embeddings",
)
def test_ingest_and_retrieve_smoke():
    from pathlib import Path

    from configs.settings import RAG_RAW_DIR
    from rag.ingest import ingest_raw_dir
    from rag.retriever import reset_collection, retrieve_context

    reset_collection()
    n = ingest_raw_dir(Path(RAG_RAW_DIR), reset=True)
    assert n > 0
    ctx = retrieve_context("parking tips busy grocery store saturday")
    assert len(ctx) > 20


if __name__ == "__main__":
    run_chroma_cloud_smoke()
