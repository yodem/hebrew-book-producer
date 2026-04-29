---
description: Manage the author's CandleKeep thesis notebook for this book — append a new idea, read the running notebook, or refresh from CandleKeep.
argument-hint: [append|show|refresh] [text...]
---

# /thesis — author thesis notebook (CandleKeep)

Manage a per-project CandleKeep notebook where the author tracks the evolving thinking about the book — running thesis, chapter ideas, voice observations, anti-patterns they want to remember, anecdotes to include, things to come back to.

This is the **knowledge layer** for the author. CandleKeep is the right home for it because:

- It persists across sessions (unlike `.book-producer/memory.md` which is local).
- It's searchable and shareable.
- It accumulates across multiple books — past thinking informs future thinking.

## Pre-flight

- `book.yaml` must have a `thesis_notebook:` field pointing to a CandleKeep item ID.
- If the field is missing, propose creating a new CandleKeep item:
  ```
  ck items create "Thesis Notebook — <book title>" --description "Running notes for the book project"
  ```
  …then write the returned item ID into `book.yaml` under `thesis_notebook:`.

## Sub-commands

### `/thesis append "<text>"`

Append a new entry to the notebook. Format:

```
## YYYY-MM-DD HH:MM
<text>

```

The skill fetches the current notebook from CandleKeep, appends the entry, and pushes it back via `ck items put`.

### `/thesis show`

Print the running notebook.

### `/thesis refresh`

Re-fetch the notebook from CandleKeep into `.ctx/thesis-notebook.md`. Run this at the start of any editing session so agents see the author's latest thinking.

## Hard rules

- **Author-driven.** The thesis notebook is the author's space. Agents may *read* it, but never *write* to it without explicit author instruction. (`/thesis append` is explicit.)
- **No primary religious texts here.** This notebook is for the author's reflections, not for caching Tanakh / Talmud / Rambam — those go through Sefaria.
- **Versioned in CandleKeep.** Every `ck items put` increments the version, so the full history is recoverable.
