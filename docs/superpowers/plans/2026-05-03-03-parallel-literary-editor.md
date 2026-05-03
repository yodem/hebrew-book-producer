# Parallel Literary Editor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Parallelize the literary editor using map-then-reduce — N Sonnet `literary-reader` sub-agents per chunk for in-chapter craft, plus one Opus `literary-synthesizer` that ingests both the literary-readers' notes and the lector's chapter notes to make cross-chapter structural decisions and emit a unified `changes.json`.

**Architecture:** Same shape as the parallel lector (Plan 1) but with a different deliverable: literary-editor produces edits, not a verdict. The synthesizer is the only writer of `changes.json`. The output flows through Plan 2's docx renderer so the author reviews per-chapter in Word.

**Tech Stack:** Same as Plan 1 (bash, Python, ck CLI, yq, Claude Code Agent tool). No new dependencies.

**Spec reference:** `docs/superpowers/specs/2026-05-02-parallel-lector-and-docx-suggestions-design.md` § Component 4.

**Depends on:** Plans 1 and 2. Specifically: splitter, instruction loader, docx renderer, change_id schema.

**Plugin root:** `plugins/hebrew-book-producer/`.

---

## File Structure

```
plugins/hebrew-book-producer/
├── agents/
│   ├── literary-reader.md             (NEW — Sonnet, parallel chunk reader)
│   ├── literary-synthesizer.md        (NEW — Opus, single-instance)
│   └── literary-editor-legacy.md      (RENAMED from agents/literary-editor.md)
├── commands/
│   └── edit.md                        (MODIFIED — wire literary stage to parallel pipeline)
└── PIPELINE.md                        (MODIFIED — replace literary-editor contract)

(per-project, runtime)
.book-producer/
└── literary-notes/chXX.json           (NEW — per-chunk literary candidates)
```

**File responsibilities:**
- `literary-reader.md` — one chunk in, one literary-notes JSON out. No final edits — only candidates.
- `literary-synthesizer.md` — reads all literary-notes + lector chapter-notes + manuscript-index; emits unified `changes.json` (literary-editor agent in PIPELINE terms).
- `literary-editor-legacy.md` — the old single-shot literary editor, kept as `--no-split` escape hatch.

---

## Pre-Flight (Task 0)

### Task 0: Verify dependencies

- [ ] **Step 1: Confirm Plans 1 and 2 are merged**

Run: `ls plugins/hebrew-book-producer/scripts/split_manuscript.py plugins/hebrew-book-producer/scripts/render_suggestions_docx.py plugins/hebrew-book-producer/scripts/changes_id.py`
Expected: All three exist.
If not: complete the missing plan first.

- [ ] **Step 2: Confirm parallel lector is operational**

Run: `ls plugins/hebrew-book-producer/agents/lector-reader.md plugins/hebrew-book-producer/agents/lector-synthesizer.md`
Expected: Both exist. The literary-synthesizer reads `.book-producer/chapter-notes/` produced by the parallel lector.

---

## Task 1: Rename existing `literary-editor` to legacy

**Files:**
- Rename: `plugins/hebrew-book-producer/agents/literary-editor.md` → `plugins/hebrew-book-producer/agents/literary-editor-legacy.md`

- [ ] **Step 1: Rename**

```bash
git mv plugins/hebrew-book-producer/agents/literary-editor.md plugins/hebrew-book-producer/agents/literary-editor-legacy.md
```

- [ ] **Step 2: Update frontmatter**

In `plugins/hebrew-book-producer/agents/literary-editor-legacy.md`, replace:

```yaml
name: literary-editor
description: Macro-level Hebrew literary editing (עריכה ספרותית). Works on chapter order, narrative arc, character/argument coherence, theme, and pacing. Produces a track-changes draft and a structural notes file. Does NOT do sentence-level grammar — that is the linguistic-editor's job.
```

With:

```yaml
name: literary-editor-legacy
description: Legacy single-shot literary editor. Use ONLY when /edit --no-split is invoked. Reads the entire manuscript in one pass; slow on long books. Prefer literary-reader + literary-synthesizer (parallel pipeline).
```

- [ ] **Step 3: Commit**

```bash
git add plugins/hebrew-book-producer/agents/literary-editor-legacy.md
git commit -m "refactor(agents): rename literary-editor to literary-editor-legacy"
```

---

## Task 2: Create `literary-reader` agent

**Files:**
- Create: `plugins/hebrew-book-producer/agents/literary-reader.md`

- [ ] **Step 1: Write the agent file**

Create `plugins/hebrew-book-producer/agents/literary-reader.md`:

```markdown
---
name: literary-reader
description: Reads ONE chunk and produces structured local-craft notes (in-chapter pacing, candidate cuts, in-chapter promises/payoffs). Spawned in parallel by /edit literary stage. Does NOT make cross-chapter decisions — that is the literary-synthesizer's job.
tools: Read, Grep, Glob, Write
model: sonnet
---

# Literary Reader Agent (קורא ספרותי)

You read **one chunk** and produce **candidate** literary edits — local craft work only. The synthesizer will combine your candidates with those of your peers (and the lector's notes) to produce the final `changes.json`.

## Mandatory session-start checklist

1. Read `${CLAUDE_PLUGIN_ROOT}/PIPELINE.md` (or `.ctx/PIPELINE.md`).
2. Read globally-cached references:
   - `.ctx/writers-guide.md` — Ch. 4 (Story First/Theme After), Ch. 5 (Two-Draft Method), Ch. 8 (Non-Fiction Structure), Ch. 11 (Shapiro).
   - `.ctx/hebrew-linguistic-reference.md` — chapter `hebrew-author-register`.
   - `.ctx/author-profile.md`.
3. Load role-specific instructions from CandleKeep:
   ```bash
   bash ${CLAUDE_PLUGIN_ROOT}/scripts/load-agent-instructions.sh literary_reader
   ```
   Then `Read .ctx/literary-reader-instructions.md` (fall back to session-cached refs if stub).
4. Read your assigned chunk (`$CHUNK_PATH`).
5. Read `.book-producer/manuscript-index.json` for context.
6. **If `.book-producer/chapter-notes/<your-chunk-id>.json` exists** (from a prior lector run), read it — it tells you what the lector observed about this chunk. Use it to focus your work.

## Inputs (from spawn prompt)

- `CHUNK_ID` — e.g. `ch03`.
- `CHUNK_PATH` — e.g. `.book-producer/chunks/ch03.md`.
- `INDEX_PATH` — `.book-producer/manuscript-index.json`.
- `LECTOR_NOTES_PATH` (optional) — `.book-producer/chapter-notes/<chunk-id>.json` if available.

## Output

Write **exactly one file**: `.book-producer/literary-notes/<CHUNK_ID>.json`.

Schema:

```json
{
  "chunk_id": "ch03",
  "title": "<from index>",
  "in_chapter_observations": "<2-4 sentences in Hebrew on the chapter's coherence, pacing, theme>",
  "candidate_cuts": [
    {
      "line_start": 42,
      "line_end": 51,
      "rationale": "<short Hebrew>",
      "before": "<verbatim excerpt — first 200 chars>",
      "severity": "minor | moderate | major"
    }
  ],
  "candidate_local_moves": [
    {
      "line_start": 100,
      "line_end": 130,
      "to_after_line": 60,
      "rationale": "<short Hebrew>"
    }
  ],
  "in_chapter_promises": [
    {"promise": "<what the chapter promises>", "paid": true|false, "where": "<line range>"}
  ],
  "pacing_notes": "<1-2 sentences>",
  "candidate_changes": [
    {
      "type": "structural | cut | move | TK | voice-flag | idea-flag",
      "level": "letter | word | sentence | idea",
      "line_start": 42,
      "line_end": 51,
      "before": "<verbatim>",
      "after": "<proposed>",
      "rationale": "<short Hebrew>"
    }
  ]
}
```

The `candidate_changes` array is the synthesizer's main input. Each entry follows the changes-schema shape **except** it does NOT include `change_id` (the synthesizer assigns those when promoting candidates to final changes).

## Hard rules

- **Local craft only.** Do not make cross-chapter decisions (chapter order, repetition between chapters, arc-level promise/payoff). Those are the synthesizer's exclusive territory.
- **Do not write `changes.json`.** You write `literary-notes/<CHUNK_ID>.json` only.
- **Voice wins.** If a candidate edit conflicts with `.ctx/author-profile.md`, mark it `voice-flag` and let the synthesizer decide.
- **Quote verbatim.** All `before` strings come from the chunk literally.
- **Hebrew prose throughout.** Field names English, values Hebrew.
- **Never write to `.book-producer/state.json`.**
```

- [ ] **Step 2: Verify**

Run: `head -8 plugins/hebrew-book-producer/agents/literary-reader.md`
Expected: Frontmatter with `name: literary-reader`, `model: sonnet`.

- [ ] **Step 3: Commit**

```bash
git add plugins/hebrew-book-producer/agents/literary-reader.md
git commit -m "feat(agents): add literary-reader (Sonnet, parallel chunk reader)"
```

---

## Task 3: Create `literary-synthesizer` agent

**Files:**
- Create: `plugins/hebrew-book-producer/agents/literary-synthesizer.md`

- [ ] **Step 1: Write the agent file**

Create `plugins/hebrew-book-producer/agents/literary-synthesizer.md`:

```markdown
---
name: literary-synthesizer
description: Reads all literary-readers' candidate notes plus the lector's chapter notes, makes cross-chapter structural decisions (reorder, repetition, arc-level promise/payoff), and emits a single unified changes.json. Single-instance, runs after all literary-readers finish.
tools: Read, Grep, Glob, Write, Bash
model: opus
---

# Literary Synthesizer Agent (סנתזט עורך ספרותי)

You are the senior literary editor. You did not read the manuscript in linear order — your readers handled the local-craft work per chunk. You read **their candidate notes** and **the lector's chapter notes**, then make the cross-chapter decisions only you can make: chapter ordering, repetition between chapters, arc-level promise/payoff, thesis coherence. You emit a single unified `changes.json`.

## Mandatory session-start checklist

1. Read `${CLAUDE_PLUGIN_ROOT}/PIPELINE.md`.
2. Read `${CLAUDE_PLUGIN_ROOT}/skills/changes-schema/SKILL.md` — the canonical shape of your output.
3. Read globally-cached references:
   - `.ctx/writers-guide.md` — Ch. 4, Ch. 5, Ch. 8, Ch. 9, Ch. 11.
   - `.ctx/hebrew-linguistic-reference.md` — chapter `hebrew-author-register`.
   - `.ctx/author-profile.md`.
4. Load role-specific instructions from CandleKeep:
   ```bash
   bash ${CLAUDE_PLUGIN_ROOT}/scripts/load-agent-instructions.sh literary_synthesizer
   ```
   Then `Read .ctx/literary-synthesizer-instructions.md` (fall back to session-cached refs if stub).
5. Read `.book-producer/manuscript-index.json`.
6. Read **every** file under `.book-producer/literary-notes/`. If a note is missing, surface in the report as a quality concern but do not fail.
7. Read **every** file under `.book-producer/chapter-notes/` (lector's notes). Use them to ground your structural decisions in what the lector already observed.

## Inputs (from spawn prompt)

- `LITERARY_NOTES_DIR` — `.book-producer/literary-notes/`.
- `LECTOR_NOTES_DIR` — `.book-producer/chapter-notes/`.
- `INDEX_PATH` — `.book-producer/manuscript-index.json`.
- `RUN_ID` — passed by the orchestrator.
- `OUT_PATH` — `.book-producer/runs/<RUN_ID>/literary-editor/changes.json`.
- `NOTES_OUT_PATH` — `LITERARY_NOTES.md` (project root, Hebrew prose for the author).

## Your work

### Step 1 — promote candidate changes from readers

For each `literary-notes/<chunk-id>.json` file, walk the `candidate_changes` array. For each candidate:
- Decide whether to keep, reword, or reject it.
- Compute the `change_id` via:
  ```bash
  python3 -c "
  import sys
  sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/scripts')
  from changes_id import compute_change_id
  print(compute_change_id('chapters/<chunk-id>.md', <line_start>, '<before>'))
  "
  ```
- Append the kept candidate to your unified `changes` array with `change_id` set.

### Step 2 — add cross-chapter changes

By reading across notes, look for:
- **Repetition between chapters** — emit `cut` changes targeting the weaker passage.
- **Chapter order issues** — emit `move` changes (the schema's `move` type covers cross-chapter relocation).
- **Arc-level promise/payoff** — if Chapter X promises something Chapter Y never pays off, emit `idea-flag` change(s) for human review.
- **Thesis contradictions** — emit `voice-flag` change(s).

For these new cross-chapter changes, compute `change_id` the same way.

### Step 3 — write `changes.json`

```bash
mkdir -p $(dirname "$OUT_PATH")
```

Write to `$OUT_PATH` matching the schema in `skills/changes-schema/SKILL.md`. Top-level shape:

```json
{
  "agent": "literary-editor",
  "chapter": "ALL",
  "run_id": "<RUN_ID>",
  "changes": [ /* unified list with change_id on every entry */ ],
  "state_transition": {"chapter": "ALL", "next_stage": "linguistic"},
  "summary": "<5-line Hebrew report per PIPELINE.md report.md shape>"
}
```

When changes touch multiple chapters, the orchestrator (production-manager) splits them per chapter when invoking the docx renderer.

### Step 4 — write `LITERARY_NOTES.md`

A short Hebrew prose document for the author summarizing your work:
- What you cut and why (top 5 by severity).
- What you reordered and why.
- Open questions (idea-flags, voice-flags) the author must decide.

## Hard rules

- **Notes only when reading per-chunk content.** You may `Grep` the canonical chunks (`.book-producer/chunks/`) for spot-checks (e.g., to verify a `before` string is correct), but do not read them linearly.
- **Every change object MUST have `change_id`.** This is required by the schema and consumed by the docx renderer.
- **Voice wins.** If a candidate conflicts with `.ctx/author-profile.md`, demote to `voice-flag` rather than auto-applying.
- **Three Yeahbuts max per chapter.** (Inherited rule from the legacy literary-editor — the synthesizer doesn't drown the author.)
- **Never write to `.book-producer/state.json`.**
- **Single output.** One `changes.json`, one `LITERARY_NOTES.md`. No per-chunk `changes.json`.
```

- [ ] **Step 2: Verify**

Run: `head -8 plugins/hebrew-book-producer/agents/literary-synthesizer.md`
Expected: Frontmatter with `name: literary-synthesizer`, `model: opus`.

- [ ] **Step 3: Commit**

```bash
git add plugins/hebrew-book-producer/agents/literary-synthesizer.md
git commit -m "feat(agents): add literary-synthesizer (Opus, single-instance, unified changes.json)"
```

---

## Task 4: Update `/edit` command for parallel literary stage

**Files:**
- Modify (or create): `plugins/hebrew-book-producer/commands/edit.md`

The existing `/edit` command may already orchestrate the linguistic + proofreader sequence; we add the literary parallel pipeline upstream of it.

- [ ] **Step 1: Read the existing /edit command**

Run: `cat plugins/hebrew-book-producer/commands/edit.md`

- [ ] **Step 2: Inject the literary parallel stage**

Edit the file. At the top, after pre-flight, insert (or replace the existing literary-editor invocation with) the parallel pipeline:

```markdown
## Phase: Literary (parallel)

If `book.yaml` indicates a literary edit is required (genre is philosophy/autobiography/popular-science, OR the user explicitly invoked `/edit literary`), run the parallel literary pipeline:

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
for f in .book-producer/runs/${RUN_ID}/literary-editor/docx/*.suggestions.docx; do
  ln -sf "$(python3 -c "import os,sys; print(os.path.relpath(sys.argv[1], 'chapters'))" "$f")" "chapters/$(basename "$f")"
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

(unchanged — see Plan 4 for parallelizing these too.)

## Flag handling

- `/edit --no-split` → skip the parallel pipeline; spawn `literary-editor-legacy` on the entire manuscript in one shot.
```

If `commands/edit.md` does not exist or has a fundamentally different structure, replace it entirely with the above (wrapped in YAML frontmatter):

```markdown
---
description: Run the editorial pipeline. Default: parallel literary edit, then linguistic, then proofreader-pass-1.
argument-hint: [literary|linguistic|proofread] [--no-split]
---
```

- [ ] **Step 3: Verify**

Run: `grep -c "literary-reader" plugins/hebrew-book-producer/commands/edit.md`
Expected: `1` or more.

- [ ] **Step 4: Commit**

```bash
git add plugins/hebrew-book-producer/commands/edit.md
git commit -m "feat(commands): /edit literary stage uses parallel readers + synthesizer"
```

---

## Task 5: Update PIPELINE.md

**Files:**
- Modify: `plugins/hebrew-book-producer/PIPELINE.md`

- [ ] **Step 1: Replace the literary-editor contract**

In `PIPELINE.md`, find the `### literary-editor` block. Replace it with three new contract blocks:

```markdown
### literary-reader

| Field | Value |
|---|---|
| name | `literary-reader` |
| model | sonnet |
| tools | Read, Grep, Glob, Write |
| reads (input artefacts) | `.book-producer/chunks/<id>.md`, `.book-producer/manuscript-index.json`, `.book-producer/chapter-notes/<id>.json` (optional, from lector), `.ctx/writers-guide.md`, `.ctx/hebrew-linguistic-reference.md`, `.ctx/author-profile.md`, `.ctx/literary-reader-instructions.md` |
| writes (output artefacts) | `.book-producer/literary-notes/<id>.json` |
| emits (state transitions) | None — readers feed the synthesizer |
| hard rules | Local craft only; never cross-chapter decisions; do NOT write changes.json directly; voice wins; never write `.book-producer/state.json` |

---

### literary-synthesizer

| Field | Value |
|---|---|
| name | `literary-synthesizer` |
| model | opus |
| tools | Read, Grep, Glob, Write, Bash |
| reads (input artefacts) | `.book-producer/literary-notes/*.json`, `.book-producer/chapter-notes/*.json`, `.book-producer/manuscript-index.json`, `.ctx/writers-guide.md`, `.ctx/hebrew-linguistic-reference.md`, `.ctx/author-profile.md`, `.ctx/literary-synthesizer-instructions.md`, `skills/changes-schema/SKILL.md` |
| writes (output artefacts) | `.book-producer/runs/<run-id>/literary-editor/changes.json` (unified, `change_id` on every entry); `LITERARY_NOTES.md` |
| emits (state transitions) | `{"chapter": "ALL", "next_stage": "linguistic"}` |
| hard rules | Notes-first reading; spot-check chunks via Grep only; every change has `change_id`; voice wins (demote to voice-flag rather than auto-apply); three Yeahbuts max per chapter; never write `.book-producer/state.json` |

---

### literary-editor-legacy (escape hatch)

| Field | Value |
|---|---|
| name | `literary-editor-legacy` |
| model | opus |
| tools | Read, Edit, Grep, Glob |
| reads (input artefacts) | (same as old literary-editor) |
| writes (output artefacts) | (same as old literary-editor — but every change MUST now include `change_id`, computed via `scripts/changes_id.py`) |
| emits (state transitions) | Same as old |
| hard rules | Use only via `/edit --no-split`. Slow on long manuscripts. |
```

- [ ] **Step 2: Verify**

Run: `grep -c "^### literary" plugins/hebrew-book-producer/PIPELINE.md`
Expected: `3` (reader, synthesizer, legacy).

- [ ] **Step 3: Commit**

```bash
git add plugins/hebrew-book-producer/PIPELINE.md
git commit -m "docs(pipeline): replace literary-editor contract with reader+synthesizer+legacy"
```

---

## Task 6: End-to-end smoke test

- [ ] **Step 1: Reuse the lector smoke test project**

If you still have `/tmp/lector-smoke` from Plan 1, reuse it. Otherwise:

```bash
TMP=$(mktemp -d)
mkdir -p "${TMP}/chapters"
for i in 01 02 03 04; do
  cat > "${TMP}/chapters/ch${i}.md" <<EOF
# פרק ${i}: כותרת לדוגמה

זהו פרק ${i}. המטרה: לבדוק את העריכה הספרותית המקבילה.
EOF
done
cat > "${TMP}/book.yaml" <<EOF
genre: philosophy
title: "ספר בדיקה"
agent_instructions:
  literary_reader: ""
  literary_synthesizer: ""
EOF
cd "${TMP}"
```

- [ ] **Step 2: Pre-populate splitter + (optionally) lector notes**

```bash
bash /Users/yotamfromm/dev/hebrew-book-producer/plugins/hebrew-book-producer/scripts/split-manuscript.sh chapters
ls .book-producer/chunks/
```

If you want the synthesizer to leverage lector notes, run `/lector chapters` first (from Plan 1). Otherwise the synthesizer will operate from literary-notes only.

- [ ] **Step 3: Run `/edit literary`**

Open Claude Code in the test project. Run `/edit literary`.

Expected:
- 4 `literary-reader` agents spawn in parallel.
- After they finish, 1 `literary-synthesizer` runs.
- `.book-producer/literary-notes/ch01.json` etc. are created.
- `.book-producer/runs/<RUN_ID>/literary-editor/changes.json` is created with every change carrying `change_id`.
- `LITERARY_NOTES.md` is written at project root.
- `.book-producer/runs/<RUN_ID>/literary-editor/docx/chXX.suggestions.docx` files are created.
- Wall-clock: ≤5 minutes for this trivial 4-chapter test.

- [ ] **Step 4: Validate `changes.json` schema**

```bash
python3 - <<'EOF'
import json
data = json.load(open('.book-producer/runs/$(ls .book-producer/runs/ | tail -1)/literary-editor/changes.json'))
for c in data['changes']:
    assert 'change_id' in c, f"missing change_id: {c}"
    assert len(c['change_id']) == 12, f"bad change_id len: {c}"
print(f"validated {len(data['changes'])} changes")
EOF
```

Expected: A line like `validated N changes`. No assertion failures.

- [ ] **Step 5: Round-trip via /apply (optional, depends on Plan 2)**

Open one of the .suggestions.docx in Word, accept some, save as .reviewed.docx, run `/apply ch01`.
Expected: canonical `chapters/ch01.md` updated; decision log written.

- [ ] **Step 6: Update CHANGELOG**

```bash
cd /Users/yotamfromm/dev/hebrew-book-producer
cat >> CHANGELOG.md <<'EOF'

## [Unreleased]

### Added
- Parallel literary editor: N Sonnet `literary-reader`s per chunk + 1 Opus `literary-synthesizer`. Synthesizer ingests lector chapter notes for grounded cross-chapter decisions and emits unified changes.json.

### Changed
- `/edit` literary stage now uses the parallel pipeline by default. Pass `--no-split` to fall back to the legacy single-shot path.

### Renamed
- `agents/literary-editor.md` → `agents/literary-editor-legacy.md`.

EOF
git add CHANGELOG.md
git commit -m "docs(changelog): document parallel literary editor"
```

---

## Self-Review

**1. Spec coverage (§ Component 4 of the design):**
- `literary-reader` agent → Task 2 ✅
- `literary-synthesizer` agent → Task 3 ✅
- Synthesizer reads lector chapter-notes → Task 3 ✅ (in agent instructions)
- Unified `changes.json` with `change_id` on every entry → Task 3 ✅
- Cross-chapter `move`/`structural` change types supported → Task 3 ✅ (delegated to existing schema)
- `/edit` orchestration → Task 4 ✅
- Legacy escape hatch → Task 1 ✅
- PIPELINE.md update → Task 5 ✅
- Docx render integration → Task 4 (Step 3) ✅

**2. Placeholder scan:** No "TBD"/"TODO". Where Task 4 references the existing `/edit` command, the step explicitly says "If commands/edit.md does not exist or has a fundamentally different structure, replace it entirely" — that's a contingency, not a placeholder.

**3. Type consistency:**
- `literary-notes/<chunk-id>.json` schema (Task 2) and the synthesizer's reading of it (Task 3) match: both reference `candidate_changes`, `candidate_cuts`, `candidate_local_moves`, `in_chapter_promises`, etc.
- `change_id` is required on every output change (Task 3 hard rules + PIPELINE update in Task 5).
- `RUN_ID` is generated in Task 4 (orchestrator) and consumed by the synthesizer (Task 3 inputs) — same name everywhere.

---

## Acceptance Criteria for Plan 3

- [ ] All 6 tasks completed and committed.
- [ ] `/edit literary` on a real multi-chapter manuscript spawns N readers in parallel + 1 synthesizer; produces unified `changes.json` with `change_id` on every entry.
- [ ] `/edit --no-split` still works (falls back to `literary-editor-legacy`).
- [ ] Per-chapter `.suggestions.docx` files render after the synthesizer finishes.
- [ ] Round-trip via `/apply <chapter>` (from Plan 2) successfully updates canonical markdown.
- [ ] Wall-clock for a 14-chapter book ≤ 8 minutes (literary editing is heavier than lector; 8 min vs lector's 5 min target is realistic).
- [ ] CHANGELOG entry committed.
