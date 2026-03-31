"""Google Maps: Distance Matrix, Directions, Places API (New) lookup."""

from __future__ import annotations

import re
from urllib.parse import quote, urlencode

import httpx

from tools.base import http_client, maps_api_key

# Distance Matrix + Directions (classic endpoints; enable both in Cloud Console)
DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"
DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

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
    query = normalize_place_search_query(query)

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


def _parse_latlon(value: str) -> tuple[float, float] | None:
    m = re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$", value or "")
    if not m:
        return None
    return float(m.group(1)), float(m.group(2))


def reverse_geocode_latlon(lat: float, lon: float) -> str | None:
    """Return a formatted street address for coordinates, or None if lookup fails.

    Uses the Geocoding API (same key as other Maps endpoints). Enable **Geocoding API**
    in Google Cloud if requests fail.
    """
    params = {"latlng": f"{lat},{lon}", "key": maps_api_key()}
    try:
        with http_client() as c:
            r = c.get(f"{GEOCODE_URL}?{urlencode(params)}")
            r.raise_for_status()
            data = r.json()
    except Exception:
        return None
    if data.get("status") != "OK":
        return None
    results = data.get("results") or []
    if not results:
        return None
    addr = results[0].get("formatted_address")
    return addr if isinstance(addr, str) and addr.strip() else None


def normalize_place_search_query(query: str) -> str:
    """Expand bare retail brands so Places searchText returns a real store near the user.

    Single-word queries like \"target\" often match nothing; \"Target store\" works with location bias.
    """
    q = (query or "").strip()
    if not q or _parse_latlon(q):
        return q
    key = re.sub(r"\s+", " ", q).strip().lower().rstrip(".")
    phrases = {
        "cold stone": "Cold Stone Creamery",
        "coldstone": "Cold Stone Creamery",
        "whole foods": "Whole Foods Market",
        "trader joes": "Trader Joe's",
        "trader joe's": "Trader Joe's",
    }
    if key in phrases:
        return phrases[key]
    if " " in key:
        return q
    if key in ("home", "work", "here"):
        return q
    single = {
        "target": "Target store",
        "walmart": "Walmart",
        "walgreens": "Walgreens",
        "cvs": "CVS Pharmacy",
        "costco": "Costco Wholesale",
        "kroger": "Kroger",
        "safeway": "Safeway",
        "aldi": "Aldi",
        "publix": "Publix",
        "chipotle": "Chipotle",
        "starbucks": "Starbucks",
        "ross": "Ross Dress for Less",
    }
    if key in single:
        return single[key]
    return q


def _maybe_normalize_endpoint(loc: str) -> str:
    s = (loc or "").strip()
    if not s or _parse_latlon(s):
        return s
    return normalize_place_search_query(s)


def _streets_block(origin_resolved: str, dest_resolved: str) -> str:
    """Machine-readable block so the agent copies full addresses into the user-facing itinerary."""
    return (
        "\n---\n"
        "STREET_ADDRESSES (required — paste these two lines into your reply to the user):\n"
        f"- Origin: {origin_resolved}\n"
        f"- Destination: {dest_resolved}\n"
    )


def get_place_address_impl(place_query: str, near_coordinates: str = "") -> str:
    """Resolve one free-text place to a formatted street address (Places searchText)."""
    place_query = (place_query or "").strip()
    if not place_query:
        return "get_place_address: empty place_query."
    bias: tuple[float, float] | None = None
    nc = (near_coordinates or "").strip()
    if nc:
        parsed = _parse_latlon(nc)
        if parsed:
            bias = parsed
    try:
        with http_client() as c:
            addr, err = _resolve_text_place_to_address(
                place_query, client=c, origin_bias=bias
            )
    except Exception as e:
        return f"get_place_address failed: {e}"
    if err:
        return f"get_place_address: {err}"
    if not addr:
        return (
            f"get_place_address: no result for {place_query!r}. "
            "Try chain + city + state (e.g. \"Target Austell GA\"). "
            "If Starting location is coordinates, pass them as near_coordinates."
        )
    return (
        f"Query: {place_query}\n"
        f"STREET_ADDRESS (required — paste into your itinerary): {addr}\n"
    )


def _resolve_text_place_to_address(
    query: str,
    *,
    client: httpx.Client,
    origin_bias: tuple[float, float] | None = None,
) -> tuple[str | None, str | None]:
    """Resolve a fuzzy place string to a concrete formatted address."""
    qn = normalize_place_search_query(query)
    body: dict = {"textQuery": qn}
    if origin_bias is not None:
        lat, lon = origin_bias
        body["locationBias"] = {
            "circle": {
                "center": {"latitude": lat, "longitude": lon},
                "radius": 25000.0,
            }
        }
    r = client.post(
        PLACES_SEARCH_TEXT_URL,
        headers=_places_v1_headers("places.formattedAddress,places.displayName"),
        json=body,
    )
    if r.status_code != 200:
        try:
            msg = r.json().get("error", {}).get("message", r.text)
        except Exception:
            msg = r.text
        return None, f"Places resolve error: HTTP {r.status_code} {msg}"
    places = r.json().get("places") or []
    if not places:
        return None, None
    p0 = places[0]
    return p0.get("formattedAddress"), None


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
    origin_in = _maybe_normalize_endpoint(origin)
    destination_in = _maybe_normalize_endpoint(destination)
    params = {
        "origins": origin_in,
        "destinations": destination_in,
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
        # Fallback: brand-only names (e.g. "Walmart") often fail in Distance Matrix.
        # Resolve via Places Search Text, then retry with concrete addresses.
        with http_client() as c:
            bias = _parse_latlon(origin_in)
            resolved_origin = origin_in
            resolved_dest = destination_in
            if bias is None:
                ro, err = _resolve_text_place_to_address(origin_in, client=c, origin_bias=None)
                if err:
                    return err
                if ro:
                    resolved_origin = ro
                    bias = _parse_latlon(resolved_origin)
            rd, err = _resolve_text_place_to_address(destination_in, client=c, origin_bias=bias)
            if err:
                return err
            if rd:
                resolved_dest = rd
            retry_params = {
                "origins": resolved_origin,
                "destinations": resolved_dest,
                "mode": mode,
                "units": "metric",
                "key": maps_api_key(),
            }
            rr = c.get(f"{DISTANCE_MATRIX_URL}?{urlencode(retry_params)}")
            rr.raise_for_status()
            retry = rr.json()
        if retry.get("status") != "OK":
            return f"Route element status: {es}"
        r_rows = retry.get("rows") or []
        if not r_rows or not (r_rows[0].get("elements") or []):
            return f"Route element status: {es}"
        r_el = r_rows[0]["elements"][0]
        if r_el.get("status") != "OK":
            return f"Route element status: {es}"
        dur = r_el.get("duration", {}).get("text", "?")
        dist = r_el.get("distance", {}).get("text", "?")
        oa = (retry.get("origin_addresses") or ["?"])[0]
        da = (retry.get("destination_addresses") or ["?"])[0]
        return (
            f"From «{origin_in}» to «{destination_in}» via {mode}: about {dur} ({dist}). "
            f"Resolved as: {oa} → {da}."
        ) + _streets_block(oa, da)
    dur = el.get("duration", {}).get("text", "?")
    dist = el.get("distance", {}).get("text", "?")
    oa = (data.get("origin_addresses") or ["?"])[0]
    da = (data.get("destination_addresses") or ["?"])[0]
    return (
        f"From «{origin}» to «{destination}» via {mode}: about {dur} ({dist}). "
        f"API origin/dest resolved as: {oa} → {da}."
    ) + _streets_block(oa, da)


def _strip_html_instructions(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html or "").strip()


def get_directions_impl(origin: str, destination: str, mode: str = "driving") -> str:
    """Directions API: duration, distance, and a short list of driving/walking steps."""
    mode = (mode or "driving").lower()
    allowed = {"driving", "walking", "bicycling", "transit"}
    if mode not in allowed:
        mode = "driving"
    origin_in = _maybe_normalize_endpoint(origin)
    destination_in = _maybe_normalize_endpoint(destination)
    params = {
        "origin": origin_in,
        "destination": destination_in,
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
        # Fallback for fuzzy/brand-only names by resolving to concrete addresses first.
        with http_client() as c:
            bias = _parse_latlon(origin_in)
            resolved_origin = origin_in
            resolved_dest = destination_in
            if bias is None:
                ro, err = _resolve_text_place_to_address(origin_in, client=c, origin_bias=None)
                if err:
                    return err
                if ro:
                    resolved_origin = ro
                    bias = _parse_latlon(resolved_origin)
            rd, err = _resolve_text_place_to_address(destination_in, client=c, origin_bias=bias)
            if err:
                return err
            if rd:
                resolved_dest = rd
            retry_params = {
                "origin": resolved_origin,
                "destination": resolved_dest,
                "mode": mode,
                "units": "metric",
                "key": maps_api_key(),
            }
            rr = c.get(f"{DIRECTIONS_URL}?{urlencode(retry_params)}")
            rr.raise_for_status()
            retry = rr.json()
        if retry.get("status") != "OK":
            return f"Directions error: {status} {data.get('error_message', '')}"
        data = retry
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
    body = "\n".join(lines)
    return body + _streets_block(start, end)
