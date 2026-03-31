"""Append Places-resolved street addresses for errand stops (does not rely on the LLM)."""

from __future__ import annotations

import re

from guardrails.parsing import split_paragraph_into_errands
from tools.maps import get_place_address_impl, normalize_place_search_query


def _coord_hint_for_bias(starting_location_note: str | None) -> str:
    n = (starting_location_note or "").strip()
    if re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$", n):
        return n
    return ""


def _is_home_line(line: str) -> bool:
    t = line.strip().lower()
    t = re.sub(r"^(then|and|to|go|back)\s+", "", t).strip()
    if t in ("home", "here", "my home", "go home", "return home", "back home"):
        return True
    if re.fullmatch(r".{0,50}\bhome\b", t):
        return True
    return False


def _strip_leading_prose(s: str) -> str:
    s = s.strip()
    s = re.sub(
        r"^\s*(i\s+need\s+to\s+go\s+to|need\s+to\s+go\s+to|go\s+to)\s+",
        "",
        s,
        flags=re.I,
    )
    return s.strip()


def _to_place_query(line: str) -> str:
    s = _strip_leading_prose(line)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s+in\s+", " ", s, flags=re.I)
    return normalize_place_search_query(s)


def _expand_lines_for_addresses(lines: list[str]) -> list[str]:
    """Reuse the same paragraph split as extract_errand_lines (incl. ... and home)."""
    if len(lines) != 1:
        return lines
    one = lines[0].strip()
    if len(one) < 12:
        return lines

    expanded = split_paragraph_into_errands(one)
    if len(expanded) > 1:
        return [x.strip() for x in expanded if x.strip()]
    return lines


def _bullet_label(raw: str) -> str:
    s = _strip_leading_prose(raw)
    return s if s else raw.strip()


def _extract_street_from_tool_out(text: str) -> str:
    m = re.search(r"STREET_ADDRESS.*?:\s*(.+?)(?:\n|$)", text, re.IGNORECASE | re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


def append_resolved_stop_addresses(
    reply: str,
    errand_lines: list[str],
    *,
    starting_location_note: str | None,
    display_location: str | None,
    cache: dict[str, str] | None = None,
) -> str:
    """Append a markdown block with one resolved address per non-home errand line."""
    lines = _expand_lines_for_addresses(list(errand_lines or []))
    if not lines:
        return reply

    near = _coord_hint_for_bias(starting_location_note)
    cache = cache if cache is not None else {}
    bullets: list[str] = []

    for raw in lines:
        if _is_home_line(raw):
            home_txt = (display_location or "").strip() or (starting_location_note or "").strip()
            if home_txt:
                bullets.append(f"- **Home:** {home_txt}")
            continue

        q = _to_place_query(raw)
        if not q:
            continue
        label = _bullet_label(raw)
        ck = f"{near}|{q}"
        if ck in cache:
            addr = cache[ck]
        else:
            try:
                out = get_place_address_impl(q, near)
            except Exception as e:
                bullets.append(f"- **{label}:** *(address lookup failed: {e})*")
                continue
            if "STREET_ADDRESS" not in out:
                bullets.append(
                    f"- **{label}:** *(could not resolve — try a more specific name + city)*"
                )
                continue
            addr = _extract_street_from_tool_out(out)
            cache[ck] = addr
        bullets.append(f"- **{label}:** {addr}")

    if not bullets:
        return reply

    block = "\n\n---\n**Resolved stop addresses**\n" + "\n".join(bullets)
    return reply.rstrip() + block
