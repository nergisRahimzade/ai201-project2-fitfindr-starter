# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Searches the dataset and returns matching items that match the given description, size and maximum price. If no items match, it handles the case gracefully without crashing the agent, failing silently or anything that would frustrate the user.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): A textual description of the item to search for.
- `size` (str): The size of the item.
- `max_price` (float): The maximum price the user is willing to pay.

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->
It returns the top matching item, containing fields of title, price, platform and condition.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->
The agent first checks if any of the fields match, and if at least one does - not all - it will return "I couldn't find perfectly matching items, but these items are relevant to your criterias.". 
If none of the fields match, the agent will not execute the next step. It will stop and return "Sorry, I couldn't find any items matching your criteria."

---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Given a specific item and the user's current wardrobe, suggests one or more complete outfit combinations. It will also handle an empty or minimal wardrobe.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): The title of the new item to be added to the outfit.
- `wardrobe` (dict): The user's current wardrobe.

**What it returns:**
<!-- Describe the return value -->
It returns a description of what to wear this items with - chosen from the user's current wardrobe - to achieve a certain kind of look and vibe - shown in the style tags of the new item -, also giving tips on how to wear the item and style it. 

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->
If the wardrobe is empty or no outfit can be suggested, it will return "Sorry, I couldn't find a suitable outfit with your current wardrobe. But here are a few affordable pieces that will go along with your new item: " and returns max of 2 items that matches the new item. The newly returned items HAS to be CHEAP, affordable and at least in GOOD condition. If nothing could be found to suggest an outfit, the agent will stop and will not execute the next tool.

---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Generates a short, shareable description of a complete outfit - the kind of thing someone would caption an Instagram post with. It will produce something different each time for different inputs.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (...): The complete outfit to generate a fit card for - includes the items suggested by the previous tool - suggest_outfit - and the new item added by the user in the prev tool as a parameter.

**What it returns:**
<!-- Describe the return value -->
It returns a short, shareable description of the outfit, suitable for use as a social media caption.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
If the outfit data is incomplete of missing, the agent will return "Sorry, I couldn't generate a fit card because the outfit is incomplete."

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->
The agent first calls search_listings() with the parameters the user provides. The agent looks at the output of from search_listings(), if the output is not empty and has the format that I instruct the agent to have, it will proceed with the next step with the output given as a parameter to the next tool, if the tool needs to be used. If the output is empty or doesn't quite have the format the user needs to see, then it will execute the fallback strategy and not proceed with the next step.

If what the output user wants to see requires the 2nd tool - suggest_outfit() - to be executed, then the tool will be used. The agent looks at the output of suggest_outfit(), if the output is not empty and has the format the user needs to see, it will proceed with the next step with the output given as a parameter to the next tool - if the tool needs to be used. If the output is empty or doesn't have the required format, it will execute the fallback strategy and not proceed with the next step.

The same goes for the 3rd tool - create_fit_card(). If the output is not empty and has the format the user needs to see, it will be returned as the final output. If the output is empty or doesn't have the required format, it will execute the fallback strategy and not return a fit card.

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->
The agent maintains a shared state dictionary throughout a session that gets updated after each tool call. It tracks the following: 
- found_item = the listing returned by search_listings()
- wardrobe = the user's existing pieces, provided at the start of the session
- suggested_outfit = the outfit combination returned by suggest_outfit()
- fit_card = the final shareable caption returned by create_fit_card()
Each tool reads what it needs from this dictionary and writes its output back into it. 

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool                                                                                                                                                      | Failure mode                          | Agent response                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| --------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| search_listings                                                                                                                                           | No results match the query            | The agent first checks if any of the fields match, and if at least one does - not all - it will return "I couldn't find perfectly matching items, but these items are relevant to your criterias.".                                                                                                                                                                                                                                                                           |
| If none of the fields match, the agent will not execute the next step. It will stop and return "Sorry, I couldn't find any items matching your criteria." |
| suggest_outfit                                                                                                                                            | Wardrobe is empty                     | If the wardrobe is empty or no outfit can be suggested, it will return "Sorry, I couldn't find a suitable outfit with your current wardrobe. But here are a few affordable pieces that will go along with your new item: " and returns max of 2 items that matches the new item. The newly returned items HAS to be CHEAP, affordable and at least in GOOD condition. If nothing could be found to suggest an outfit, the agent will stop and will not execute the next tool. |
|                                                                                                                                                           |
| create_fit_card                                                                                                                                           | Outfit input is missing or incomplete | If the outfit data is incomplete of missing, the agent will return "Sorry, I couldn't generate a fit card because the outfit is incomplete."                                                                                                                                                                                                                                                                                                                                  |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->
User query (description, size, max_price, wardrobe)
    │
    ▼
Planning Loop
    │
    ├─► search_listings(description, size, max_price)
    │       │
    │       ├── returns None ───► "Sorry, I couldn't find any items matching
    │       │   (no match)        your criteria."  → STOP
    │       │
    │       │ returns {title, price, platform, condition}  (single best match)
    │       ▼
    │   Session: found_item = search_listings(...)
    │       │
    ├─► suggest_outfit(found_item, wardrobe)
    │       │
    │       ├── wardrobe empty /        "Sorry, I couldn't find a suitable outfit
    │       │   no match found ──────►   with your current wardrobe. But here are
    │       │                            a few affordable pieces that will go along
    │       │                            with your new item: [≤2 cheap, good-condition
    │       │                            items from listings]"
    │       │                                │
    │       │                                ├── affordable items found → STOP
    │       │                                │   (do not call create_fit_card)
    │       │                                └── nothing found → STOP
    │       │
    │       │ outfit_suggestion = "wear X with Y for [vibe] look"
    │       ▼
    │   Session: suggested_outfit = outfit_suggestion
    │       │
    └─► create_fit_card(suggested_outfit, found_item)
            │
            ├── outfit incomplete ──► "Sorry, I couldn't generate a fit card
            │                          because the outfit is incomplete."  → STOP
            │
            │ fit_card = "<Instagram-style caption>"
            ▼
        Session: fit_card = fit_card
            │
            ▼
        Return fit_card to user

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**
This is my prompt that I used when implementing tool 1:

"
I want you to implement search_listings() tool in tools.py. @tools.py  @planning.md 
When implementing it, take the todo list written in comment lines into account. When loading files use load_listings() function available in data_loader.py @utils/data_loader.py   All the details about search_listings() is available in Tools -> Tool 1 part in planning.md. Take Error Handling part of planning.md into account when handling errors/edge cases. Make sure the implementation of search_listings() is matching with the Architecture part of planning.md
"

I used Claude to implement search_listings() tool with the details I filled in planning.md before any implementation.

This is my prompt that I used when implementing tool 2:

"
Okay, now I want you to implement the second tool - suggest_outfit() in @tools.py . Follow the Todo list when implementing the tool and take the Tools -> Tool 2, Error Handling, State Management  and Architechture of  @browser: @planning.md  into account when handling the inputs, outputs, edge cases. For LLM use llama-3.3-70b-versatile model via Groq API. Summarize everything you do at the end of your response
"
I used Claude to implement suggest_outfit() tool with the details I filled in planning.md before any implementation.

**Milestone 4 — Planning loop and state management:**

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
<!-- What does the agent do first? Which tool is called? With what input? -->
Call search_listings("vintage graphic tee under $30", size="", max_price=30), return the output to the user, proceed with the next step if output is not empty. If the output is empty, execute the fallback strategy and DON'T proceed with the next step.

**Step 2:**
<!-- What happens next? What was returned from step 1? What tool is called now? -->
Call suggest_outfit(new_item=<output from step 1>, wardrobe=<user's wardrobe>) - user's wardrobe is fetched from the database of wardrobe_schema.json, return the output to the user and proceed with the next step. If the output is empty, execute the fallback strategy and DON'T proceed with the next step. 

**Step 3:**
<!-- Continue until the full interaction is complete -->
Call create_fit_card(outfit=<output from step 2>, new_item=<output from step 1>), return the output to the user and proceed with the next step. If the output is empty, execute the fallback strategy and DON'T proceed with the next step.

**Final output to user:**
<!-- What does the user actually see at the end? -->
If all outputs from each step is not empty, the final output will be the fit card created in step 3. Otherwise, the final output depends on the step that failed.
