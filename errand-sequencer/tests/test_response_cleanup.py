"""Tests for assistant response post-processing."""

from app.response_cleanup import strip_relative_now_phrases


def test_strip_relative_now_phrases_simple():
    text = "Arrival ETA: now + 18 minutes."
    out = strip_relative_now_phrases(text)
    assert "now + 18 minutes" not in out.lower()


def test_strip_relative_now_phrases_chained():
    text = "ETA now + 18 minutes + 9 minutes and depart now + 5 minutes."
    out = strip_relative_now_phrases(text)
    assert "now +" not in out.lower()


def test_strip_boilerplate_notice_block():
    text = (
        "Plan looks good.\n\n"
        "This order follows the planned stop order and avoids duplicating stops. "
        "The travel times are estimates based on the provided tool outputs, and the ETAs take into "
        "account the current local time at request.\n\n"
        "Note that this route assumes the user will be leaving from their starting location "
        "(2732 Groovers Lake Point) for each leg of the trip. If you have any further questions "
        "or need additional assistance, please let me know!"
    )
    out = strip_relative_now_phrases(text)
    assert "planned stop order and avoids duplicating stops" not in out.lower()
    assert "assistance, please let me know" not in out.lower()
    assert out.strip() == "Plan looks good."


def test_strip_based_on_provided_information_prefix():
    text = "Based on the provided information and tool outputs, here is a suggested route for the user: Plan text."
    out = strip_relative_now_phrases(text)
    assert out == "Plan text."


def test_readability_cleanup_splits_numbered_and_bulleted_lines():
    text = (
        "Here is route 1. From A to B, travel time: 5 minutes ETA: "
        "2. From B to C, travel time: 9 minutes ETA: "
        "Addresses: • From A to B • To C"
    )
    out = strip_relative_now_phrases(text)
    assert "\n1. " in out
    assert "\n2. " in out
    assert "Addresses:" not in out


def test_strip_route_noise_addresses_block():
    text = (
        "Since the first leg is from Current Location to Wendy's, we'll use the full address.\n"
        "• From A to B, travel time 5 minutes.\n\n"
        "Addresses:\n"
        "• From A to B\n"
        "• To Wendy's\n"
        "\n---\n**Resolved stop addresses**\n- **wendys:** 599 Thornton Rd"
    )
    out = strip_relative_now_phrases(text)
    assert "Since the first leg is from Current Location" not in out
    assert "\nAddresses:\n" not in out
    assert "**Resolved stop addresses**" in out

