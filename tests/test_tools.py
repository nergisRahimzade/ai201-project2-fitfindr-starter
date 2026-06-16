from tools import search_listings, suggest_outfit
from utils.data_loader import load_listings, get_empty_wardrobe


# ── search_listings ──────────────────────────────────────────────────────────

def test_search_returns_match():
    result = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(result, dict)
    assert set(result) == {"title", "price", "platform", "condition"}

def test_search_empty_results():
    result = search_listings("designer ballgown", size="XXS", max_price=5)
    assert result is None   # None, no exception

def test_search_price_filter():
    result = search_listings("jacket", size=None, max_price=10)
    assert result is None or result["price"] <= 10


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
