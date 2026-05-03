# Parallel Lector & Docx Suggestion Mode — Design

**Date:** 2026-05-02
**Scope:** Two independent tasks shipped together because they share a manuscript-splitter foundation.
**Status:** Design — not yet implemented.

---

## Background

The `hebrew-book-producer` plugin currently operates as a sequence of single-shot Opus agents that read entire manuscripts in one go. The `lector` agent has been observed running for 20+ minutes without completing on real-world manuscripts. Editorial agents also write changes to the markdown source directly, leaving the author with markdown diffs as their only review surface — not the Word "track changes" workflow Israeli authors and editors actually use.

This design addresses both pain points:

1. **Task 1 — Parallel lector:** make the lector finish in roughly the wall-clock time of a single chapter, not the whole book.
2. **Task 2 — Docx suggestion mode:** every editorial agent emits a `.docx` with tracked changes + comments so the author can review and accept/reject in Word, with a round-trip back to the canonical markdown.

The same map-then-reduce pattern that fixes the lector is then applied to the **literary editor** — the highest-stakes editorial stage, which previously read the whole book in one shot. Local craft (in-chapter pacing, candidate cuts) runs in parallel chapter readers; cross-chapter structure (reorder, repetition, arc-level promise/payoff) is decided by a single Opus synthesizer that reads the readers' notes and the lector's notes. **The linguistic-editor and proofreader** are even simpler — embarrassingly parallel per chunk, no synthesizer needed.

A shared **manuscript splitter** underpins all of this.

## Goals

- A single `/lector <file>` invocation finishes in roughly the wall-clock time of a single chapter (target: ≤3 min for a 14-chapter book on Sonnet readers, vs. 20+ min today).
- The author never has to manually split their manuscript. They hand over a `.docx`, a `.md`, or a folder.
- After every editorial agent run, the author receives a `chXX.suggestions.docx` they can open in Word, review using the standard Review ribbon, and round-trip back into the project.
- Per-agent instructions live in CandleKeep (the author's knowledge layer) and are pulled on demand by each sub-agent — they are not hardcoded into the plugin.
- The literary editor stage is also parallelized via map-then-reduce — chapter readers + one synthesizer — so structural decisions still see the whole book while the per-chapter craft work runs concurrently.
- The work plan generalizes: the same splitter and parallel pattern feed `/edit` (linguistic stage) and `/proof` without re-design.

## Non-Goals

- Two-way live sync with Google Docs (deferred; would require Google auth setup).
- Real-time collaborative editing in the browser.
- Replacing markdown as the canonical source. Markdown stays the source of truth; docx is a review surface only.
- Automating accept/reject decisions on behalf of the author.

---

## Architecture Overview

```
       ┌─────────────────────────────────┐
       │  User input: file or folder     │
       │  (.docx, .md, chapters/)        │
       └──────────────┬──────────────────┘
                      │
                      ▼
       ┌─────────────────────────────────┐
       │  Manuscript Splitter            │  ← shared utility
       │  scripts/split-manuscript.sh    │
       └──────────────┬──────────────────┘
                      │
            writes:   ▼
       .book-producer/manuscript.md
       .book-producer/manuscript-index.json
       .book-producer/chunks/ch01.md ... chXX.md
                      │
        ┌──────────────┬──────────────────┬─────────────────────┐
        │              │                  │                     │
   /lector flow   /edit (literary)   /edit (linguistic)    /proof
        │              │                  │                     │
        ▼              ▼                  ▼                     ▼
  ┌──────────┐   ┌──────────┐     ┌──────────────┐      ┌──────────┐
  │ N readers│   │ N readers│     │ N editors    │      │ N editors│
  │ Sonnet   │   │ Sonnet   │     │ Sonnet       │      │ Sonnet   │
  │→ notes/  │   │→ notes/  │     │→ changes.json│      │→ changes │
  └─────┬────┘   └─────┬────┘     │  per chunk   │      │  per chnk│
        │              │          └──────┬───────┘      └─────┬────┘
        ▼              ▼                 │                    │
  ┌──────────┐   ┌──────────┐            │                    │
  │ 1 synth  │   │ 1 synth  │            │                    │
  │ Opus     │   │ Opus     │            │                    │
  │→ LECTOR  │   │→ unified │            │                    │
  │  REPORT  │   │  changes │            │                    │
  │  .md     │   │  .json   │            │                    │
  └──────────┘   └────┬─────┘            │                    │
                      │                  │                    │
                      └──────────────────┴────────────────────┘
                                         │
                                         ▼
                              ┌─────────────────────┐
                              │  Docx Renderer      │
                              │  → chXX.suggestions │
                              │     .docx           │
                              └──────────┬──────────┘
                                         │
                               author reviews in Word
                                         │
                                         ▼
                              ┌─────────────────────┐
                              │  /apply <chapter>   │
                              │  → chapters/chXX.md │
                              └─────────────────────┘
```

---

## Component 1 — Manuscript Splitter (shared utility)

### Purpose

Take any manuscript form the user gives us and produce a canonical, chunked representation that all downstream agents share. Runs deterministically; no LLM involved.

### Inputs

One of:
- A `.docx` file (single file).
- A `.md` file (single file).
- A folder of `.md` files (assumed to be one-per-chapter).

### Outputs

```
.book-producer/
├── manuscript.md                   # canonical normalized markdown
├── manuscript-index.json           # chunk metadata
└── chunks/
    ├── ch01.md
    ├── ch02.md
    └── ...
```

`manuscript-index.json` shape:

```json
{
  "$schema_version": "1.0",
  "source_file": "my-book.docx",
  "source_format": "docx",
  "split_strategy": "toc | headings | wordcount",
  "chunks": [
    {
      "id": "ch01",
      "title": "פרק 1: התחלה",
      "path": ".book-producer/chunks/ch01.md",
      "start_offset": 0,
      "end_offset": 4521,
      "word_count": 2810,
      "heading_level": 1
    }
  ]
}
```

### Splitting algorithm (deterministic, in priority order)

1. **Folder input** → use directory listing, sorted by filename. Each file becomes one chunk. Title derived from first heading or filename.
2. **`book.yaml` declares `toc:`** → split by the TOC anchors (must match heading text in the manuscript).
3. **Heading detection** → match Hebrew chapter patterns:
   - `^# `, `^## ` (markdown headings)
   - `^פרק \w+`, `^חלק \w+` (Hebrew chapter words at line start)
   - `^Chapter \w+`, `^Part \w+` (English fallback)
4. **Word-count fallback** → ~3000-word chunks at paragraph boundaries (never split mid-paragraph).

### Format conversion

- `.docx` → markdown via `pandoc -f docx -t markdown --wrap=none`. Output written to `.book-producer/manuscript.md`. Pandoc is added to plugin dependencies (or detected and prompted if absent).
- `.md` → copied to `.book-producer/manuscript.md` (always copy, never symlink — we don't want splitter side-effects on the user's source file).
- Folder → concatenate in TOC order (or alphabetical fallback) to `.book-producer/manuscript.md` with chunk-boundary markers preserved.

### Confirmation prompt

After the splitter runs, the orchestrator (`/lector`, `/edit`, `/proof`) shows the user a one-line Hebrew confirmation:

> "זיהיתי N פרקים אוטומטית. להמשיך, או שתרצה לראות את הרשימה לפני?"

Default = continue. The user can hit Enter or say "המשך". Asking "תראה רשימה" prints the index titles and re-prompts.

### Idempotence and reuse

- If `.book-producer/chunks/` already exists and the `--resume` flag is passed, splitter is skipped and the existing chunks are reused.
- If `.book-producer/manuscript.md` already exists and the source file has the same mtime, splitter short-circuits.
- The splitter never writes to user-provided source files. It only writes under `.book-producer/`.

### Optional CandleKeep upload

If `book.yaml` has `candlekeep_book_id:` set, the splitter optionally pushes `manuscript.md` and `manuscript-index.json` to that book. Off by default; enabled by `--push-candlekeep` flag or by setting `splitter.auto_push: true` in `book.yaml`. This lets future sessions skip the local split step.

---

## Component 2 — Parallel Lector (Task 1)

### Three-phase flow

#### Phase 0: Split

`/lector <file>` calls the splitter (Component 1). Result: a populated `.book-producer/chunks/` directory and `manuscript-index.json`.

#### Phase 1: N parallel `lector-reader` sub-agents

For each chunk in the index, spawn a `lector-reader` sub-agent in parallel. Each receives the chunk path as context and writes a structured note file.

**Agent definition (`agents/lector-reader.md`):**

```yaml
---
name: lector-reader
description: Reads ONE chunk of the manuscript and produces structured notes. Spawned in parallel by /lector. Does NOT produce a verdict — that's the synthesizer's job.
tools: Read, Grep, Glob, Write
model: sonnet
---
```

The agent's session-start checklist:

1. Read `.ctx/writers-guide.md` (cached globally by SessionStart hook).
2. Read `.ctx/hebrew-linguistic-reference.md` (cached globally).
3. Read `.ctx/author-profile.md` (cached globally).
4. **Load lector-reader instructions from CandleKeep on demand:**
   ```bash
   bash ${CLAUDE_PLUGIN_ROOT}/scripts/load-agent-instructions.sh lector_reader
   ```
   Then `Read .ctx/lector-reader-instructions.md`.
5. Read the assigned chunk: `$CHUNK_PATH`.
6. Read `.book-producer/manuscript-index.json` for context about position in the book.

**Output per reader:** `.book-producer/chapter-notes/<chunk-id>.json`:

```json
{
  "chunk_id": "ch03",
  "title": "פרק 3: ...",
  "structural_observations": "...",
  "voice_alignment": "...",
  "ai_markers": ["sentence 1", "sentence 2"],
  "authorial_markers": ["sentence 1", "sentence 2"],
  "register_notes": "...",
  "specific_quotes": [
    {"page_or_offset": 1234, "text": "...", "type": "ai|authorial|register-drift"}
  ],
  "concerns": ["..."],
  "strengths": ["..."]
}
```

#### Phase 2: Single `lector-synthesizer` agent

After all readers finish (the orchestrator awaits them), spawn one `lector-synthesizer` agent. It does **not** re-read the manuscript — it reads only the chapter notes and the index.

**Agent definition (`agents/lector-synthesizer.md`):**

```yaml
---
name: lector-synthesizer
description: Reads chapter notes from parallel lector-readers and produces the unified LECTOR_REPORT.md verdict. Sees notes only, never the raw manuscript.
tools: Read, Grep, Glob, Write
model: opus
---
```

Session-start checklist mirrors lector-reader but loads `lector_synthesizer` instructions from CandleKeep instead.

**Output:** `LECTOR_REPORT.md` in the project root, in the same structure the current lector produces (sections 1–7).

### CandleKeep instruction loader

New script: `scripts/load-agent-instructions.sh`

```bash
#!/usr/bin/env bash
# Usage: load-agent-instructions.sh <agent_key>
# Reads book.yaml -> agent_instructions.<agent_key>, fetches from CandleKeep,
# writes to .ctx/<agent_key>-instructions.md. No-op if already cached.

set -euo pipefail
AGENT_KEY="${1:?usage: load-agent-instructions.sh <agent_key>}"
CACHE_FILE=".ctx/${AGENT_KEY//_/-}-instructions.md"

if [ -f "$CACHE_FILE" ]; then
  exit 0  # already cached, possibly by a sibling parallel agent
fi

INSTR_ID=$(yq ".agent_instructions.${AGENT_KEY}" book.yaml 2>/dev/null || echo "null")
if [ "$INSTR_ID" = "null" ] || [ -z "$INSTR_ID" ]; then
  echo "WARN: no agent_instructions.${AGENT_KEY} in book.yaml; skipping" >&2
  exit 0
fi

mkdir -p .ctx
ck items get "$INSTR_ID" --no-session > "$CACHE_FILE"
```

`book.yaml` gains:

```yaml
agent_instructions:
  lector_reader: <candlekeep-page-id>
  lector_synthesizer: <candlekeep-page-id>
  literary_editor: <candlekeep-page-id>
  linguistic_editor: <candlekeep-page-id>
  proofreader: <candlekeep-page-id>
  docx_renderer: <candlekeep-page-id>
```

The author uploads each instruction page to their CandleKeep "agent instructions" book and pastes the IDs into `book.yaml`. They can edit the pages any time without touching the plugin.

### Concurrency

The orchestrator (`/lector` command body) spawns readers using parallel agent invocations. Cap concurrency at 8 by default (configurable via `splitter.max_parallel: N` in `book.yaml`) to avoid rate-limit issues on large books. If there are more chunks than the cap, run in waves.

Race condition note: parallel readers may simultaneously try to write `.ctx/lector-reader-instructions.md`. The loader script's existence check (`if [ -f "$CACHE_FILE" ]`) handles the common case. For a true race, the worst case is two writers producing identical content — there is no logical inconsistency since they fetch the same CandleKeep ID.

### Backwards compatibility

- The existing `/lector` command keeps the same UX. The user notices only a speedup.
- The original single-shot `agents/lector.md` is preserved as `agents/lector-legacy.md` and invoked when `/lector --no-split` is passed. Escape hatch for debugging.

---

## Component 3 — Docx Suggestion Mode (Task 2)

### What "suggestion mode" means here

After any editorial agent (linguistic-editor, proofreader, literary-editor) writes its `changes.json`, a renderer step produces a Word-readable `.docx` per chapter where:

- Each change appears as a Word **tracked change** (deletion + insertion).
- Each change's `rationale` appears as a Word **comment** anchored to the change.
- Each change is anchored to a hidden Word bookmark named `chg_<change_id>`, allowing precise round-trip on apply.

### Output

For every editorial run, the producer writes:

```
.book-producer/runs/<run-id>/<agent>/
├── changes.json
└── docx/
    ├── ch01.suggestions.docx
    ├── ch02.suggestions.docx
    └── ...
```

The latest run for each chapter is also exposed at the convenience path:

```
chapters/ch01.suggestions.docx -> ../.book-producer/runs/<latest-run>/<agent>/docx/ch01.suggestions.docx
```

(symlink, refreshed on each run; the `chapters/` folder is for the author's convenience.)

### Renderer

New component: `scripts/render-suggestions-docx.py`. Implementation uses `python-docx` to write Word XML directly (we cannot rely on pandoc for this because pandoc cannot author tracked changes — it can only flatten them).

Inputs:
- `chapters/chXX.md` — the canonical markdown for the chapter (pre-change state).
- `.book-producer/runs/<run-id>/<agent>/changes.json` — the proposed changes for this chapter.

Output:
- `.book-producer/runs/<run-id>/<agent>/docx/chXX.suggestions.docx`.

For each change in `changes.json` with `file == "chapters/chXX.md"`:
- Locate the `before` text in the markdown (using `line_start`/`line_end` as a hint, exact-match the `before` string within those lines).
- Wrap the matched range with a `w:bookmarkStart`/`w:bookmarkEnd` named `chg_<change_id>`.
- Replace the range's content with a tracked-changes pair:
  - `w:del` containing the `before` text (attributed to "hebrew-book-producer / <agent>").
  - `w:ins` containing the `after` text (same attribution).
- Insert a `w:commentReference` anchored at the bookmark, with `commentText = rationale`.

`change_id` field is added to the `changes-schema` (already part of the schema implicitly via `run_id` + index, but we make it explicit). Each change object gains `"change_id": "<short-stable-hash>"`. The hash is `sha256(file + line_start + before)[:12]` — stable across re-runs as long as the source line and `before` text don't change.

### Renderer agent vs. plain script

The renderer is a deterministic script, not an agent. It does not reason; it just transforms `changes.json` + markdown → docx. Production-manager calls it after each editorial agent finishes:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/render-suggestions-docx.py \
  --changes .book-producer/runs/<run-id>/<agent>/changes.json \
  --source chapters/ \
  --out .book-producer/runs/<run-id>/<agent>/docx/
```

(If we later need adaptive rendering — e.g., reformatting comments based on author preferences — we'd promote it to an agent. For now, deterministic.)

### Round-trip — `/apply <chapter>`

New command: `commands/apply.md`.

```
/apply <chapter>            # round-trip a single chapter
/apply <chapter> --accept-all  # accept every proposed change without round-tripping
/apply                       # round-trip all chapters with reviewed docx files
```

Round-trip algorithm:

1. **Locate the reviewed docx.** Look for `chapters/chXX.reviewed.docx`. If absent, look for `chapters/chXX.suggestions.docx` with mtime newer than the producer wrote it (= author saved over it). If neither found, error.
2. **Flatten the reviewed docx to markdown.** Use `pandoc --track-changes=accept` to write `.book-producer/round-trip/chXX.reviewed.md`. The accepted changes become plain text; rejected changes are dropped.
3. **Compare against `changes.json`.** For each change in the original `changes.json`:
   - If the `before` text appears at the expected location in `chXX.reviewed.md` → **rejected** (author kept the original).
   - If the `after` text appears → **accepted**.
   - If neither matches → **modified** (author tweaked the proposal).
4. **Detect novel edits.** Run a pandoc diff between `chapters/chXX.md` (canonical pre-change) and `chXX.reviewed.md` (post-author). Any text changes that are **not** explained by an accepted/modified change in `changes.json` are surfaced as novel edits — the author typed something themselves.
5. **Apply to canonical markdown.** Write a new `chapters/chXX.md`:
   - Apply each `accepted` change as `before → after`.
   - Apply each `modified` change as `before → <author's tweaked version from reviewed.md>`.
   - Apply each `novel edit` after author confirmation (Hebrew prompt).
   - Drop `rejected` changes (no-op).
6. **Write a decision log** to `.book-producer/runs/<run-id>/apply-decisions.json`:

   ```json
   {
     "run_id": "<run-id>",
     "chapter": "ch03",
     "applied_at": "2026-05-02T12:00:00Z",
     "accepted": ["chg_abc123", "chg_def456"],
     "rejected": ["chg_ghi789"],
     "modified": [
       {"change_id": "chg_jkl012", "original_after": "...", "author_after": "..."}
     ],
     "novel_edits": [
       {"location": "line 42", "before": "...", "after": "..."}
     ]
   }
   ```

   This feeds `voice-miner` so the system learns what the author rejects and how they tweak proposals.
7. **Show the author a Hebrew summary:**

   > "מתוך 47 שינויים מוצעים: אישרת 31, דחית 9, שינית 7. הוספת בעצמך 3 עריכות נוספות. הקובץ הסופי: `chapters/ch03.md`. רוצה לראות את ההבדל מול הגרסה המקורית?"

### Whole-book export and re-split

For authors who prefer a single file:

- `/export-suggestions` concatenates all `chXX.suggestions.docx` into `manuscript.suggestions.docx`. Each chapter boundary is preserved as a Word section break with a hidden bookmark `chunk_<chunk-id>`.
- `/apply` (no chapter argument) detects `manuscript.reviewed.docx`, splits it back per chunk using the bookmarks, runs the per-chapter apply for each.

### Changes-schema additions

`skills/changes-schema/SKILL.md` schema gets one new required field:

- `change_id` (string) — stable short hash, `sha256(file + line_start + before)[:12]`.

Backwards compatibility: existing `changes.json` files without `change_id` are migrated by production-manager on read (it computes the hash and writes it back).

### Edge cases

- **Pandoc round-trip lossiness.** Mitigated by anchoring all changes via `change_id` and applying them as text edits to the existing markdown. The docx is a review surface; the markdown is canonical.
- **Author edits a change rationale comment.** Comments are read-only from the producer's side — author replies to comments are captured in the decision log under `novel_edits` only if they touch body text.
- **Author deletes a change comment.** No effect on apply — the bookmark remains and the change_id can still be matched. Comment deletion is treated as "author dismissed the rationale," not as accept/reject.
- **Author adds a tracked-change of their own.** Captured as `novel_edit` and surfaced for explicit confirmation.
- **Conflicting changes from multiple agents.** Each agent writes its own `runs/<run-id>/<agent>/docx/`. Production-manager merges across agents in a defined order (proofreader → linguistic → literary, reverse for application). Out-of-scope for this design — handled by existing production-manager logic.

---

## Component 4 — Parallel Literary Editor (map-then-reduce)

The literary editor is the most expensive editorial stage and the one most likely to time out under the current single-shot Opus model. We apply the same map-then-reduce shape used by the lector — the difference is the deliverable: literary-editor produces edits (`changes.json`), not just a verdict.

### Why map-then-reduce works for the literary editor

A literary editor's work splits cleanly into two layers:

| Layer | Local? | Examples |
|---|---|---|
| **In-chapter craft** | Yes | Pacing within the chapter, in-chapter promises/payoffs, candidate cuts, scene-level work |
| **Cross-chapter structure** | No | Chapter order, repetition between chapters, arc-level promise/payoff, thesis coherence, sequencing decisions |

A pure parallel-per-chapter setup misses the cross-chapter layer entirely. Map-then-reduce captures both: parallel readers handle the local layer; a single synthesizer with the full book's notes handles the cross-chapter layer.

### Phase 1: N parallel `literary-reader` agents

For each chunk, spawn a `literary-reader` sub-agent. Each writes a local-craft note file.

**Agent definition (`agents/literary-reader.md`):**

```yaml
---
name: literary-reader
description: Reads ONE chunk and produces structured local-craft notes. Spawned in parallel by /edit. Does NOT make cross-chapter decisions.
tools: Read, Grep, Glob, Write
model: sonnet
---
```

Session-start checklist mirrors `lector-reader` but loads the `literary_reader` instructions page from CandleKeep instead. The reader **also** ingests the matching `chapter-notes/<chunk-id>.json` from the lector run if available — this saves a re-read and grounds the literary work in what the lector already observed.

**Output per reader:** `.book-producer/literary-notes/<chunk-id>.json`:

```json
{
  "chunk_id": "ch03",
  "in_chapter_observations": "...",
  "candidate_cuts": [
    {"line_start": 42, "line_end": 51, "rationale": "..."}
  ],
  "candidate_local_moves": [
    {"line_start": 100, "line_end": 130, "to_after_line": 60, "rationale": "..."}
  ],
  "in_chapter_promises": [{"promise": "...", "paid": true|false}],
  "pacing_notes": "...",
  "candidate_changes": [
    /* draft change objects, not yet finalized */
  ]
}
```

The readers do **not** write `changes.json` directly. They write candidate notes; the synthesizer is the only writer of `changes.json`.

### Phase 2: Single `literary-synthesizer` agent

After all literary-readers finish, spawn one `literary-synthesizer` agent on Opus. It reads:

- All `literary-notes/*.json` (local-craft candidates).
- All `chapter-notes/*.json` from the lector run (the lector's structural observations).
- `manuscript-index.json` (book layout).
- The full canonical `manuscript.md` for cross-chapter spot-checks (it can `Grep`/`Read` ranges as needed; it does not need to read it linearly).

The synthesizer's job:

1. **Promote candidates → finalized changes** for the local-craft layer (it can reject readers' candidates; it can also reword rationales).
2. **Add cross-chapter changes** (`move`, `cut`, `structural`) it identifies by reading across notes.
3. **Resolve duplicates** when two chapters' readers flagged the same problem from different angles.
4. **Emit a single unified `changes.json`** covering both layers.

**Agent definition (`agents/literary-synthesizer.md`):**

```yaml
---
name: literary-synthesizer
description: Reads literary-readers' local notes + lector's chapter notes, plus the manuscript for spot-checks. Emits a single unified changes.json covering local-craft and cross-chapter edits.
tools: Read, Grep, Glob, Write
model: opus
---
```

### Outputs

- `.book-producer/runs/<run-id>/literary-editor/changes.json` (single unified file).
- Rendered docx per chapter via Component 3 — author reviews each chapter's changes in Word.
- `LITERARY_NOTES.md` for `voice-flag` / `idea-flag` items the synthesizer surfaces but doesn't auto-apply (per existing changes-schema rules).

### Per-stage summary

| Stage | Concurrency | Why | Output |
|---|---|---|---|
| `lector` | Map-then-reduce: N readers, 1 synthesizer | Verdict needs whole-book view; reading is local | `LECTOR_REPORT.md` |
| `literary-editor` | Map-then-reduce: N readers, 1 synthesizer | Local craft is per-chapter; structure needs whole-book view | `changes.json` (unified) + per-chapter docx |
| `linguistic-editor` | Embarrassingly parallel: N editors, no synthesizer | Sentence/register decisions are local | `changes.json` per chunk, merged by production-manager + per-chapter docx |
| `proofreader` | Embarrassingly parallel | Typos are local | Same as linguistic |

This design ships **all four** stages' parallelism (lector + literary-editor map-then-reduce, linguistic + proofreader embarrassingly parallel) plus the docx renderer + apply. The four share the same splitter, the same CandleKeep instruction loader, and the same docx round-trip — so the marginal cost of adding linguistic and proofreader parallelism is small once the lector pattern is in place.

---

---

## Implementation Guide

This section grounds the design in the actual CandleKeep books the author already has, the Opus/Sonnet model split that makes parallel agents economical, and the Claude Code agent-spawning patterns the plugin uses today.

### CandleKeep books to use as authoritative references

The author's CandleKeep library already contains everything needed. **Use these IDs directly** — do not re-research the topics:

| CandleKeep book | ID | Used by |
|---|---|---|
| The Writer's Guide: How to Write, Edit, and Proofread a Book | `cmok9h0m10ahik30zt8yt0lt2` | All readers, all synthesizers (already cached as `.ctx/writers-guide.md` by SessionStart hook) |
| Hebrew Linguistic Reference | `cmomjonvy0fdmk30zwef79c48` | linguistic-editor, proofreader, all readers needing Hebrew register/anti-AI checks (already cached as `.ctx/hebrew-linguistic-reference.md`) |
| Building Your Agent Team: A Practitioner's Guide to Multi-Agent AI Systems | `cmnudfue5003rmy0zlxt7ioa1` | **Implementer's reference** — read Chapters 4 (Agent Architecture), 5 (Communication Layer), and Part III (Operations) before writing the orchestrator code |
| Claude Opus 4.7 + Claude Code: Operator's Rulebook | `cmo2kdydq00x1qp0z5ytxf951` | **Implementer's reference** — Chapter 1 (Effort Levels), Chapter 6 (When Opus 4.7 Shines) inform the model split decisions below |
| Inside Claude Code: The Architecture | `cmnft2cot0163qh0zskpzuphq` | **Implementer's reference** — for understanding how Claude Code spawns sub-agents and propagates context |

The implementer should pull these into the working session via:

```bash
ck items get cmnudfue5003rmy0zlxt7ioa1 --no-session > .ctx/agent-team-guide.md
ck items get cmo2kdydq00x1qp0z5ytxf951 --no-session > .ctx/opus-rulebook.md
ck items get cmnft2cot0163qh0zskpzuphq > .ctx/claude-code-architecture.md
```

(`--no-session` matches the pattern already used by the existing SessionStart hook in `scripts/load-candlekeep-guide.sh`.)

### Per-agent CandleKeep instruction pages to create

The author needs to create these pages in CandleKeep (one new "agent instructions" book or scattered across existing books — author's choice). Each page is the **role-specific** working instructions for that agent — distinct from the shared writer's guide.

| Page | Purpose | Mandatory sections |
|---|---|---|
| `lector-reader-instructions` | What a lector-reader looks for in one chunk | Per-chunk note schema, what counts as an AI marker, voice-alignment check, register classification |
| `lector-synthesizer-instructions` | How to write the unified `LECTOR_REPORT.md` from notes only | Verdict criteria, how to weight chapter notes, how to phrase the Hebrew report (sections 1–7) |
| `literary-reader-instructions` | What in-chapter craft work looks like | Pacing rubric, in-chapter promise/payoff, candidate-cut criteria, how to draft change candidates |
| `literary-synthesizer-instructions` | How to merge candidates and add cross-chapter changes | When to reject a candidate, how to detect cross-chapter repetition, when to issue `move`/`structural` change types |
| `linguistic-editor-instructions` | Sentence-level register and word-choice work | Register matching, anti-AI rewrite rules, when to flag voice violations |
| `proofreader-instructions` | Typo and punctuation pass | Hebrew-specific typos, niqqud rules (genre-gated), idea-flag criteria |
| `docx-renderer-instructions` | Optional — only if the renderer becomes an agent later | Comment style, bookmark naming, how to format rationale for Word readers |

After creating each page, the author records its ID in `book.yaml`:

```yaml
agent_instructions:
  lector_reader: <page-id>
  lector_synthesizer: <page-id>
  literary_reader: <page-id>
  literary_synthesizer: <page-id>
  linguistic_editor: <page-id>
  proofreader: <page-id>
  docx_renderer: <page-id>  # optional
```

The `scripts/load-agent-instructions.sh` loader (Component 2) reads this map. Pages can be edited in CandleKeep without touching the plugin source — the `.ctx/<role>-instructions.md` cache is regenerated each session.

### Model split — Opus vs. Sonnet

Per the **Opus 4.7 Operator's Rulebook** (`cmo2kdydq00x1qp0z5ytxf951`), Opus is the right choice when reasoning depth matters more than throughput; Sonnet is the right choice for high-throughput tasks where the work is local and the schema is tight. The map-then-reduce pattern fits this perfectly: map = many Sonnets, reduce = one Opus.

| Agent role | Model | Rationale |
|---|---|---|
| `lector-reader` | **Sonnet** | Local observation per chunk; output is a tightly-schemed note JSON; runs N-way parallel, so cost adds up |
| `lector-synthesizer` | **Opus** | Verdict reasoning across the whole book; runs once; produces nuanced Hebrew prose |
| `literary-reader` | **Sonnet** | Same as lector-reader: local, schemed, N-way parallel |
| `literary-synthesizer` | **Opus** | Cross-chapter structural reasoning is the highest-stakes editorial decision in the pipeline; this is exactly what Chapter 6 of the rulebook calls out as "where Opus shines" |
| `linguistic-editor` (per chunk) | **Sonnet** | Sentence-level register work is well-suited to Sonnet; the linguistic reference book provides the rules |
| `proofreader` (per chunk) | **Sonnet** | Typo/punctuation pass is the most local stage; Sonnet is fine |
| `docx-renderer` | **Not an agent** | Deterministic Python script; no model |

Effort/thinking budgets (per Chapter 1 of the rulebook):

- Sonnet readers/editors: **medium** thinking effort. They have a tight schema and a small input (one chunk).
- Opus synthesizers: **high** thinking effort. They are doing the hard reasoning the entire pipeline depends on.
- Apply round-trip and splitter: **no thinking** — these are deterministic.

### Spawning sub-agents in Claude Code

Per **Inside Claude Code: The Architecture** (`cmnft2cot0163qh0zskpzuphq`) and the existing patterns in `agents/production-manager.md`, sub-agents are spawned via the `Agent` tool. For parallel spawning, the orchestrator **must invoke multiple Agent tool calls in a single tool-use block** — that is what causes Claude Code to run them concurrently. Sequential `Agent` calls in separate turns run serially.

**Pattern for the orchestrator (e.g., `commands/lector.md`):**

```markdown
After splitter completes, spawn one lector-reader per chunk in parallel:

For each chunk in `manuscript-index.json` chunks[], invoke the `lector-reader` 
agent with these inputs:
  - CHUNK_PATH: <chunk path>
  - CHUNK_ID: <chunk id>
  - INDEX_PATH: .book-producer/manuscript-index.json

ALL invocations must be in a single message — do not invoke them one at a time.

After all readers return, invoke the `lector-synthesizer` agent once with:
  - NOTES_DIR: .book-producer/chapter-notes/
  - INDEX_PATH: .book-producer/manuscript-index.json
```

**Concurrency cap.** Claude Code does not currently expose a built-in concurrency limit on parallel agent spawns. The orchestrator implements the cap (`splitter.max_parallel`, default 8) by chunking the chunks list into waves and issuing one wave per turn.

### Tool whitelist per agent

Each sub-agent should have the minimum tool set it needs. This is enforced via the `tools:` frontmatter in the agent definition.

| Agent | Tools | Why |
|---|---|---|
| `lector-reader` | `Read, Grep, Glob, Write` | Reads its chunk + cached refs; writes one note JSON. No `Edit` — readers never modify the manuscript |
| `lector-synthesizer` | `Read, Grep, Glob, Write` | Reads notes + index; writes `LECTOR_REPORT.md`. No `Edit` |
| `literary-reader` | `Read, Grep, Glob, Write` | Same as lector-reader |
| `literary-synthesizer` | `Read, Grep, Glob, Write` | Reads notes + manuscript spot-checks; writes unified `changes.json` |
| `linguistic-editor` | `Read, Grep, Glob, Write` | Writes `changes.json` per chunk. No `Edit` — production-manager applies later |
| `proofreader` | `Read, Grep, Glob, Write` | Same as linguistic-editor |
| `production-manager` | `Read, Edit, Write, Bash, Agent` | Orchestrator: spawns sub-agents, applies merges, calls renderer script |

**Critical rule (per existing `CLAUDE.md`):** sub-agents do **not** write to `.book-producer/state.json`. Only `production-manager` does. This rule extends to the new agents.

### Agent file template (re-usable)

Every new sub-agent file follows this exact shape (adapted from the existing `agents/lector.md`):

```markdown
---
name: <role>
description: <one-sentence what this agent does and where in the pipeline>
tools: Read, Grep, Glob, Write
model: sonnet | opus
---

# <Role Title>

## Mandatory session-start checklist

1. Read `${CLAUDE_PLUGIN_ROOT}/PIPELINE.md` (or `.ctx/PIPELINE.md` if cached).
2. Read globally-cached references:
   - `.ctx/writers-guide.md`
   - `.ctx/hebrew-linguistic-reference.md` (if linguistic work)
   - `.ctx/author-profile.md`
3. Load role-specific instructions from CandleKeep:
   ```bash
   bash ${CLAUDE_PLUGIN_ROOT}/scripts/load-agent-instructions.sh <agent_key>
   ```
   Then `Read .ctx/<agent-key-dashed>-instructions.md`.
4. Read your assigned input(s): `$CHUNK_PATH`, `$NOTES_DIR`, etc.

## Inputs

- <list every env-var or path the orchestrator passes>

## Output

- <exact file path the agent writes>
- <schema reference>

## Hard rules

- <role-specific invariants>
- Never write to `.book-producer/state.json`.
```

The orchestrator passes inputs via the spawning prompt; each sub-agent reads its inputs from the prompt, not from environment variables (Claude Code agents do not inherit env vars from the orchestrator).

### Step-by-step build order

This is the recommended order for the implementer. Each step ends with a runnable, testable artifact:

1. **Splitter prototype** (`scripts/split-manuscript.sh`).
   - Input: a sample `.docx` and `.md`. Output: chunks under `.book-producer/chunks/` and a valid `manuscript-index.json`.
   - Test: round-trip a known book; verify chunk count matches expected TOC.

2. **CandleKeep instruction loader** (`scripts/load-agent-instructions.sh`).
   - Test: with a fake `book.yaml` mapping → confirm the cache file appears under `.ctx/`. With no mapping → confirm it no-ops with a warning.

3. **`lector-reader` agent** (`agents/lector-reader.md`).
   - Smoke-test: spawn one manually on a single chunk; verify the note JSON is well-formed.

4. **`lector-synthesizer` agent** (`agents/lector-synthesizer.md`).
   - Smoke-test: pre-populate `.book-producer/chapter-notes/*.json` from step 3; spawn synthesizer; verify `LECTOR_REPORT.md` matches expected sections 1–7.

5. **Updated `commands/lector.md`** that wires steps 1, 3, 4 together with parallel spawning.
   - Test: end-to-end on a real book; confirm wall-clock <3 min for 14 chapters.
   - Keep `agents/lector-legacy.md` available via `/lector --no-split`.

6. **Docx renderer** (`scripts/render-suggestions-docx.py`).
   - Prototype with `python-docx` writing tracked changes + comments + bookmarks. Verify by opening in Word.
   - Critical: confirm `python-docx` can author `w:ins`/`w:del`/`w:commentReference` correctly. If not, fall back to writing raw OOXML.

7. **Apply command** (`commands/apply.md` + supporting Python).
   - Test: render a docx, manually accept some / reject some / type novel edits / save as `.reviewed.docx`. Run `/apply ch3`. Verify the canonical markdown reflects only the accepted + modified + novel changes, with rejected ones dropped.

8. **`literary-reader` and `literary-synthesizer` agents** (mirror of lector pair). Wire into `commands/edit.md`.

9. **Embarrassingly-parallel wrappers** for `linguistic-editor` and `proofreader`. These are the cheapest because they reuse the splitter and the docx flow with no synthesizer.

10. **Changes-schema migration**: ensure every new `changes.json` includes `change_id`. Add a one-time migration in production-manager for legacy files.

### Things to verify against `Building Your Agent Team`

The implementer should specifically read these chapters of `cmnudfue5003rmy0zlxt7ioa1` before writing the orchestrator:

- **Chapter 4 — Agent Architecture Deep Dive.** Confirms the template-vs-instance pattern (one agent definition file, many parallel instances) and the system-prompt-assembly model. Our design matches this: each `lector-reader` instance is a fresh agent process with its own context.
- **Chapter 5 — The Communication Layer.** Reinforces that sub-agents communicate by writing files in agreed locations, not via shared memory. Our `chapter-notes/`, `literary-notes/`, `changes.json` paths are the file-based message bus.
- **Part III — Operations.** Read for failure handling: a sub-agent dying mid-run leaves a partial note. The synthesizer must handle missing notes (continue without them, flag in the verdict).

### Things to verify against the Opus rulebook

Specifically Chapter 6 ("When Opus 4.7 Shines"):

- Cross-chapter coherence is exactly the kind of "global reasoning" the rulebook says to give Opus.
- Per-chunk register checks are exactly the kind of "local schema work" the rulebook says to give Sonnet.
- The literary-synthesizer's job — taking a flat list of candidate edits and deciding which to keep, which to reorder, which to merge — is the rulebook's canonical use case for Opus's higher reasoning budget.

If the implementer is tempted to put the synthesizer on Sonnet to save cost: don't. The whole pipeline's quality depends on this one decision being well-made. The cost difference per book is small; the quality difference is large.

---

## Sequencing

The two tasks have one shared dependency (the splitter) but otherwise ship independently.

1. **Splitter** (`scripts/split-manuscript.sh`, `manuscript-index.json` schema). Used by every stage.
2. **CandleKeep instruction loader** (`scripts/load-agent-instructions.sh`, `book.yaml` schema addition). Used by every new agent.
3. **Task 1 — parallel lector:** new agents (`lector-reader`, `lector-synthesizer`), updated `commands/lector.md`. Lector-legacy kept as escape hatch.
4. **Task 2 — docx renderer:** `scripts/render-suggestions-docx.py`, integration with production-manager.
5. **Task 2 — apply round-trip:** `commands/apply.md`, decision-log schema.
6. **Changes-schema migration:** add `change_id`, write a one-time migration in production-manager.
7. **Parallel literary editor:** new agents (`literary-reader`, `literary-synthesizer`), updated `commands/edit.md`. Reuses splitter + instruction loader + docx renderer.
8. **Embarrassingly-parallel linguistic and proofreader:** wrap existing agents in per-chunk parallel spawn. Cheapest step because no synthesizer is needed.

Steps 1–6 form Tasks 1 and 2 (the user's explicit asks). Steps 7–8 are the natural follow-ups that fall out for free once 1–6 land. Steps 1 and 2 must land first; everything else can fan out in parallel after that.

---

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Pandoc dependency adds setup friction | Detect on first run; print Hebrew install instructions if missing |
| Splitter mis-detects chapter boundaries | One Hebrew confirmation prompt before spawning readers; user can reject and request `--no-split` |
| Parallel readers hit rate limits | Concurrency cap of 8 by default; configurable per book |
| Docx round-trip drops formatting | Markdown stays canonical; docx is review-only; changes anchored by `change_id` |
| Author sees noisy XML/bookmark IDs in Word | Bookmarks are hidden; only `rationale` text appears in comments |
| Race on `.ctx/<agent>-instructions.md` | Existence check + identical content guarantees no inconsistency |
| Author edits the docx in unexpected ways | "Novel edits" detection surfaces them for explicit confirmation, never silently applied |
| Existing single-shot lector users get surprised | `--no-split` flag preserves old behavior; legacy agent kept as `lector-legacy.md` |

---

## Open Questions Deferred to Implementation

- Exact pandoc invocation flags for Hebrew RTL preservation (will be exercised during build).
- Whether `python-docx` can author Word comments anchored to ranges in the form Word expects (verify on a small prototype before full implementation).
- CandleKeep `ck items get` behavior when an ID is missing or revoked (graceful degradation: warn and continue without the instruction file).

These do not affect the design shape and will be resolved during implementation.

---

## Success Criteria

- `/lector my-book.docx` on a 14-chapter book finishes in ≤3 minutes wall-clock and produces a `LECTOR_REPORT.md` indistinguishable in shape from today's output.
- `/edit ch3` produces `chapters/ch03.suggestions.docx`. The author opens it in Word, sees tracked changes with rationale comments, accepts/rejects, saves, runs `/apply ch3`. The canonical `chapters/ch03.md` reflects only the changes the author accepted, plus any novel edits they typed.
- A new author can swap in custom per-agent instructions by editing pages in their CandleKeep "agent instructions" book — without touching the plugin source.
- The pattern generalizes: adding parallelism to `linguistic-editor` is a one-day task that reuses splitter + docx renderer with no design changes.
