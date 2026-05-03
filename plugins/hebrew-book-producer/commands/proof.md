---
description: Proofreading pass (parallel). Runs proofreader pass 1 (pre-typesetting) or pass 2 (post-typesetting) automatically based on .book-producer/state.json. Spawns N proofreader agents in parallel — one per chunk.
argument-hint: [chapter-id]
---

# /proof — proofreading (parallel)

## Pre-flight

1. Verify `book.yaml` and `chapters/` exist.
2. Determine pass: read `.book-producer/state.json`; if any chapter is at stage `typeset`, this is **pass 2**; otherwise **pass 1**.
3. Splitter: ensure `.book-producer/chunks/`. If absent:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/split-manuscript.sh chapters/
```

## Parallel pipeline

Generate `RUN_ID` (e.g., `$(date -u +%Y%m%d-%H%M%S)`).
Determine `PASS_DIR`: `proofreader-pass1` if pass 1, `proofreader-pass2` if pass 2.
Determine `NEXT_STAGE`: pass 1 → `typeset`, pass 2 → `done`.

Spawn one `proofreader` agent **per chunk in a single message**:

```
You are processing chunk <CHUNK_ID> for proofreading pass <PASS>.

Inputs:
  CHUNK_ID = <id>
  CHUNK_PATH = <path>
  RUN_ID = <run-id>
  PASS = <1 or 2>
  NEXT_STAGE = <typeset or done>
  OUT_PATH = .book-producer/runs/<run-id>/<PASS_DIR>/<CHUNK_ID>.changes.json

Follow your session-start checklist exactly. Two passes are non-negotiable; this is pass <PASS>.
```

Concurrency cap 8. Wait for all to return.

## Merge

```bash
mkdir -p .book-producer/runs/${RUN_ID}/${PASS_DIR}
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/merge_changes_per_chunk.py \
  --chunks-dir .book-producer/runs/${RUN_ID}/${PASS_DIR}/ \
  --out .book-producer/runs/${RUN_ID}/${PASS_DIR}/changes.json \
  --agent proofreader \
  --run-id ${RUN_ID}
```

## Render docx

```bash
mkdir -p .book-producer/runs/${RUN_ID}/${PASS_DIR}/docx
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/render_suggestions_docx.py \
  --changes .book-producer/runs/${RUN_ID}/${PASS_DIR}/changes.json \
  --source chapters/ \
  --out .book-producer/runs/${RUN_ID}/${PASS_DIR}/docx/
```

## Conditional skills

- If `book.yaml` has `niqqud: true` → run the `niqqud-pass` skill as a separate sweep AFTER the main parallel proofread (never during).
- If religious primary sources detected → individual proofreader agents verify each reference inline via `mcp__claude_ai_Sefaria__get_text`; tag `[UNVERIFIED]` on anything that fails to resolve.

## Hebrew summary

```
שלב הגהה (פסקה <PASS>): <N> תיקונים מוצעים.
לסקירה: chapters/chXX.suggestions.docx
המשך: /apply לכל פרק.
```

## Hard rules

- **Two passes are non-negotiable.** Pass 1 before typesetting; pass 2 after typesetting (run `/proof` again).
- **Idea-flags are NEVER auto-fixed.** They surface in the rendered docx as comments for human review.
- **Never write to `.book-producer/state.json`** — production-manager owns that file.
