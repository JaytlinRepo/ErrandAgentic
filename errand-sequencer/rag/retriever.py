"""ChromaDB retrieval for errand knowledge (local persistent or Chroma Cloud)."""

from __future__ import annotations

import hashlib
import os
from functools import lru_cache

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from configs.settings import (
    CHROMA_API_KEY,
    CHROMA_DATABASE,
    CHROMA_DATABASE_DEFAULT,
    CHROMA_TENANT,
    RAG_CHROMA_DIR,
    RAG_COLLECTION,
    RAG_EMBEDDING_MODEL,
    RAG_KIND_GENERAL,
    RAG_KIND_USER,
    RAG_TOP_K,
)
from configs.ml_tracker import get_mlflow_tracker
from rag.embedder import embed_texts


def _make_cloud_client() -> ClientAPI:
    """Connect to Chroma Cloud with explicit tenant + database (required by Chroma Cloud)."""
    assert CHROMA_API_KEY
    # Cloud always needs a database name; default matches `python -m rag.ensure_chroma_database`.
    db = CHROMA_DATABASE or CHROMA_DATABASE_DEFAULT
    if CHROMA_TENANT:
        return chromadb.CloudClient(
            api_key=CHROMA_API_KEY,
            tenant=CHROMA_TENANT,
            database=db,
        )
    saved: dict[str, str] = {}
    for key in ("CHROMA_TENANT", "CHROMA_DATABASE"):
        if key in os.environ:
            saved[key] = os.environ.pop(key)
    try:
        return chromadb.CloudClient(api_key=CHROMA_API_KEY)
    finally:
        for k, v in saved.items():
            os.environ[k] = v


@lru_cache(maxsize=1)
def _client() -> ClientAPI:
    """Single shared client: Chroma Cloud if CHROMA_API_KEY is set, else local persistent."""
    if CHROMA_API_KEY:
        return _make_cloud_client()
    RAG_CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(RAG_CHROMA_DIR))


def reset_client_cache() -> None:
    """Clear cached client (e.g. after changing CHROMA_* env vars in the same process)."""
    _client.cache_clear()


def chroma_connection_mode() -> str:
    """Human-readable label for diagnostics."""
    return "chroma_cloud" if CHROMA_API_KEY else "local_persistent"


def list_collection_names() -> list[str]:
    return [c.name for c in _client().list_collections()]


def get_collection() -> Collection:
    return _client().get_or_create_collection(
        name=RAG_COLLECTION,
        metadata={"description": "Errand sequencing knowledge (RAG)"},
    )


def reset_collection() -> None:
    """Remove the collection entirely (used before full re-ingest)."""
    c = _client()
    try:
        c.delete_collection(RAG_COLLECTION)
    except Exception:
        pass


def retrieve_context(query: str, *, top_k: int | None = None) -> str:
    """Return formatted excerpts from curated knowledge (kind=general), or empty if none."""
    return _retrieve_by_kind(
        query,
        kind=RAG_KIND_GENERAL,
        top_k=top_k,
        source_label="source",
    )


def retrieve_user_memory(query: str, user_id: str, *, top_k: int | None = None) -> str:
    """Return formatted excerpts for this user only (kind=user). Empty if none."""
    user_id = (user_id or "").strip()
    if not user_id:
        return ""
    return _retrieve_by_kind(
        query,
        kind=RAG_KIND_USER,
        top_k=top_k,
        source_label="user_id",
        extra_where={"user_id": user_id},
        show_source_line=False,
    )


def _retrieve_by_kind(
    query: str,
    *,
    kind: str,
    top_k: int | None,
    source_label: str,
    extra_where: dict[str, str] | None = None,
    show_source_line: bool = True,
) -> str:
    query = (query or "").strip()
    if not query:
        return ""
    k = top_k if top_k is not None else RAG_TOP_K
    col = get_collection()
    where: dict = {"kind": kind}
    if extra_where:
        where = {"$and": [{"kind": kind}, extra_where]}
    probe = col.get(where=where, limit=1, include=[])
    if not (probe.get("ids") or []):
        return ""
    emb = embed_texts([query], model_name=RAG_EMBEDDING_MODEL)[0]
    res = col.query(
        query_embeddings=[emb],
        n_results=k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    if not docs:
        return ""
    lines: list[str] = []
    for i, doc in enumerate(docs, start=1):
        meta = metas[i - 1] if i - 1 < len(metas) else {}
        if show_source_line:
            src = (meta or {}).get(source_label, "?")
            lines.append(f"[{i}] ({source_label}: {src})\n{doc.strip()}")
        else:
            lines.append(f"[{i}]\n{doc.strip()}")
    distances = (res.get("distances") or [[]])[0]
    scores: list[float] | None = None
    if distances:
        scores = [1.0 / (1.0 + float(d)) for d in distances]
    get_mlflow_tracker().log_rag_retrieval(
        query=query,
        chunks_retrieved=list(docs),
        scores=scores,
    )
    return "\n\n".join(lines)


def upsert_user_memory_texts(
    texts: list[str],
    user_id: str,
    *,
    model_name: str | None = None,
) -> int:
    """Embed and store user-specific insights (kind=user). Returns number of chunks stored."""
    user_id = (user_id or "").strip()
    if not user_id:
        return 0
    cleaned = [t.strip() for t in texts if t and str(t).strip()]
    if not cleaned:
        return 0
    model = model_name or RAG_EMBEDDING_MODEL
    col = get_collection()
    ids = [stable_user_memory_id(user_id, i, t) for i, t in enumerate(cleaned)]
    metadatas: list[dict[str, str | int]] = [
        {"kind": RAG_KIND_USER, "user_id": user_id, "chunk_index": i}
        for i in range(len(cleaned))
    ]
    embs = embed_texts(cleaned, model_name=model)
    batch = 64
    for i in range(0, len(ids), batch):
        col.upsert(
            ids=ids[i : i + batch],
            embeddings=embs[i : i + batch],
            documents=cleaned[i : i + batch],
            metadatas=metadatas[i : i + batch],
        )
    return len(ids)


def stable_chunk_id(source: str, chunk_index: int, text: str) -> str:
    h = hashlib.sha256(f"{source}:{chunk_index}:{text}".encode()).hexdigest()[:24]
    return f"{source}:{chunk_index}:{h}"


def stable_user_memory_id(user_id: str, chunk_index: int, text: str) -> str:
    uid = hashlib.sha256(user_id.encode()).hexdigest()[:12]
    h = hashlib.sha256(f"{user_id}:{chunk_index}:{text}".encode()).hexdigest()[:24]
    return f"um:{uid}:{chunk_index}:{h}"
