"""Heuristic: restaurant vs grocery / retail (for eat-last UI)."""

from __future__ import annotations


def is_food_place(text: str) -> bool:
    t = text.lower()
    grocery_markers = (
        "grocery",
        "groceries",
        "supermarket",
        "market",
        "kroger",
        "walmart",
        "costco",
        "sam's club",
        "aldi",
        "publix",
        "trader joe",
        "whole foods",
        "food lion",
        "safeway",
    )
    if any(k in t for k in grocery_markers):
        return False

    keywords = (
        "mcdonald",
        "burger king",
        "wendy",
        "taco",
        "chipotle",
        "subway",
        "kfc",
        "popeyes",
        "chick-fil",
        "restaurant",
        "pizza",
        "coffee",
        "starbucks",
        "dunkin",
        "cafe",
        "eat",
        "lunch",
        "dinner",
    )
    return any(k in t for k in keywords)
