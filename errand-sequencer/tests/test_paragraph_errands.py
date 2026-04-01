"""Tests for paragraph-style errand input (prose vs one-per-line lists)."""

from __future__ import annotations

from guardrails.parsing import extract_errand_lines, split_paragraph_into_errands


def test_split_semicolon_paragraph():
    text = (
        "Today I need to hit the post office for a package; "
        "swing by Target for returns; "
        "then grab dinner somewhere near the mall."
    )
    out = split_paragraph_into_errands(text)
    assert len(out) == 3
    assert "post office" in out[0].lower()
    assert "target" in out[1].lower()
    assert "dinner" in out[2].lower()


def test_split_then_chain():
    text = "I'm going to stop at the bank then CVS then the grocery store on the way home."
    out = split_paragraph_into_errands(text)
    assert len(out) == 3
    assert "bank" in out[0].lower()
    assert "cvs" in out[1].lower()
    assert "grocery" in out[2].lower()


def test_split_oxford_comma_list():
    text = (
        "Please route me past USPS near Harvard, Trader Joe's on Memorial Drive, "
        "and CVS by the square."
    )
    out = split_paragraph_into_errands(text)
    assert len(out) == 3
    assert "usps" in out[0].lower()
    assert "trader" in out[1].lower()
    assert "cvs" in out[2].lower()


def test_split_plain_comma_three_items():
    text = "Stops today: USPS, Whole Foods, Chipotle."
    out = split_paragraph_into_errands(text)
    assert len(out) >= 3
    joined = " ".join(out).lower()
    assert "usps" in joined
    assert "whole foods" in joined
    assert "chipotle" in joined


def test_split_multi_sentence_paragraph():
    text = (
        "Start at the dry cleaner on Main. "
        "Next I need prescriptions at Walgreens. "
        "End with groceries at Kroger."
    )
    out = split_paragraph_into_errands(text)
    assert len(out) == 3
    assert "dry cleaner" in out[0].lower()
    assert "walgreens" in out[1].lower()
    assert "kroger" in out[2].lower()


def test_extract_errand_lines_expands_single_paragraph_line():
    blob = (
        "I need to visit the post office, the pharmacy, and the pet store before 5pm."
    )
    lines = extract_errand_lines(blob)
    assert len(lines) == 3
    assert any("post office" in x.lower() for x in lines)
    assert any("pharmacy" in x.lower() for x in lines)
    assert any("pet store" in x.lower() for x in lines)


def test_multiline_list_still_works():
    text = "Post office\nGrocery store\nPharmacy\n"
    lines = extract_errand_lines(text)
    assert lines == ["Post office", "Grocery store", "Pharmacy"]


def test_short_single_line_not_over_split():
    lines = extract_errand_lines("Just the post office today.")
    assert len(lines) == 1


def test_split_target_kroger_and_home():
    text = "I need to go to target in Austell, Kroger in Douglasville and home"
    out = split_paragraph_into_errands(text)
    assert len(out) == 3
    assert "target" in out[0].lower() and "austell" in out[0].lower()
    assert "kroger" in out[1].lower() and "douglasville" in out[1].lower()
    assert out[2].strip().lower() == "home"


def test_split_same_with_and_then_home():
    text = "I need to go to target in Austell, Kroger in Douglasville and then home"
    out = split_paragraph_into_errands(text)
    assert len(out) == 3
    assert out[2].strip().lower() == "home"


def test_split_costco_and_whole_foods_single_and():
    text = "I need to go to Costco in Kennesaw and Whole Foods in Buckhead"
    out = split_paragraph_into_errands(text)
    assert len(out) == 2
    assert "costco" in out[0].lower() and "kennesaw" in out[0].lower()
    assert "whole foods" in out[1].lower() or "whole" in out[1].lower()


def test_extract_errand_lines_expands_costco_and_whole_foods():
    blob = "I need to go to Costco in Kennesaw and Whole Foods in Buckhead"
    lines = extract_errand_lines(blob)
    assert len(lines) == 2

