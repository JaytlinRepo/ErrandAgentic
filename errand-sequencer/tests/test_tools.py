"""Tests for Maps and weather tool backends."""

from __future__ import annotations

import os

import pytest

from tools.weather import get_weather_impl


def test_get_weather_returns_summary():
    text = get_weather_impl("Paris")
    assert len(text) > 10
    assert "Paris" in text or "France" in text or "°C" in text or "Clear" in text or "cloud" in text.lower()


def test_get_weather_cambridge_massachusetts():
    text = get_weather_impl("Cambridge Massachusetts")
    assert "No geographic match" not in text
    assert "°C" in text or "Temperature" in text


@pytest.mark.skipif(not os.getenv("GOOGLE_MAPS_API_KEY"), reason="GOOGLE_MAPS_API_KEY not set")
def test_get_travel_time_matrix():
    from tools.maps import get_travel_time_impl

    text = get_travel_time_impl("Boston MA", "Cambridge MA", "driving")
    assert "Distance Matrix error" not in text
    assert "min" in text.lower()


@pytest.mark.skipif(not os.getenv("GOOGLE_MAPS_API_KEY"), reason="GOOGLE_MAPS_API_KEY not set")
def test_get_directions_summary():
    from tools.maps import get_directions_impl

    text = get_directions_impl("Boston MA", "Cambridge MA", "driving")
    assert "Directions error" not in text
    assert "Route" in text or "step" in text.lower() or "min" in text.lower()


@pytest.mark.skipif(not os.getenv("GOOGLE_MAPS_API_KEY"), reason="GOOGLE_MAPS_API_KEY not set")
def test_get_hours_places():
    from tools.hours import get_hours_impl

    text = get_hours_impl("CVS Harvard Square Cambridge MA")
    assert len(text) > 20
    assert "Cambridge" in text or "Harvard" in text or "CVS" in text
