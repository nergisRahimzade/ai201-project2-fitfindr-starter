import os

import pytest

from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import load_listings, get_empty_wardrobe, get_example_wardrobe

# Tests that call the live LLM (Groq) are skipped when no API key is present,
# so the offline suite still passes everywhere.
needs_llm = pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"), reason="requires GROQ_API_KEY for a live LLM call"
)


# ── search_listings ──────────────────────────────────────────────────────────

def test_search_returns_match():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list) and len(results) > 0
    assert isinstance(results[0], dict)

def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []   # empty list, no exception

def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


# ── suggest_outfit ───────────────────────────────────────────────────────────

# A real listing used as the "new item" the shopper is considering.
# These tests cover the offline (no-LLM) paths so they stay deterministic,
# matching the search_listings tests. The wardrobe→LLM path is verified manually.
NEW_ITEM = next(l for l in load_listings() if l["title"].startswith("Y2K Baby Tee"))

def test_suggest_empty_wardrobe_fallback():
    result = suggest_outfit(NEW_ITEM, get_empty_wardrobe())
    # Empty wardrobe → fallback message + affordable pieces, no exception.
    assert isinstance(result, str)
    assert result.startswith("Sorry, I couldn't find a suitable outfit")
    assert "affordable pieces" in result

def test_suggest_none_wardrobe():
    result = suggest_outfit(NEW_ITEM, None)   # missing wardrobe handled gracefully
    assert isinstance(result, str) and len(result.strip()) > 0

def test_suggest_no_match_message_only():
    # An item nothing in the dataset matches → message alone (agent will stop).
    result = suggest_outfit({"title": "zzqq", "style_tags": ["zzqq"]}, {"items": []})
    assert result == "Sorry, I couldn't find a suitable outfit with your current wardrobe."


# ── create_fit_card ──────────────────────────────────────────────────────────

INCOMPLETE_MSG = "Sorry, I couldn't generate a fit card because the outfit is incomplete."

def test_fit_card_empty_outfit():
    assert create_fit_card("", NEW_ITEM) == INCOMPLETE_MSG

def test_fit_card_whitespace_outfit():
    assert create_fit_card("   \n  ", NEW_ITEM) == INCOMPLETE_MSG   # no exception

def test_fit_card_missing_item():
    # Outfit text present but no item to caption → incomplete.
    assert create_fit_card("wear the tee with baggy jeans", None) == INCOMPLETE_MSG

@needs_llm
def test_fit_card_returns_caption():
    outfit = "Y2K Baby Tee with baggy jeans and chunky white sneakers."
    result = create_fit_card(outfit, NEW_ITEM)
    assert isinstance(result, str) and result.strip()
    assert result != INCOMPLETE_MSG   # a real caption, not the error message


# ── end-to-end: all three tools chained ──────────────────────────────────────

@needs_llm
def test_full_pipeline_search_suggest_fit_card():
    # Tool 1: find matching items and take the top result.
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list) and results
    item = results[0]

    # Tool 2: suggest an outfit from a real wardrobe (live LLM).
    outfit = suggest_outfit(item, get_example_wardrobe())
    assert isinstance(outfit, str) and outfit.strip()
    assert not outfit.startswith("Sorry")   # a real suggestion, not the fallback

    # Tool 3: turn the outfit into a shareable caption (live LLM).
    card = create_fit_card(outfit, item)
    assert isinstance(card, str) and card.strip()
    assert card != INCOMPLETE_MSG
