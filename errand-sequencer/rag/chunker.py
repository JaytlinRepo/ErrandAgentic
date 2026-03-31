"""Split documents into overlapping chunks for embedding."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    text: str
    source: str
    chunk_index: int


def _normalize(text: str) -> str:
    t = text.replace("\r\n", "\n").strip()
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t


def _split_oversized(text: str, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    out: list[str] = []
    start = 0
    step = max(1, max_chars - overlap)
    while start < len(text):
        piece = text[start : start + max_chars]
        out.append(piece.strip())
        start += step
    return [p for p in out if p]


def chunk_text(
    text: str,
    *,
    source: str,
    max_chars: int = 600,
    overlap: int = 120,
) -> list[TextChunk]:
    """Split on paragraphs first, then merge/split to stay near max_chars with overlap."""
    text = _normalize(text)
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    buf: list[str] = []
    buf_len = 0

    def flush() -> None:
        nonlocal buf, buf_len
        if buf:
            merged = "\n\n".join(buf)
            for piece in _split_oversized(merged, max_chars, overlap):
                chunks.append(piece)
            buf = []
            buf_len = 0

    for p in paragraphs:
        if buf_len + len(p) + 2 <= max_chars:
            buf.append(p)
            buf_len += len(p) + 2
        else:
            flush()
            if len(p) <= max_chars:
                buf = [p]
                buf_len = len(p)
            else:
                for piece in _split_oversized(p, max_chars, overlap):
                    chunks.append(piece)
    flush()

    return [TextChunk(text=c, source=source, chunk_index=i) for i, c in enumerate(chunks)]


def chunk_file(path: str, *, max_chars: int, overlap: int) -> list[TextChunk]:
    from pathlib import Path

    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    return chunk_text(raw, source=str(p.name), max_chars=max_chars, overlap=overlap)
