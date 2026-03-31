"""LangChain tool definitions wrapping Maps and weather backends."""

from __future__ import annotations

from langchain_core.tools import tool

from tools.hours import get_hours_impl
from tools.maps import (
    get_directions_impl,
    get_place_address_impl,
    get_travel_time_impl,
)
from tools.weather import get_weather_impl


@tool
def get_travel_time(origin: str, destination: str, mode: str = "driving") -> str:
    """Estimate travel time and distance using Google Distance Matrix (fast matrix lookup).

    Prefer this for comparing legs or quick duration checks. For turn-by-turn outline use get_directions.
    The returned text always ends with a **STREET_ADDRESSES** block — copy those lines into your reply.

    Args:
        origin: Start address or place description.
        destination: End address or place description.
        mode: One of: driving, walking, bicycling, transit. Defaults to driving.
    """
    if not (origin or "").strip():
        return (
            "get_travel_time: missing origin. Use the user's Starting location context for routing "
            "(coordinates or address) as origin, or ask the user for a start point."
        )
    try:
        return get_travel_time_impl(origin, destination, mode)
    except Exception as e:
        return f"get_travel_time failed: {e}"


@tool
def get_directions(origin: str, destination: str, mode: str = "driving") -> str:
    """Summarized route with key steps using Google Directions API.

    Use when the user wants how to get from A to B, not just duration. Requires Directions API enabled.
    The returned text ends with a **STREET_ADDRESSES** block — copy those lines into your reply.

    Args:
        origin: Start address or place description.
        destination: End address or place description.
        mode: One of: driving, walking, bicycling, transit. Defaults to driving.
    """
    if not (origin or "").strip():
        return (
            "get_directions: missing origin. Use the user's Starting location context for routing "
            "(coordinates or address) as origin, or ask the user for a start point."
        )
    try:
        return get_directions_impl(origin, destination, mode)
    except Exception as e:
        return f"get_directions failed: {e}"


@tool
def get_place_address(place_query: str, near_coordinates: str = "") -> str:
    """Look up one place's formatted street address (Google Places).

    Use so each errand in the final answer has a full address. Combine chain + city/state from the user's
    errands (e.g. \"Target Austell GA\", \"Kroger Douglasville GA\").

    Args:
        place_query: Store name plus area, or a full address string.
        near_coordinates: Optional comma-separated lat,lon from \"Starting location context for routing\"
            so the correct nearby chain location is chosen.
    """
    if not (place_query or "").strip():
        return (
            "get_place_address: empty place_query. Pass a non-empty store + city or address."
        )
    try:
        return get_place_address_impl(place_query, near_coordinates)
    except Exception as e:
        return f"get_place_address failed: {e}"


@tool
def get_hours(place_query: str) -> str:
    """Look up opening hours and whether a place is open now (Google Places).

    Use for questions like when a store closes or if it is open. Requires
    `GOOGLE_MAPS_API_KEY` with Places API enabled.

    Args:
        place_query: Business name, chain + area, or street address.
    """
    if not (place_query or "").strip():
        return (
            "get_hours: missing place_query. Pass a non-empty store name with area or address "
            '(e.g. \"Trader Joe Cambridge MA\" or a full address).'
        )
    try:
        return get_hours_impl(place_query)
    except Exception as e:
        return f"get_hours failed: {e}"


@tool
def get_weather(location: str) -> str:
    """Current weather for a city or region (Open-Meteo; no API key).

    Use for rain/extreme temperature when ordering outdoor errands.

    Args:
        location: City or region name, e.g. 'Seattle', 'Austin TX'.
    """
    if not (location or "").strip():
        return (
            "get_weather: missing location. Pass a city/region or reuse coordinates from the user's "
            "Starting location context when inferring weather."
        )
    try:
        return get_weather_impl(location)
    except Exception as e:
        return f"get_weather failed: {e}"


ERRAND_TOOLS = [
    get_travel_time,
    get_directions,
    get_place_address,
    get_hours,
    get_weather,
]
