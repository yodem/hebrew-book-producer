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

## Phase: Linguistic + Proofreader

(See Plan 4 for parallelizing these. For now, the existing linguistic-editor and proofreader paths run as before.)

## Argument

- No stage argument → run literary parallel pipeline (and continue to linguistic if linguistic stage exists).
- `literary` → only the literary parallel stage.
- `linguistic` → only the linguistic stage.
- A chapter ID (e.g. `ch04`) → constrain to that chapter only.

## Gates

Production-manager invokes Metaswarm `$plan-review-gate` before the literary stage if the gate is installed.

## Report

A single summary at the end:

- Chapters edited.
- Major restructuring decisions.
- Word count delta.
- Next action: `/apply <chapter>` to round-trip reviewed docx, then `/proof`.
