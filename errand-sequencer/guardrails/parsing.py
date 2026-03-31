"""Errand text parsing: list lines vs preference notes."""

from __future__ import annotations

import re


def split_paragraph_into_errands(text: str) -> list[str]:
    """Split a single prose block into multiple stops (paragraph / sentence style).

    Handles semicolons, \"then\" chains, Oxford-comma lists (\", and \"), and
    multi-sentence paragraphs. Does not split short single-line errands.
    """
    s = " ".join((text or "").split())
    if not s:
        return []

    # 1) Explicit legs separated by semicolons
    if ";" in s:
        parts = [p.strip().strip(".;") for p in s.split(";") if p.strip()]
        if len(parts) > 1:
            return parts

    # 2) "… then …" / "… and then …"
    for pat in (r"\s+then\s+", r"\s+and\s+then\s+", r"\s+after\s+that\s*,?\s+"):
        if re.search(pat, s, flags=re.I):
            parts = re.split(pat, s, flags=re.I)
            parts = [p.strip().strip(".;") for p in parts if p.strip()]
            if len(parts) > 1:
                return parts

    # 3) Oxford comma: "A, B, and C"
    if re.search(r",\s+and\s+", s, flags=re.I):
        head, tail = re.split(r",\s+and\s+", s, maxsplit=1, flags=re.I)
        left_items = [p.strip() for p in head.split(",") if p.strip()]
        t = tail.strip()
        if left_items and t:
            return left_items + [t]

    # 4) Plain comma-separated (3+ segments), e.g. "USPS, Target, Whole Foods"
    if s.count(",") >= 2:
        parts = [p.strip() for p in s.split(",") if p.strip()]
        if len(parts) >= 3:
            return parts

    # 5) Multiple sentences as separate stops
    sents = re.split(r"(?<=[.!?])\s+", s)
    if len(sents) >= 2:
        out = [x.strip() for x in sents if len(x.strip()) > 5]
        if len(out) >= 2:
            return out

    return [s]


def _should_expand_paragraph_line(line: str) -> bool:
    line = line.strip()
    if len(line) < 24:
        return False
    if ";" in line:
        return True
    if re.search(r"\s+then\s+|\s+and\s+then\s+", line, flags=re.I):
        return True
    if re.search(r",\s+and\s+", line, flags=re.I):
        return True
    if line.count(",") >= 2:
        return True
    if len(re.findall(r"[.!?]", line)) >= 2:
        return True
    return False


def extract_errand_lines(errands: str) -> list[str]:
    lines: list[str] = []
    for raw in (errands or "").splitlines():
        line = raw.strip()
        if not line:
            # Treat first blank line as boundary between errands and extra notes/preferences.
            if lines:
                break
            continue
        # Trim common list prefixes ("- item", "1. item")
        line = re.sub(r"^\s*[-*]\s+", "", line)
        line = re.sub(r"^\s*\d+\.\s+", "", line)
        if not line:
            continue
        lower = line.lower()
        # Ignore preference/instruction lines that are not actual places.
        if any(
            marker in lower
            for marker in (
                "i would like",
                "prefer",
                "preference:",
                "eat last",
                "food last",
            )
        ):
            continue
        if line:
            lines.append(line)

    # One long prose line → split into stops (paragraph-style input)
    if len(lines) == 1 and _should_expand_paragraph_line(lines[0]):
        expanded = split_paragraph_into_errands(lines[0])
        if len(expanded) > 1:
            return expanded

    return lines


def wants_eat_last(errands: str) -> bool:
    t = (errands or "").lower()
    return "eat last" in t or "food last" in t
