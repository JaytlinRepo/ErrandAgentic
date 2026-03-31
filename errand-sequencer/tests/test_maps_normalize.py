"""Tests for place query normalization (short retail names)."""

from __future__ import annotations

from tools.maps import normalize_place_search_query


def test_target_expands():
    assert "Target" in normalize_place_search_query("target")


def test_latlon_unchanged():
    assert normalize_place_search_query("33.77, -84.66") == "33.77, -84.66"


def test_home_unchanged():
    assert normalize_place_search_query("home") == "home"


def test_cold_stone_phrase():
    assert "Cold Stone" in normalize_place_search_query("cold stone")
