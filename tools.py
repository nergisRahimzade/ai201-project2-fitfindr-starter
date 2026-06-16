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
    best_listing = None
    best_score = 0
    for listing in listings:
        if max_price is not None and listing.get("price", 0) > max_price:
            continue
        if size and not _size_matches(size, listing.get("size", "")):
            continue

        listing_text = " ".join([
            listing.get("title", ""),
            listing.get("description", ""),
            listing.get("category", ""),
            listing.get("brand") or "",
            *(listing.get("style_tags") or []),
            *(listing.get("colors") or []),
        ])
        score = len(keywords & _tokenize(listing_text))

        # Keep the highest-scoring match so far (first wins on a tie).
        if score > best_score:
            best_score = score
            best_listing = listing

    if best_listing is None:
        return None
    return {
        field: best_listing.get(field)
        for field in ("title", "price", "platform", "condition")
    }


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
    # Replace this with your implementation
    return ""


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
    # Replace this with your implementation
    return ""
