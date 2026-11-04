---
description: Manage the author's Trove thesis notebook for this book — append a new idea, read the running notebook, or refresh from Trove.
argument-hint: [append|show|refresh] [text...]
---

# /thesis — author thesis notebook (Trove)

Manage a per-project Trove notebook where the author tracks the evolving thinking about the book — running thesis, chapter ideas, voice observations, anti-patterns they want to remember, anecdotes to include, things to come back to.

This is the **knowledge layer** for the author. Trove is the right home for it because:

- It persists across sessions (unlike `.book-producer/memory.md` which is local).
- It's searchable and shareable.
- It accumulates across multiple books — past thinking informs future thinking.

## Pre-flight

- `book.yaml` must have a `thesis_notebook:` field pointing to a Trove item ID.
- If the field is missing, propose creating a new Trove item:
  ```
  trove items create "Thesis Notebook — <book title>" --description "Running notes for the book project" --json --no-session
  ```
  …then write the returned item ID into `book.yaml` under `thesis_notebook:`.

## Sub-commands

### `/thesis append "<text>"`

Append a new entry to the notebook. Format:

```
## YYYY-MM-DD HH:MM
<text>

```

The skill appends the entry with `trove items append <id> --file <entry.md> --no-session` (no need to re-send the whole notebook).

### `/thesis show`

Print the running notebook.

### `/thesis refresh`

Re-fetch the notebook from Trove into `.ctx/thesis-notebook.md` (`bash "${CLAUDE_PLUGIN_ROOT}/scripts/trove-fetch.sh" <id> .ctx/thesis-notebook.md`). Run this at the start of any editing session so agents see the author's latest thinking.

## Hard rules

- **Author-driven.** The thesis notebook is the author's space. Agents may *read* it, but never *write* to it without explicit author instruction. (`/thesis append` is explicit.)
- **No primary religious texts here.** This notebook is for the author's reflections, not for caching Tanakh / Talmud / Rambam — those go through Sefaria.
- **Versioned in Trove.** Every write increments the version; `trove items history <id>` lists them and `trove items restore` brings one back.
