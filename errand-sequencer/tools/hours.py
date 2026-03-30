"""Business / place opening hours via Places API (New)."""

from __future__ import annotations

from tools.base import http_client
from tools.maps import find_place_id, place_details_v1


def get_hours_impl(place_query: str) -> str:
    """Fetch human-readable opening hours for a place name or address."""
    place_query = (place_query or "").strip()
    if not place_query:
        return "No place name provided."

    with http_client() as c:
        place_id, _name, err = find_place_id(place_query, client=c)
        if err:
            return err
        if not place_id:
            return f"Could not find a place matching «{place_query}»."

        result, err = place_details_v1(place_id, client=c)
        if err:
            return err
        if not result:
            return "No details returned for that place."

    name = (result.get("displayName") or {}).get("text", place_query)
    addr = result.get("formattedAddress", "")
    biz = result.get("businessStatus", "")
    lines = [f"{name}", f"Address: {addr}" if addr else ""]
    if biz:
        lines.append(f"Status: {biz}")

    roh = result.get("regularOpeningHours") or {}
    weekday_text = roh.get("weekdayDescriptions")
    if weekday_text:
        lines.append("Weekly hours:")
        lines.extend(f"  • {t}" for t in weekday_text)
    else:
        lines.append("No structured opening hours in Google (may be 24h, residential, or data missing).")

    curr = result.get("currentOpeningHours") or {}
    # New API may expose openNow on regularOpeningHours or currentOpeningHours
    open_now = curr.get("openNow")
    if open_now is None:
        open_now = roh.get("openNow")
    if open_now is True:
        lines.append("Currently: open (per Google).")
    elif open_now is False:
        lines.append("Currently: closed (per Google).")

    return "\n".join(line for line in lines if line)
