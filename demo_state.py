"""
demo_state.py — makes state passing VISIBLE for the demo video.

It runs one full interaction through run_agent(), then prints each session field
alongside its Python object id(). Because state is threaded through a single
session dict (not re-derived), you can SEE the same id() appear as the output of
one tool and the input of the next — e.g. search_results[0] and selected_item
share the same id, and that is the exact dict handed to suggest_outfit /
create_fit_card.

    python demo_state.py
"""

from agent import run_agent
from utils.data_loader import get_example_wardrobe

QUERY = "looking for a vintage graphic tee under $30"


def short(value, n=72):
    """One-line, truncated repr for readable on-camera output."""
    text = str(value).replace("\n", " ")
    return text if len(text) <= n else text[:n] + "..."


session = run_agent(QUERY, get_example_wardrobe())

print("=" * 70)
print(f'USER QUERY: "{QUERY}"')
print("=" * 70)

print("\n[1] PARSE  -> session['parsed']")
print(f"      {session['parsed']}")

print("\n[2] search_listings()  -> session['search_results']")
print(f"      {len(session['search_results'])} matches; top = "
      f"{short(session['search_results'][0]['title'])}")
print(f"      id(search_results[0]) = {id(session['search_results'][0])}")

print("\n[3] select top result  -> session['selected_item']")
print(f"      title = {short(session['selected_item']['title'])}")
print(f"      id(selected_item)     = {id(session['selected_item'])}")
print(f"      --> SAME OBJECT as search_results[0]? "
      f"{session['selected_item'] is session['search_results'][0]}")
print("          (this exact dict is what gets passed into suggest_outfit)")

print("\n[4] suggest_outfit(selected_item, wardrobe)  -> session['outfit_suggestion']")
print(f"      {short(session['outfit_suggestion'])}")
print(f"      id(outfit_suggestion) = {id(session['outfit_suggestion'])}")
print("          (this exact string is what gets passed into create_fit_card)")

print("\n[5] create_fit_card(outfit_suggestion, selected_item)  -> session['fit_card']")
print(f"      {short(session['fit_card'])}")

print("\n" + "=" * 70)
print("FINAL SESSION (one object carrying all state):")
print("=" * 70)
for key, value in session.items():
    print(f"  {key:18} = {short(value)}")
