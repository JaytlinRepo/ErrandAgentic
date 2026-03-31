"""Tests for place query normalization (short retail names)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from tools.maps import get_place_address_impl, normalize_place_search_query, reverse_geocode_latlon


def test_target_expands():
    assert "Target" in normalize_place_search_query("target")


def test_latlon_unchanged():
    assert normalize_place_search_query("33.77, -84.66") == "33.77, -84.66"


def test_home_unchanged():
    assert normalize_place_search_query("home") == "home"


def test_cold_stone_phrase():
    assert "Cold Stone" in normalize_place_search_query("cold stone")


def test_reverse_geocode_latlon_returns_formatted_address():
    with patch("tools.maps.maps_api_key", return_value="test-key"), patch("tools.maps.http_client") as hc:
        cm = MagicMock()
        hc.return_value.__enter__.return_value = cm
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "status": "OK",
            "results": [{"formatted_address": "1 Peachtree St, Atlanta, GA"}],
        }
        cm.get.return_value = resp
        assert reverse_geocode_latlon(33.77, -84.66) == "1 Peachtree St, Atlanta, GA"


def test_get_place_address_impl_returns_street_line():
    with patch("tools.maps.maps_api_key", return_value="test-key"), patch("tools.maps.http_client") as hc:
        cm = MagicMock()
        hc.return_value.__enter__.return_value = cm
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "places": [{"formattedAddress": "100 Main St, Austell, GA 30106"}],
        }
        cm.post.return_value = resp
        out = get_place_address_impl("Target Austell GA", "")
        assert "100 Main St" in out
        assert "STREET_ADDRESS" in out
