"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import (
    search_listings,
    suggest_outfit,
    create_fit_card,
    _NO_OUTFIT_MSG,   # fallback prefix -> lets the loop detect "no outfit built"
)


# ── query parsing ───────────────────────────────────────────────────────────

def _parse_query(query: str) -> dict:
    """
    Extract a search description, size, and max_price from a free-text query
    using regex (documented choice — no LLM needed for this step).

    Examples:
        "vintage graphic tee under $30, size M"
            -> {description: "vintage graphic tee", size: "M", max_price: 30.0}
        "90s track jacket in size M"
            -> {description: "90s track jacket in", size: "M", max_price: None}
    """
    text = (query or "").strip()

    # max_price: "under $30", "below 30", "max $40", or a bare "$30".
    price_match = re.search(
        r"(?:under|below|less than|max(?:imum)?|<)\s*\$?\s*(\d+(?:\.\d+)?)",
        text, re.I,
    ) or re.search(r"\$\s*(\d+(?:\.\d+)?)", text)
    max_price = float(price_match.group(1)) if price_match else None

    # size: "size M", "size 8", "in size L".
    size_match = re.search(r"\bsize\s+([A-Za-z0-9/]+)", text, re.I)
    size = size_match.group(1) if size_match else None

    # description: the query with the recognized size/price phrases stripped out.
    spans = [m.span() for m in (price_match, size_match) if m]
    description = text
    for start, end in sorted(spans, reverse=True):
        description = description[:start] + description[end:]
    description = re.sub(r"\s+", " ", description).strip(" ,") or text

    return {"description": description, "size": size, "max_price": max_price}


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

    TODO — implement this function using the planning loop you designed in planning.md:

        Step 1: Initialize the session with _new_session().

        Step 2: Parse the user's query to extract a description, size, and
                max_price. You can use regex, string splitting, or ask the LLM
                to parse it — document your choice in planning.md.
                Store the result in session["parsed"].

        Step 3: Call search_listings() with the parsed parameters.
                Store results in session["search_results"].
                If no results: set session["error"] to a helpful message and
                return the session early. Do NOT proceed to suggest_outfit
                with empty input.

        Step 4: Select the item to use (e.g., the top result).
                Store it in session["selected_item"].

        Step 5: Call suggest_outfit() with the selected item and wardrobe.
                Store the result in session["outfit_suggestion"].

        Step 6: Call create_fit_card() with the outfit suggestion and selected item.
                Store the result in session["fit_card"].

        Step 7: Return the session.

    Before writing code, complete the Planning Loop and State Management sections
    of planning.md — your implementation should match what you described there.
    """
    # Step 1: fresh session — the single source of truth for this interaction.
    session = _new_session(query, wardrobe)

    # Step 2: parse the query into search parameters.
    session["parsed"] = _parse_query(query)
    parsed = session["parsed"]

    # Step 3: search. search_listings returns a relevance-sorted list (or []).
    results = search_listings(
        parsed["description"],
        size=parsed["size"],
        max_price=parsed["max_price"],
    )
    session["search_results"] = results
    if not results:
        # Branch A: no match -> stop before suggest_outfit (do not chain on empty).
        session["error"] = (
            "Sorry, I couldn't find any items matching your criteria. "
            "Try removing the size or price filter, or describing the item "
            "more broadly (e.g. \"denim jacket\" instead of a specific brand)."
        )
        return session

    # Step 4: select the top (most relevant) result to carry forward.
    session["selected_item"] = results[0]

    # Step 5: suggest an outfit from the selected item + wardrobe.
    session["outfit_suggestion"] = suggest_outfit(session["selected_item"], wardrobe)

    # Branch B: an empty/unworkable wardrobe makes suggest_outfit return its
    # fallback message instead of a real outfit. Per the Architecture diagram,
    # stop here and do NOT build a fit card (leave session["fit_card"] = None).
    if session["outfit_suggestion"].startswith(_NO_OUTFIT_MSG):
        return session

    # Step 6: turn the real outfit suggestion into a shareable fit card.
    session["fit_card"] = create_fit_card(
        session["outfit_suggestion"], session["selected_item"]
    )

    # Step 7: return the completed session.
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee (example wardrobe) ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Parsed:   {session['parsed']}")
        print(f"Found:    {session['selected_item']['title']}")
        print(f"\nOutfit:   {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")
        # State-flow check: the same dict/string objects move between tools.
        assert session["selected_item"] is session["search_results"][0]
        assert session["fit_card"] is not None
        print("\n[state check] selected_item is search_results[0]; fit_card built OK")

    print("\n\n=== Branch B: empty wardrobe -> fallback, NO fit card ===\n")
    session_empty = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_empty_wardrobe(),
    )
    print(f"Outfit:   {session_empty['outfit_suggestion']}")
    print(f"Fit card: {session_empty['fit_card']}")
    assert session_empty["fit_card"] is None   # create_fit_card was NOT called
    print("[state check] empty wardrobe -> fit_card is None (create_fit_card skipped) OK")

    print("\n\n=== Branch A: no-results path -> error, NO outfit/fit card ===\n")
    session_none = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message:     {session_none['error']}")
    print(f"Outfit suggestion: {session_none['outfit_suggestion']}")
    print(f"Fit card:          {session_none['fit_card']}")
    assert session_none["error"] is not None
    assert session_none["outfit_suggestion"] is None   # suggest_outfit was NOT called
    assert session_none["fit_card"] is None
    print("[state check] no results -> suggest_outfit & create_fit_card skipped OK")
