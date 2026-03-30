"""Base tool helpers and shared HTTP utilities."""

from __future__ import annotations

import httpx

from configs.settings import GOOGLE_MAPS_API_KEY

DEFAULT_TIMEOUT = httpx.Timeout(30.0)


def maps_api_key() -> str:
    """Return the configured Google Maps API key or raise."""
    if not GOOGLE_MAPS_API_KEY:
        raise ValueError(
            "GOOGLE_MAPS_API_KEY is not set. Add it to `.env` and enable "
            "Places API + Distance Matrix API (and optionally Directions API) in Google Cloud."
        )
    return GOOGLE_MAPS_API_KEY


def http_client() -> httpx.Client:
    return httpx.Client(timeout=DEFAULT_TIMEOUT)
