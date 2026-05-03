---
description: Run a manuscript appraisal (קריאת לקטור). Splits the manuscript, runs N parallel lector-readers (Sonnet), then a single lector-synthesizer (Opus). Outputs LECTOR_REPORT.md.
argument-hint: <manuscript-file-or-folder> [--no-split] [--resume]
---

# /lector — manuscript appraisal (parallel pipeline)

## Pre-flight

1. Verify `book.yaml` exists. If not — refuse and tell the user to run `/init` first.
2. Verify the argument file or folder exists.
3. The `SessionStart` hook normally caches `.ctx/writers-guide.md` etc. If `.ctx/writers-guide.md` is missing, fall back to `bash ${CLAUDE_PLUGIN_ROOT}/scripts/load-candlekeep-guide.sh`.

## Flag handling

- `--no-split` → invoke the legacy single-shot path: spawn `lector-legacy` agent on the entire manuscript. Skip splitter and synthesizer. Use this only when the parallel path misbehaves.
- `--resume` → if `.book-producer/chunks/` already exists, skip the splitter and reuse existing chunks. Useful for re-runs after fixing chunking.

## Parallel pipeline (default)

### Phase 0 — split

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/split-manuscript.sh "<argument>"
```

If a previous run left `.book-producer/chunks/` and the user did NOT pass `--resume`, the splitter will re-create the chunks (deterministic). If the user passed `--resume`, skip this step.

After splitting, parse `.book-producer/manuscript-index.json` to get the list of chunk IDs.

### Phase 1 — parallel lector-readers

Spawn one `lector-reader` agent **per chunk in a single message** (this is what causes Claude Code to run them concurrently). For each chunk in `manuscript-index.json` chunks[]:

Spawn the `lector-reader` agent with the prompt:

```
You are processing chunk <CHUNK_ID> of a parallel lector run.

Inputs:
  CHUNK_ID = <id>
  CHUNK_PATH = <path>
  INDEX_PATH = .book-producer/manuscript-index.json

Follow your session-start checklist exactly. Write your output to:
  .book-producer/chapter-notes/<CHUNK_ID>.json
```

**Concurrency cap:** if the index has more than 8 chunks, run in waves of 8. Read `splitter.max_parallel` from `book.yaml` if set; default 8.

Wait for all readers to return before proceeding.

### Phase 2 — synthesizer

Spawn **one** `lector-synthesizer` agent with the prompt:

```
You are synthesizing the lector verdict from all chapter notes.

Inputs:
  NOTES_DIR = .book-producer/chapter-notes/
  INDEX_PATH = .book-producer/manuscript-index.json
  OUT_PATH = LECTOR_REPORT.md

Follow your session-start checklist exactly. Read the chapter notes only — do NOT read the chunks themselves. Write your output to LECTOR_REPORT.md.
```

### Phase 3 — summarise to user

Read `LECTOR_REPORT.md`. Print a 5-line Hebrew summary in `.report.md` shape (per `PIPELINE.md`):

```
סוכן: lector-synthesizer
פרק: כל הספר — קריאת לקטור הסתיימה
שינויים: <N עמודי דוח>
שלב הבא: <Go|Go עם תיקונים מהותיים|No-Go>
הערה: <ההערה הראשונה ב-LECTOR_REPORT.md סעיף 7, OR "אין הערות">
```

Then recommend next action based on the verdict:

- If verdict is **Go** → `/edit`
- If verdict is **Go with major revisions** → describe what the author needs to fix first; do NOT auto-proceed.
- If verdict is **No-go** → describe why; offer to discuss before any further work.

## Hard rules

- **Do NOT write prose.** Lector is read-only on the manuscript.
- **Do NOT modify chapters/.** The splitter writes only under `.book-producer/`.
- **Always parallel-spawn readers in a single tool-use message.** Sequential `Agent` calls in separate messages run serially.
- If any reader returns malformed JSON, the synthesizer surfaces it as a quality concern in section 7 — do not fail the whole run.
