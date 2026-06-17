# 🎬 FitFindr — Demo Video Script (3–5 min)

**Setup before recording:** have two windows ready — (1) the Gradio app open in a
browser, (2) a terminal in the project root. Increase terminal font size for legibility,
record at ~1080p, and rehearse once so it lands in 3–5 minutes.

---

## Scene 0 — Intro (15s)
> "This is FitFindr — an agent that helps you shop secondhand. You describe what you
> want, and it chains three tools: it finds a listing, styles it against your wardrobe,
> and writes a shareable caption. The key idea is a **planning loop** that decides which
> tools to run based on what each one returns — it doesn't blindly run all three."

## Scene 1 — Launch (15s)
Terminal:
```bash
python app.py
```
> "I start the app and open the URL it prints — here, localhost:7860."

Switch to the browser showing the three empty panels.

## Scene 2 — Happy path, all 3 tools (75–90s)
Query box (wardrobe = **Example wardrobe**):
```
looking for a vintage graphic tee under $30
```
Click **Find it**. As the panels fill, narrate each tool:

> "Step one — the agent **parses** my query with regex: description 'vintage graphic
> tee', max price $30. It calls **`search_listings`**, which scores every listing by
> keyword overlap and returns the best match — the Y2K Baby Tee, $18, on Depop.
> That's panel one."

> "Step two — it takes that found item and my wardrobe and calls **`suggest_outfit`**,
> which asks the LLM to build outfits from my *actual named pieces* — wide-leg khakis,
> chunky sneakers. Panel two."

> "Step three — it passes that outfit plus the item into **`create_fit_card`**, which
> writes the Instagram caption in panel three — notice it names the item, the $18 price,
> and Depop, once each."

## Scene 3 — State passing (visible) (40s)
Terminal:
```bash
python agent.py
```
Point at the `[state check] ... OK` lines:

> "To prove state actually flows between tools and isn't re-derived: this CLI runs the
> same loop and **asserts** that `selected_item` is literally the same object as
> `search_results[0]` — the exact dict that went into `suggest_outfit` — and that the
> outfit string is what went into `create_fit_card`. These assertions pass, so state is
> genuinely threaded through the session dict."

## Scene 4 — Branch behavior: empty wardrobe (30s)
Browser: switch the radio to **Empty wardrobe (new user)**, same query, **Find it**:

> "Same item, but now an empty wardrobe. The agent **branches** — `suggest_outfit` can't
> build an outfit, so it falls back to affordable matching pieces, and the loop **stops
> before making a fit card**. Panel three stays empty. Different input, different path."

## Scene 5 — Triggered failure (40s)
Terminal (required failure trigger):
```bash
python -c "from tools import search_listings; print(search_listings('designer ballgown', size='XXS', max_price=5))"
```
> "I deliberately break it — an impossible query. `search_listings` returns an empty
> list, no exception."

Then in the browser, query `designer ballgown size XXS under $5`:

> "And end-to-end, the agent doesn't crash or say a bare 'no results' — it tells me
> **what failed and what to try**: remove a filter or broaden the description. It also
> never calls the outfit or caption tools, because there's nothing to style."

## Scene 6 — Close (10s)
> "Three tools, a conditional planning loop, state passing through one session dict, and
> every failure mode handled gracefully. That's FitFindr."

---

## ✅ Rubric checklist (what the video must show)

- [ ] Complete multi-step interaction, query → fit card, **all 3 tools** (Scene 2)
- [ ] Narration at each step — which tool and why (Scene 2)
- [ ] State passing visible/narrated — the `agent.py` assertions (Scene 3)
- [ ] At least one triggered failure + graceful response (Scene 5)
- [ ] (Bonus) conditional branching via the empty-wardrobe path (Scene 4)
- [ ] Interface running at the printed URL (Scene 1)

**Tips:** the two LLM calls in Scene 2 take a few seconds each — narrate through them
rather than cutting. Capture narration live or dub it after.
