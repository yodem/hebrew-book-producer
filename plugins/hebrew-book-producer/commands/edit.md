---
description: Run the literary + linguistic edit pipeline on the manuscript. Literary stage uses parallel readers + synthesizer (map-then-reduce); linguistic stage runs after. Production-manager merges and renders docx for review.
argument-hint: [literary|linguistic|all] [chapter-id] [--no-split]
---

# /edit — editorial pipeline

Run the literary-editor (parallel) and then the linguistic-editor on the manuscript.

## Pre-flight

- `book.yaml` must exist.
- `LECTOR_REPORT.md` must exist with verdict `Go` or `Go with major revisions` (and revisions completed).
- If `LECTOR_REPORT.md` is missing — refuse; tell the user to `/lector` first.

## Flag handling

- `--no-split` → skip the parallel pipeline; spawn `literary-editor-legacy` on the entire manuscript in one shot.

## Phase: Literary (parallel)

If no stage argument or `literary` is passed:

### 0 — splitter

Ensure `.book-producer/chunks/` and `.book-producer/manuscript-index.json` exist. If absent, run:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/split-manuscript.sh chapters/
```

### 1 — parallel literary-readers

Spawn one `literary-reader` agent **per chunk in a single message**. For each chunk in `manuscript-index.json` chunks[], pass:

```
You are processing chunk <CHUNK_ID> of a parallel literary edit.

Inputs:
  CHUNK_ID = <id>
  CHUNK_PATH = <path>
  INDEX_PATH = .book-producer/manuscript-index.json
  LECTOR_NOTES_PATH = .book-producer/chapter-notes/<CHUNK_ID>.json   # optional

Follow your session-start checklist exactly. Write to:
  .book-producer/literary-notes/<CHUNK_ID>.json
```

Concurrency cap: 8 by default; configurable via `splitter.max_parallel` in `book.yaml`. Wait for all readers to return.

### 2 — synthesizer

Generate a `RUN_ID` (ISO timestamp, e.g. `$(date -u +%Y%m%d-%H%M%S)`).

Spawn **one** `literary-synthesizer` agent:

```
You are synthesizing the literary edit from all chunk notes + lector notes.

Inputs:
  LITERARY_NOTES_DIR = .book-producer/literary-notes/
  LECTOR_NOTES_DIR = .book-producer/chapter-notes/
  INDEX_PATH = .book-producer/manuscript-index.json
  RUN_ID = <run-id>
  OUT_PATH = .book-producer/runs/<run-id>/literary-editor/changes.json
  NOTES_OUT_PATH = LITERARY_NOTES.md

Follow your session-start checklist exactly. Write changes.json and LITERARY_NOTES.md only.
```

### 3 — render docx for review

After the synthesizer returns:

```bash
RUN_ID=<the run-id>
mkdir -p .book-producer/runs/${RUN_ID}/literary-editor/docx
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/render_suggestions_docx.py \
  --changes .book-producer/runs/${RUN_ID}/literary-editor/changes.json \
  --source chapters/ \
  --out .book-producer/runs/${RUN_ID}/literary-editor/docx/
```

Expose to author via convenience symlinks:

```bash
mkdir -p chapters
for f in .book-producer/runs/${RUN_ID}/literary-editor/docx/*.suggestions.docx; do
  rel=$(python3 -c "import os,sys; print(os.path.relpath(sys.argv[1], 'chapters'))" "$f")
  ln -sf "$rel" "chapters/$(basename "$f")"
done
```

### 4 — Hebrew summary to user

Print:

```
שלב ספרותי: <N> שינויים מוצעים בכל הספר.
דוח: LITERARY_NOTES.md
לסקירה ב-Word: chapters/chXX.suggestions.docx
המשך: לאחר שתסקרי, רוצי /apply לכל פרק.
```

## Phase: Linguistic (parallel)

After the literary stage completes (or skipping straight here on `/edit linguistic`):

### 0 — splitter

Ensure `.book-producer/chunks/` exists (created by Plan 1's splitter). If not:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/split-manuscript.sh chapters/
```

### 0b — Gemini availability pre-flight (linguistic stage)

Before spawning linguistic-editors, determine run-wide Gemini availability ONCE:

1. Read `AUTHOR_VOICE.md`. If `provider: "gemini"` is set (uncommented) AND `mcp__gemini-api__gemini_edit` is present in your toolset, set `GEMINI_AVAILABLE=true`; otherwise set `GEMINI_AVAILABLE=false`.
2. If `GEMINI_AVAILABLE=false` but `provider: "gemini"` was set, notify the user once:
   > "Gemini tool not available for this session — linguistic-editor will run in Claude mode for all chunks."
3. Pass `GEMINI_AVAILABLE` to every spawn prompt below. This commits the engine choice before any agent runs, preventing mixed-engine output across chunks.

### 1 — parallel linguistic-editors

Generate `RUN_ID` (e.g., `$(date -u +%Y%m%d-%H%M%S)`).

Spawn one `linguistic-editor` agent **per chunk in a single message**. For each chunk in `manuscript-index.json` chunks[], pass:

```
You are processing chunk <CHUNK_ID> for the linguistic edit.

Inputs:
  CHUNK_ID = <id>
  CHUNK_PATH = <path>
  RUN_ID = <run-id>
  OUT_PATH = .book-producer/runs/<run-id>/linguistic-editor/<CHUNK_ID>.changes.json
  GEMINI_AVAILABLE = <true|false>   ← from pre-flight above; if false, skip provider check and use Claude mode

Follow your session-start checklist exactly.
```

Concurrency cap 8 (configurable via `splitter.max_parallel`). Wait for all to return.

### 2 — merge per-chunk outputs

```bash
RUN_ID=<the run-id>
mkdir -p .book-producer/runs/${RUN_ID}/linguistic-editor
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/merge_changes_per_chunk.py \
  --chunks-dir .book-producer/runs/${RUN_ID}/linguistic-editor/ \
  --out .book-producer/runs/${RUN_ID}/linguistic-editor/changes.json \
  --agent linguistic-editor \
  --run-id ${RUN_ID}
```

### 3 — render per-chapter docx

```bash
mkdir -p .book-producer/runs/${RUN_ID}/linguistic-editor/docx
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/render_suggestions_docx.py \
  --changes .book-producer/runs/${RUN_ID}/linguistic-editor/changes.json \
  --source chapters/ \
  --out .book-producer/runs/${RUN_ID}/linguistic-editor/docx/
```

### 4 — Hebrew summary to user

```
שלב לשוני: <N> שינויים מוצעים בכל הספר.
לסקירה ב-Word: chapters/chXX.suggestions.docx
המשך: לאחר שתסקרי, רוצי /apply לכל פרק.
```

## Argument

- No stage argument → run literary parallel pipeline (and continue to linguistic if linguistic stage exists).
- `literary` → only the literary parallel stage.
- `linguistic` → only the linguistic stage.
- A chapter ID (e.g. `ch04`) → constrain to that chapter only.

## Report

A single summary at the end:

- Chapters edited.
- Major restructuring decisions.
- Word count delta.
- Next action: `/apply <chapter>` to round-trip reviewed docx, then `/proof`.
