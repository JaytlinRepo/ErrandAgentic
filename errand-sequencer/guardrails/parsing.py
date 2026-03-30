"""Errand text parsing: list lines vs preference notes."""

from __future__ import annotations

import re


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
    return lines


def wants_eat_last(errands: str) -> bool:
    t = (errands or "").lower()
    return "eat last" in t or "food last" in t
