"""Google Maps: Distance Matrix, Directions, Places API (New) lookup."""

from __future__ import annotations

import re
from urllib.parse import quote, urlencode

import httpx

from tools.base import http_client, maps_api_key

# Distance Matrix + Directions (classic endpoints; enable both in Cloud Console)
DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"
DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"

# Places API (New) — use when legacy Places is disabled on the GCP project
PLACES_SEARCH_TEXT_URL = "https://places.googleapis.com/v1/places:searchText"


def _places_v1_headers(field_mask: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": maps_api_key(),
        "X-Goog-FieldMask": field_mask,
    }


def find_place_id(
    query: str, *, client: httpx.Client | None = None
) -> tuple[str | None, str | None, str | None]:
    """Resolve free text to (place_id, display_name, error) using Places API (New)."""
    query = (query or "").strip()
    if not query:
        return None, None, None

    own_client = client is None
    c = client or http_client()
    try:
        r = c.post(
            PLACES_SEARCH_TEXT_URL,
            headers=_places_v1_headers("places.id,places.displayName"),
            json={"textQuery": query},
        )
        if r.status_code != 200:
            try:
                body = r.json()
                msg = body.get("error", {}).get("message", r.text)
            except Exception:
                msg = r.text
            return None, None, f"Places (New) error: HTTP {r.status_code} {msg}"

        data = r.json()
        places = data.get("places") or []
        if not places:
            return None, None, None
        p0 = places[0]
        pid = p0.get("id")
        dn = (p0.get("displayName") or {}).get("text")
        return pid, dn, None
    finally:
        if own_client:
            c.close()


def place_details_v1(
    place_id: str, *, client: httpx.Client
) -> tuple[dict | None, str | None]:
    """GET Place details (New). Returns (detail_json, error_message)."""
    place_id = place_id.removeprefix("places/")
    # Path segment must be percent-encoded
    url = f"https://places.googleapis.com/v1/places/{quote(place_id, safe='')}"
    r = client.get(
        url,
        headers=_places_v1_headers(
            "id,displayName,formattedAddress,regularOpeningHours,"
            "currentOpeningHours,businessStatus"
        ),
    )
    if r.status_code != 200:
        try:
            msg = r.json().get("error", {}).get("message", r.text)
        except Exception:
            msg = r.text
        return None, f"Place Details (New) error: HTTP {r.status_code} {msg}"
    return r.json(), None


def get_travel_time_impl(origin: str, destination: str, mode: str = "driving") -> str:
    """Distance Matrix: duration and distance between two locations."""
    mode = (mode or "driving").lower()
    allowed = {"driving", "walking", "bicycling", "transit"}
    if mode not in allowed:
        mode = "driving"
    params = {
        "origins": origin,
        "destinations": destination,
        "mode": mode,
        "units": "metric",
        "key": maps_api_key(),
    }
    with http_client() as c:
        r = c.get(f"{DISTANCE_MATRIX_URL}?{urlencode(params)}")
        r.raise_for_status()
        data = r.json()
    status = data.get("status")
    if status != "OK":
        return f"Distance Matrix error: {status} {data.get('error_message', '')}"
    rows = data.get("rows") or []
    if not rows:
        return "No route rows returned."
    elems = rows[0].get("elements") or []
    if not elems:
        return "No route elements returned."
    el = elems[0]
    es = el.get("status")
    if es != "OK":
        return f"Route element status: {es}"
    dur = el.get("duration", {}).get("text", "?")
    dist = el.get("distance", {}).get("text", "?")
    return (
        f"From «{origin}» to «{destination}» via {mode}: about {dur} ({dist}). "
        f"API origin/dest resolved as: {data.get('origin_addresses', ['?'])[0]} → "
        f"{data.get('destination_addresses', ['?'])[0]}."
    )


def _strip_html_instructions(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html or "").strip()


def get_directions_impl(origin: str, destination: str, mode: str = "driving") -> str:
    """Directions API: duration, distance, and a short list of driving/walking steps."""
    mode = (mode or "driving").lower()
    allowed = {"driving", "walking", "bicycling", "transit"}
    if mode not in allowed:
        mode = "driving"
    params = {
        "origin": origin,
        "destination": destination,
        "mode": mode,
        "units": "metric",
        "key": maps_api_key(),
    }
    with http_client() as c:
        r = c.get(f"{DIRECTIONS_URL}?{urlencode(params)}")
        r.raise_for_status()
        data = r.json()
    status = data.get("status")
    if status != "OK":
        return f"Directions error: {status} {data.get('error_message', '')}"
    routes = data.get("routes") or []
    if not routes:
        return "No routes returned."
    legs = routes[0].get("legs") or []
    if not legs:
        return "No route legs returned."
    leg = legs[0]
    dur = leg.get("duration", {}).get("text", "?")
    dist = leg.get("distance", {}).get("text", "?")
    start = leg.get("start_address", "?")
    end = leg.get("end_address", "?")
    steps = leg.get("steps") or []
    lines = [
        f"Route via {mode}: {dur}, {dist}",
        f"{start} → {end}",
        "Key steps:",
    ]
    for step in steps[:6]:
        txt = _strip_html_instructions(step.get("html_instructions", ""))
        if txt:
            lines.append(f"  • {txt}")
    if len(steps) > 6:
        lines.append(f"  • … plus {len(steps) - 6} more steps")
    return "\n".join(lines)
