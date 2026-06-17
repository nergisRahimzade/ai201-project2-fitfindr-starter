# FitFindr 🛍️

FitFindr is an agentic assistant for secondhand fashion. You describe what you're
looking for in plain language; it finds a matching listing, suggests how to style it
with your existing wardrobe, and writes a shareable "fit card" caption for it.

It runs as a small planning loop over three tools, with a single session dict
carrying state between them. The agent **branches on what each tool returns** —
it does not call all three tools unconditionally.

---

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file in the project root
(free key at [console.groq.com](https://console.groq.com)):

```
GROQ_API_KEY=your_key_here
```

Tools 2 and 3 call the Groq-hosted `llama-3.3-70b-versatile` model. Tool 1 and all
fallback/error paths are pure Python and need no API key.

## Running

```bash
python app.py        # launch the Gradio UI (open the URL printed in the terminal)
python agent.py      # CLI walkthrough of all branches with state-flow assertions
python -m pytest     # run the test suite (run from the project root)
```

The Gradio app serves at **http://localhost:7860** by default — but check your
terminal, as the port can differ.

---

## Tool Inventory

All three tools live in [`tools.py`](tools.py) and can be called and tested in
isolation. The documented signatures below match the actual function definitions.

### 1. `search_listings(description, size=None, max_price=None) → list[dict]`

| | |
|---|---|
| **Inputs** | `description` (str) — keywords describing the item, e.g. `"vintage graphic tee"`. `size` (str \| None) — size filter, case-insensitive (`"M"` matches `"S/M"`); `None` skips the filter. `max_price` (float \| None) — inclusive price ceiling; `None` skips the filter. |
| **Output** | A list of matching **full listing dicts** (`id, title, description, category, style_tags, size, condition, price, colors, brand, platform`), sorted by relevance, best match first. **Empty list `[]`** if nothing matches. |
| **Purpose** | Find candidate secondhand items. It filters by price/size, then scores each remaining listing by keyword overlap between the query and the listing's text (title, description, category, brand, style tags, colors), drops zero-score items, and sorts by score. No LLM — deterministic. |

### 2. `suggest_outfit(new_item, wardrobe) → str`

| | |
|---|---|
| **Inputs** | `new_item` (dict) — the listing the shopper is considering. `wardrobe` (dict) — `{"items": [...]}`, the user's existing pieces; may be empty. |
| **Output** | A non-empty string. With a stocked wardrobe: 1–2 concrete outfits built from named wardrobe pieces, leaning into the new item's style tags, with styling tips. With an empty/unworkable wardrobe: a fallback message plus up to 2 cheap, at-least-good-condition listings that match the item. |
| **Purpose** | Turn a found item into wearable outfit ideas. Calls the LLM for real suggestions; degrades to the affordable-pieces fallback when no outfit can be built. |

### 3. `create_fit_card(outfit, new_item) → str`

| | |
|---|---|
| **Inputs** | `outfit` (str) — the suggestion string from `suggest_outfit()`. `new_item` (dict) — the listing being captioned. |
| **Output** | A 2–4 sentence casual OOTD caption mentioning the item name, price, and platform once each. If `outfit` is empty/whitespace or `new_item` is missing → a descriptive error string (never an exception). |
| **Purpose** | Produce a social-media-ready caption. Uses a higher LLM temperature (0.9) so captions vary across runs/inputs. |

The orchestrator [`run_agent(query: str, wardrobe: dict) → dict`](agent.py) ties these
together and returns the completed session dict.

---

## How the Planning Loop Works

The loop lives in `run_agent()` ([agent.py](agent.py)). It is **conditional**, not a
fixed three-step pipeline — the result of each tool decides whether the next one runs.

```
parse query → search_listings → [results?] → suggest_outfit → [real outfit?] → create_fit_card
                                    │ no                          │ no
                                    └── STOP (error)              └── STOP (keep fallback)
```

1. **Parse** the free-text query into `description`, `size`, and `max_price` using
   regex (see `_parse_query()`), and store it in `session["parsed"]`.
2. **Search.** Call `search_listings()` with the parsed parameters.
   - **Branch A — no results (`[]`):** set `session["error"]` to a message that says
     *what failed and what to try* (loosen the filters / broaden the description) and
     **return immediately.** `suggest_outfit` and `create_fit_card` are **not** called.
   - Otherwise store the list in `session["search_results"]` and take the top result
     (`results[0]`) as `session["selected_item"]`.
3. **Suggest an outfit** from the selected item + wardrobe.
   - **Branch B — no workable outfit:** if `suggest_outfit()` returns its fallback
     message (empty wardrobe, or nothing pairs), the loop **stops before
     `create_fit_card`** and leaves `session["fit_card"] = None`. The user still sees
     the helpful fallback text, but no caption is fabricated from a non-outfit.
4. **Create the fit card** only when there's a real outfit, then return the session.

Because of Branches A and B, the same code produces visibly different behavior for
different inputs — which is the whole point of a planning loop.

---

## State Management

A single **session dict** (built by `_new_session()`) is the source of truth for one
interaction. Each step reads what it needs and writes its result back; nothing is
re-prompted or hardcoded between steps.

| Key | Written at | Holds |
|---|---|---|
| `query` | start | the original user text |
| `parsed` | step 1 | `{description, size, max_price}` |
| `search_results` | step 2 | the relevance-sorted list from `search_listings` |
| `selected_item` | step 2 | `search_results[0]` — the dict passed into `suggest_outfit` and `create_fit_card` |
| `wardrobe` | start | the user's wardrobe dict |
| `outfit_suggestion` | step 3 | the string from `suggest_outfit` — the exact value passed into `create_fit_card` |
| `fit_card` | step 4 | the caption from `create_fit_card` (stays `None` if the loop stopped early) |
| `error` | any branch | set when the interaction ends early; `None` on success |

State passes **by object identity**: `selected_item` *is* `search_results[0]`, and the
same string in `outfit_suggestion` is what `create_fit_card` receives. `python agent.py`
asserts both of these so the flow is verifiable, not just claimed.

`handle_query()` in [app.py](app.py) calls `run_agent()` and maps the session to the
three UI panels: the error (if any) into the first panel, otherwise the formatted
listing, the outfit suggestion, and the fit card into the three panels respectively.

---

## Error Handling (per tool)

Every tool fails *soft* — it returns a usable value instead of raising — so the
planning loop can always branch cleanly. Each row below was triggered deliberately
during Milestone 5 testing.

| Tool | Failure mode | Behavior | Triggered example |
|---|---|---|---|
| `search_listings` | Impossible query (no match) | Returns `[]`, never raises. The agent reports what failed *and what to try*. | `search_listings("designer ballgown", size="XXS", max_price=5)` → `[]`. Full agent → `"Sorry, I couldn't find any items matching your criteria. Try removing the size or price filter, or describing the item more broadly…"` and `outfit_suggestion`/`fit_card` stay `None`. |
| `suggest_outfit` | Empty wardrobe / no outfit possible | Returns a useful string (fallback message + ≤2 cheap, good-condition matching pieces), never empty, never raises. | `suggest_outfit(results[0], get_empty_wardrobe())` → `"Sorry, I couldn't find a suitable outfit with your current wardrobe. But here are a few affordable pieces… Leather Belt — Brown, Braided ($12.00, excellent, thredUp); Biker Shorts — Black, Shiny ($14.00, excellent, depop)"` |
| `create_fit_card` | Empty/whitespace outfit, or missing item | Returns a descriptive error string, never raises. | `create_fit_card("", results[0])` → `"Sorry, I couldn't generate a fit card because the outfit is incomplete."` |

Additionally, all three LLM calls are wrapped so a network/auth failure degrades to the
relevant fallback rather than crashing the agent.

---

## Spec Reflection

**One way the spec helped:** the Architecture diagram and Error-Handling table in
[planning.md](planning.md) pinned down the *exact* branch points and fallback wording
before any code existed. Implementing the two STOP branches (no results; no workable
outfit) was then mechanical — the diagram already said where to stop and what message
to surface, so the planning loop matched the design on the first pass.

**One way the implementation diverged, and why:** planning.md's Tool 1 entry says
`search_listings` should return *"the top matching item"* with only
`{title, price, platform, condition}`. The implementation instead returns a
**relevance-sorted list of full listing dicts**. Two forces drove this: (1) the
planning loop and Architecture diagram both select `results[0]`, which needs a list;
and (2) `suggest_outfit`/`create_fit_card` need the item's full field set
(`style_tags`, `category`, `colors`) to reason about vibe and matches — the trimmed
4-field shape couldn't support them. The 4-field view still exists, but as a
*display* concern in the UI's listing panel rather than the tool's return type.
(A smaller divergence: for an empty wardrobe, the in-code TODO suggested "general
styling advice," but I followed planning.md's more specific rule — return affordable
matching pieces — to keep behavior consistent with the Error-Handling table.)

---

## AI Usage

I used Claude to implement and refine the code, directing it with specific sections of
my planning.md rather than vague asks. Concrete instances:

1. **Implementing `search_listings` (Tool 1).** I gave Claude my Tool 1 spec (inputs,
   return value, failure mode), the Error-Handling table, and the Architecture diagram,
   and told it to use `load_listings()`. It produced a keyword-overlap scorer with
   price/size filtering. **What I changed:** I had it simplify the first draft (it had
   added a strong/weak field-weighting scheme beyond my spec), and that simplification
   surfaced a real bug — a substring size check matched `"S"` against `"oversized"`,
   which I had it fix with token-based size matching. I also iterated on the return
   type (single item vs. list) and ultimately kept a relevance-sorted list.

2. **Implementing `suggest_outfit` (Tool 2).** I gave Claude the Tool 2 spec, the
   Error-Handling row, the State-Management and Architecture sections, and specified
   the `llama-3.3-70b-versatile` model. It generated the LLM call plus an
   empty-wardrobe path. **What I overrode:** the starter's in-code TODO said an empty
   wardrobe should get "general styling advice," but my planning.md said to return ≤2
   cheap, good-condition matching pieces. I directed it to follow planning.md, so the
   fallback returns affordable suggestions instead of generic advice.

3. **Wiring the planning loop (Milestone 4).** I shared the full Architecture diagram
   plus the Planning Loop and State-Management sections and asked for `run_agent()`. I
   reviewed the result specifically for: does it branch on the search result, does it
   store values in the session dict, and does it avoid calling all three tools
   unconditionally? I kept the two-branch structure and added explicit state-identity
   assertions to `python agent.py` to prove state passes between tools.

---

## Project Layout

```
ai201-project2-fitfindr-starter/
├── tools.py            # the three tools (+ private helpers)
├── agent.py            # run_agent() planning loop, query parser, CLI walkthrough
├── app.py              # Gradio UI + handle_query()
├── planning.md         # design doc (written before implementation)
├── tests/test_tools.py # tool + end-to-end tests
├── data/               # listings.json, wardrobe_schema.json
└── utils/data_loader.py
```
