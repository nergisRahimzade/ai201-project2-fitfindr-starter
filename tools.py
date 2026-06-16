"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → dict | None
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> dict | None:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        The single best-matching listing as a dict with the fields
        {title, price, platform, condition}, or None if nothing matches.
        Never raises — a failed/empty search returns None.

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Return the highest-scoring listing, trimmed to the fields above
           (or None if no listing scores above 0).

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    try:
        listings = load_listings()
    except (OSError, ValueError):
        return None

    keywords = _tokenize(description)
    best, best_score = None, 0
    for listing in listings:
        if max_price is not None and listing.get("price", 0) > max_price:
            continue
        if size and not _size_matches(size, listing.get("size", "")):
            continue
        # Score by keyword overlap; keep the best (first wins on a tie).
        score = len(keywords & _tokenize(_searchable_text(listing)))
        if score > best_score:
            best, best_score = listing, score

    if best is None:
        return None
    return {f: best.get(f) for f in ("title", "price", "platform", "condition")}


# ── search_listings helpers ─────────────────────────────────────────────────

# Common filler words that carry no matching signal for a clothing search.
_STOPWORDS = {
    "a", "an", "and", "the", "for", "with", "looking", "want", "need", "find",
    "some", "any", "im", "size", "price", "priced", "cheap", "affordable",
    "under", "below", "less", "than", "max", "maximum",
}


def _tokenize(text: str) -> set[str]:
    """Lowercase `text` into a set of meaningful keyword tokens, dropping
    punctuation, pure numbers (prices/sizes), and short filler words."""
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in text or "")
    return {
        tok for tok in cleaned.split()
        if len(tok) >= 2 and not tok.isdigit() and tok not in _STOPWORDS
    }


def _searchable_text(item: dict) -> str:
    """Join an item's text fields into one blob for keyword matching."""
    return " ".join([
        item.get("title") or item.get("name") or "",
        item.get("description", ""),
        item.get("category", ""),
        item.get("brand") or "",
        *(item.get("style_tags") or []),
        *(item.get("colors") or []),
    ])


def _size_tokens(size: str) -> set[str]:
    """Split a size string into lowercase tokens on any non-alphanumeric
    separator: "S/M" -> {"s", "m"}, "XL (oversized)" -> {"xl", "oversized"}."""
    return set("".join(c.lower() if c.isalnum() else " " for c in size).split())


def _size_matches(requested: str, listing_size: str) -> bool:
    """Case-insensitive size match: true if any requested size token appears as
    a whole token in the listing's size ("M" matches "S/M", "W30" matches
    "W30 L30"). Token matching avoids "S" wrongly matching "oversized"."""
    return bool(_size_tokens(requested) & _size_tokens(listing_size))


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    items = (wardrobe or {}).get("items") or []

    if items:
        suggestion = _suggest_with_wardrobe(new_item, items)
        if suggestion and suggestion.strip():
            return suggestion
    return _affordable_fallback(new_item)


# ── suggest_outfit helpers ───────────────────────────────────────────────────

# Both LLM-backed tools (suggest_outfit, create_fit_card) use this model.
_LLM_MODEL = "llama-3.3-70b-versatile"

# Conditions considered "at least GOOD" for the affordable-pieces fallback.
_GOOD_CONDITIONS = {"good", "excellent"}

_NO_OUTFIT_MSG = (
    "Sorry, I couldn't find a suitable outfit with your current wardrobe."
)
_FALLBACK_PREFIX = (
    _NO_OUTFIT_MSG + " But here are a few affordable pieces that will go "
    "along with your new item: "
)


def _describe_item(item: dict) -> str:
    """Compact one-line description of a listing/new item for an LLM prompt."""
    parts = [item.get("title") or item.get("name") or "item"]
    if item.get("category"):
        parts.append(f"({item['category']})")
    if item.get("style_tags"):
        parts.append("style: " + ", ".join(item["style_tags"]))
    if item.get("colors"):
        parts.append("colors: " + ", ".join(item["colors"]))
    if item.get("condition"):
        parts.append(f"condition: {item['condition']}")
    return " — ".join(parts)


def _suggest_with_wardrobe(new_item: dict, items: list[dict]) -> str | None:
    """Ask the LLM to build 1–2 outfits from the new item + wardrobe pieces.
    Returns the suggestion text, or None if the LLM call fails (so the caller
    can fall back gracefully — this function never raises)."""
    wardrobe_lines = "\n".join(f"- {_describe_item(w)}" for w in items)
    style_tags = ", ".join(new_item.get("style_tags") or []) or "its overall look"

    prompt = (
        "You are a thrift-fashion stylist. A shopper is considering this "
        "second-hand item:\n"
        f"  {_describe_item(new_item)}\n\n"
        "Here is their current wardrobe:\n"
        f"{wardrobe_lines}\n\n"
        "Suggest 1–2 complete outfits that pair the new item with specific, "
        "named pieces from their wardrobe above. Lean into the vibe of the "
        f"new item ({style_tags}). For each outfit, name the exact wardrobe "
        "pieces you'd combine and add a short styling tip (how to wear/layer "
        "it). Keep it friendly and concrete — no preamble."
    )

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model=_LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception:
        # Network/auth/parse failure counts as "no outfit could be suggested".
        return None


def _affordable_fallback(new_item: dict) -> str:
    """Per planning.md: a fallback message plus up to 2 cheap, at-least-good
    condition listings that match the new item. If nothing fits, return the
    message alone (the agent stops and does not call create_fit_card)."""
    try:
        listings = load_listings()
    except (OSError, ValueError):
        listings = []

    item_keywords = _tokenize(_searchable_text(new_item))
    new_title = (new_item.get("title") or "").strip().lower()

    matches = []
    for listing in listings:
        if listing.get("condition") not in _GOOD_CONDITIONS:
            continue
        if (listing.get("title") or "").strip().lower() == new_title:
            continue  # don't recommend the item back to itself
        score = len(item_keywords & _tokenize(_searchable_text(listing)))
        if score:
            matches.append((score, listing))

    if not matches:
        return _NO_OUTFIT_MSG

    # Cheapest first (must be affordable), breaking ties by relevance.
    matches.sort(key=lambda pair: (pair[1].get("price", 0.0), -pair[0]))
    picks = [listing for _, listing in matches[:2]]
    summaries = [
        f"{p['title']} (${p['price']:.2f}, {p['condition']}, {p['platform']})"
        for p in picks
    ]
    return _FALLBACK_PREFIX + "; ".join(summaries)


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    # 1. Guard against an empty/whitespace outfit or a missing item — per
    #    planning.md, incomplete outfit data returns a descriptive message.
    if not outfit or not outfit.strip() or not new_item:
        return _INCOMPLETE_FIT_CARD_MSG

    # 2/3. Build the prompt, call the LLM, and return the caption.
    caption = _generate_fit_card(outfit, new_item)
    if caption and caption.strip():
        return caption
    return _INCOMPLETE_FIT_CARD_MSG


# ── create_fit_card helpers ──────────────────────────────────────────────────

_INCOMPLETE_FIT_CARD_MSG = (
    "Sorry, I couldn't generate a fit card because the outfit is incomplete."
)


def _generate_fit_card(outfit: str, new_item: dict) -> str | None:
    """Ask the LLM for a short, shareable OOTD caption. Returns the caption,
    or None if the LLM call fails (so the caller falls back gracefully —
    this function never raises)."""
    price = new_item.get("price")
    platform = new_item.get("platform")
    price_str = f"${price:.2f}" if isinstance(price, (int, float)) else "a steal"

    prompt = (
        "Write a short, casual Instagram/TikTok OOTD caption (2–4 sentences) "
        "for a thrifted find. It should feel authentic and personal, like a "
        "real outfit-of-the-day post — not a product description.\n\n"
        f"The standout piece: {_describe_item(new_item)}.\n"
        f"Snagged it for {price_str}"
        + (f" on {platform}.\n" if platform else ".\n")
        + f"\nThe outfit:\n{outfit}\n\n"
        "Mention the item name, its price, and the platform naturally — once "
        "each. Capture the outfit's vibe in specific terms. No hashtag spam, "
        "no preamble — just the caption."
    )

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model=_LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,  # higher temp → a different caption each time
        )
        return response.choices[0].message.content
    except Exception:
        return None
