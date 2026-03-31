"""Tests for RAG chunking and (optional) Chroma ingest."""

from __future__ import annotations

import os

import pytest

from rag.chunker import chunk_text


def test_chunker_splits_paragraphs():
    text = "A\n\nB\n\n" + "x" * 800
    chunks = chunk_text(text, source="test.md", max_chars=300, overlap=50)
    assert len(chunks) >= 2
    assert all(c.source == "test.md" for c in chunks)


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
