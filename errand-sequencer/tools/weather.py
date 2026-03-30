"""Weather via Open-Meteo (no API key)."""

from __future__ import annotations

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


def get_weather_impl(location: str) -> str:
    """Current conditions for a city or region name."""
    location = (location or "").strip()
    if not location:
        return "No location provided."

    params = {"name": location, "count": 1, "language": "en", "format": "json"}
    with http_client() as c:
        r = c.get(f"{GEOCODE_URL}?{urlencode(params)}")
        r.raise_for_status()
        geo = r.json()
    results = geo.get("results") or []
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
