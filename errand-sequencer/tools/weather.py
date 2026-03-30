"""Weather via Open-Meteo (no API key)."""

from __future__ import annotations

import re
from urllib.parse import urlencode

import httpx

from tools.base import http_client

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# WMO Weather interpretation codes (day), subset
_WMO = {
    0: "Clear",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with heavy hail",
}


def _describe_code(code: int | None) -> str:
    if code is None:
        return "unknown"
    return _WMO.get(int(code), f"code {code}")


def _geocode_search(client: httpx.Client, name: str, **extra: str | int) -> list:
    params: dict[str, str | int] = {
        "name": name,
        "count": 5,
        "language": "en",
        "format": "json",
    }
    params.update(extra)
    r = client.get(f"{GEOCODE_URL}?{urlencode(params)}")
    r.raise_for_status()
    return r.json().get("results") or []


def _resolve_location(client: httpx.Client, location: str) -> list:
    """Open-Meteo geocode with US city+state disambiguation (API uses countryCode)."""
    results = _geocode_search(client, location)
    if results:
        return results

    lo = location.lower()
    us_trailing_state = re.search(
        r",?\s*(massachusetts|connecticut|new\s+york|california|texas)\s*$", lo
    )
    if us_trailing_state:
        city = re.sub(
            r",?\s*(massachusetts|connecticut|new\s+york|california|texas)\s*$",
            "",
            location,
            count=1,
            flags=re.I,
        ).strip(" ,")
        if city:
            results = _geocode_search(client, city, countryCode="US")
            if results:
                return results

    if re.search(r",?\s*ma\s*$", lo) or "massachusetts" in lo:
        city = re.sub(r",?\s*(massachusetts|ma)\s*$", "", location, flags=re.I).strip(" ,")
        if city:
            results = _geocode_search(client, city, countryCode="US")
            if results:
                return results

    first = location.split(",")[0].strip()
    if first and first != location:
        results = _geocode_search(client, first, countryCode="US")
        if results:
            return results

    if re.search(r"\b(usa|u\.s\.|united states)\b", lo):
        shorter = re.sub(
            r",?\s*(usa|u\.s\.a?\.?|united states)\s*$", "", location, flags=re.I
        ).strip(" ,")
        if shorter:
            r_us = _geocode_search(client, shorter, countryCode="US")
            if r_us:
                return r_us

    return []


def get_weather_impl(location: str) -> str:
    """Current conditions for a city or region name."""
    location = (location or "").strip()
    if not location:
        return "No location provided."

    with http_client() as c:
        results = _resolve_location(c, location)
    if not results:
        return f"No geographic match for «{location}»."

    g = results[0]
    lat, lon = g["latitude"], g["longitude"]
    label = ", ".join(
        p for p in (g.get("name"), g.get("admin1"), g.get("country")) if p
    )

    fc_params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
        "timezone": "auto",
    }
    with http_client() as c:
        r = c.get(f"{FORECAST_URL}?{urlencode(fc_params)}")
        r.raise_for_status()
        fc = r.json()

    cur = fc.get("current") or {}
    temp = cur.get("temperature_2m")
    rh = cur.get("relative_humidity_2m")
    code = cur.get("weather_code")
    wind = cur.get("wind_speed_10m")
    desc = _describe_code(code)

    parts = [
        f"{label}: {desc}",
        f"Temperature: {temp}°C" if temp is not None else "",
        f"Humidity: {rh}%" if rh is not None else "",
        f"Wind: {wind} km/h" if wind is not None else "",
    ]
    return " | ".join(p for p in parts if p)
