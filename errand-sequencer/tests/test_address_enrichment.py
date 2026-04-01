"""Tests for server-side stop address enrichment."""

from __future__ import annotations

from unittest.mock import patch

from app.address_enrichment import append_resolved_stop_addresses


def test_appends_resolved_addresses_for_comma_and_then_home():
    lines = [
        "I need to go to target in Austell, Kroger in Douglasville and then home",
    ]
    ok_out = (
        "Query: x\n"
        "STREET_ADDRESS (required — paste into your itinerary): 100 Store Rd, Austell, GA\n"
    )

    with patch("app.address_enrichment.get_place_address_impl", return_value=ok_out) as gp:
        out = append_resolved_stop_addresses(
            "Assistant plan here.",
            lines,
            starting_location_note="33.7,-84.6",
            display_location="2732 Example St, Lithia Springs, GA",
            cache={},
        )
    assert "Resolved stop addresses" in out
    assert "100 Store Rd" in out
    assert gp.call_count == 2
    assert "**Home:**" in out


def test_appends_resolved_addresses_for_comma_and_home_no_then():
    lines = [
        "I need to go to target in Austell, Kroger in Douglasville and home",
    ]
    ok_out = (
        "Query: x\n"
        "STREET_ADDRESS (required — paste into your itinerary): 4125 Austell Rd, Austell, GA\n"
    )
    with patch("app.address_enrichment.get_place_address_impl", return_value=ok_out) as gp:
        out = append_resolved_stop_addresses(
            "Assistant plan here.",
            lines,
            starting_location_note="33.7,-84.6",
            display_location="2732 Example Rd, Lithia Springs, GA",
            cache={},
        )
    assert gp.call_count == 2
    assert "**Home:** 2732 Example Rd" in out


def test_home_uses_display_location():
    lines = ["Target Austell", "home"]
    ok_out = "Query: x\nSTREET_ADDRESS (required — paste into your itinerary): 1 Main St\n"
    with patch("app.address_enrichment.get_place_address_impl", return_value=ok_out):
        out = append_resolved_stop_addresses(
            "Hi.",
            lines,
            starting_location_note=None,
            display_location="99 Home Ln, GA",
            cache={},
        )
    assert "**Home:** 99 Home Ln, GA" in out


def test_append_resolved_stop_addresses_replaces_existing_section():
    lines = ["Target Austell"]
    prior = "Plan text.\n\n---\n**Resolved stop addresses**\n- old line"
    ok_out = "Query: x\nSTREET_ADDRESS (required — paste into your itinerary): 1 Main St\n"
    with patch("app.address_enrichment.get_place_address_impl", return_value=ok_out):
        out = append_resolved_stop_addresses(
            prior,
            lines,
            starting_location_note=None,
            display_location=None,
            cache={},
        )
    assert out.count("**Resolved stop addresses**") == 1
    assert "old line" not in out


def test_hungry_want_to_go_label_is_clean():
    lines = ["I'm hungry and want to go to wendys"]
    ok_out = (
        "Query: x\n"
        "STREET_ADDRESS (required — paste into your itinerary): 599 Thornton Rd, Lithia Springs, GA\n"
    )
    with patch("app.address_enrichment.get_place_address_impl", return_value=ok_out):
        out = append_resolved_stop_addresses(
            "Plan.",
            lines,
            starting_location_note=None,
            display_location=None,
            cache={},
        )
    assert "**wendys:**" in out.lower()
