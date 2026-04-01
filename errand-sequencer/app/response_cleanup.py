"""Post-processing helpers for assistant output formatting."""

from __future__ import annotations

import re


_RELATIVE_NOW_RE = re.compile(
    r"\bnow\s*\+\s*\d+\s*minutes?(?:\s*\+\s*\d+\s*minutes?)*\b",
    flags=re.IGNORECASE,
)

_BOILERPLATE_PATTERNS = [
    re.compile(
        r"This order follows the planned stop order and avoids duplicating stops\..*?current local time at request\.\s*",
        flags=re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"Note that this route assumes the user will be leaving from their starting location.*?(?:please let me know!|additional assistance, please let me know!?)\s*",
        flags=re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"Based on the provided information and tool outputs, here is a suggested route for the user:\s*",
        flags=re.IGNORECASE,
    ),
]

_ROUTE_NOISE_PATTERNS = [
    re.compile(
        r"Since the first leg is from Current Location[\s\S]*?(?=(?:\n---|\n\*\*Resolved stop addresses\*\*|$))",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\n{0,2}Addresses:\s*[\s\S]*?(?=(?:\n---|\n\*\*Resolved stop addresses\*\*|$))",
        flags=re.IGNORECASE,
    ),
]


def strip_relative_now_phrases(text: str) -> str:
    """Clean noisy assistant phrasing and improve readability."""
    if not text:
        return text
    out = _RELATIVE_NOW_RE.sub("", text)
    for pat in _BOILERPLATE_PATTERNS:
        out = pat.sub("", out)
    for pat in _ROUTE_NOISE_PATTERNS:
        out = pat.sub("", out)
    # Break run-on numbered itineraries into separate lines.
    out = re.sub(r"(?<!\n)\s*([1-9]\d*\.)\s+", r"\n\1 ", out)
    # Normalize inline bullet delimiters.
    out = re.sub(r"\s+•\s+", "\n- ", out)
    # Normalize "Addresses:" section to a block.
    out = re.sub(r"\bAddresses:\s*", "\n\nAddresses:\n", out, flags=re.IGNORECASE)
    # Remove dangling ETA labels after relative-time stripping.
    out = re.sub(r"\bETA:[ \t]*(?=(?:\n|$|Addresses:|---|[1-9]\d*\.))", "", out)
    # Remove accidental repeated separators between duplicated address sections.
    out = re.sub(
        r"(?:---\s*\*\*Resolved stop addresses\*\*\s*){2,}",
        "---\n**Resolved stop addresses**\n",
        out,
        flags=re.IGNORECASE,
    )
    out = re.sub(r"\(\s*\)", "", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"[ \t]+\n", "\n", out)
    out = out.strip()
    return out or "Suggested route updated."

