"""Sentence-transformer embeddings (lazy-loaded model)."""

from __future__ import annotations

from functools import lru_cache
from typing import Sequence


@lru_cache(maxsize=4)
def _model(model_name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def embed_texts(texts: Sequence[str], *, model_name: str) -> list[list[float]]:
    """Return one embedding vector per input string."""
    if not texts:
        return []
    model = _model(model_name)
    vectors = model.encode(
        list(texts),
        convert_to_numpy=True,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return [v.tolist() for v in vectors]
