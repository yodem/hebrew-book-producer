# PIPELINE.md — Hebrew Book Producer: Canonical Agent Contracts

**Single source of truth** for the production pipeline. Every agent reads this at session start. Production-manager uses this to validate sub-agent outputs. Editors use this to know exactly what they accept and emit.

---

## Pipeline Diagram

```
manuscript
    │
    ▼
[lector]          ── LECTOR_REPORT.md
    │
    ▼  stage: literary
[literary-editor]  ── LITERARY_NOTES.md + changes.json
    │
    ▼  stage: linguistic
[linguistic-editor] ── LINGUISTIC_NOTES.md + changes.json
    │
    ▼  stage: proofread-1
[proofreader pass 1] ── PROOF_NOTES.md + changes.json
    │
    ▼  stage: typeset
[typesetting-agent]  ── TYPESETTING_BRIEF.md
    │
    ▼  stage: proofread-2-pending
[proofreader pass 2] ── PROOF_NOTES.md (updated) + changes.json
    │
    ▼  stage: done
```

**State names (verbatim):** `drafted` → `literary` → `linguistic` → `proofread-1` → `typeset` → `proofread-2-pending` → `done`

---

## Per-Agent Contract Table

### lector-reader

| Field | Value |
|---|---|
| name | `lector-reader` |
| model | sonnet |
| tools | Read, Grep, Glob, Write |
| reads (input artefacts) | `.book-producer/chunks/<id>.md`, `.book-producer/manuscript-index.json`, `.ctx/writers-guide.md`, `.ctx/hebrew-linguistic-reference.md`, `.ctx/author-profile.md`, `.ctx/lector-reader-instructions.md` |
| writes (output artefacts) | `.book-producer/chapter-notes/<id>.json` (one per spawned instance) |
| emits (state transitions) | None — readers feed the synthesizer; no direct state mutation |
| hard rules | Read the assigned chunk fully; quote verbatim; one JSON out per instance; no verdict; never write `.book-producer/state.json` |

---

### lector-synthesizer

| Field | Value |
|---|---|
| name | `lector-synthesizer` |
| model | opus |
| tools | Read, Grep, Glob, Write |
| reads (input artefacts) | `.book-producer/chapter-notes/*.json`, `.book-producer/manuscript-index.json`, `.ctx/writers-guide.md`, `.ctx/hebrew-linguistic-reference.md`, `.ctx/author-profile.md`, `.ctx/lector-synthesizer-instructions.md` |
| writes (output artefacts) | `LECTOR_REPORT.md` (project root, 7 sections in Hebrew) |
| emits (state transitions) | None — lector is a one-shot gate, not a state-advancing agent |
| hard rules | Read notes only — do NOT read raw chunks; quote verbatim from readers' AI/authorial markers; honest not flattering; one report per project |

---

### lector-legacy (escape hatch)

| Field | Value |
|---|---|
| name | `lector-legacy` |
| model | opus |
| tools | Read, Grep, Glob |
| reads (input artefacts) | `chapters/*.md`, `book.yaml`, `.ctx/*` |
| writes (output artefacts) | `LECTOR_REPORT.md` |
| emits (state transitions) | None |
| hard rules | Use only via `/lector --no-split`. Slow on long manuscripts. |

---

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
| reads (input artefacts) | `chapters/<id>.md`, `AUTHOR_VOICE.md`, `LECTOR_REPORT.md`, `book.yaml`, `.ctx/writers-guide.md`, `.ctx/hebrew-linguistic-reference.md` |
| writes (output artefacts) | Edits `chapters/<id>.md` in place via `Edit`; `LITERARY_NOTES.md`; `changes.json` (every change must include `change_id`, computed via `scripts/changes_id.py`) |
| emits (state transitions) | `{"chapter": "<id>", "next_stage": "linguistic"}` per chapter touched |
| hard rules | Use only via `/edit --no-split`. Slow on long manuscripts. |

---

### linguistic-editor (chunk-mode parallel)

| Field | Value |
|---|---|
| name | `linguistic-editor` |
| model | sonnet |
| tools | Read, Grep, Glob, Write |
| reads (input artefacts) | `.book-producer/chunks/<id>.md`, `AUTHOR_VOICE.md`, `LITERARY_NOTES.md`, `.ctx/writers-guide.md`, `.ctx/hebrew-linguistic-reference.md`, `.book-producer/memory.md` (last 50 lines) |
| writes (output artefacts) | `.book-producer/runs/<run-id>/linguistic-editor/<chunk-id>.changes.json` (per-chunk; merged by `merge_changes_per_chunk.py` into a single `changes.json`) |
| emits (state transitions) | `{"chapter": "<chunk-id>", "next_stage": "proofread-1"}` per chunk |
| hard rules | Runs in parallel chunk-mode (one instance per chunk); never edits the manuscript directly; every change must include `change_id`; never silently rewrite a paragraph; voice wins; the 10% formula is NOT yours; do NOT write `.book-producer/state.json` |

---

### proofreader (chunk-mode parallel)

| Field | Value |
|---|---|
| name | `proofreader` |
| model | sonnet |
| tools | Read, Grep, Glob, Write |
| reads (input artefacts) | `.book-producer/chunks/<id>.md`, `book.yaml`, `.book-producer/state.json` (read-only, to determine pass 1 or pass 2), `.ctx/writers-guide.md`, `.ctx/hebrew-linguistic-reference.md` |
| writes (output artefacts) | `.book-producer/runs/<run-id>/proofreader-pass[1|2]/<chunk-id>.changes.json` (per-chunk; merged into a single `changes.json`) |
| emits (state transitions) | Pass 1: `{"chapter": "<chunk-id>", "next_stage": "typeset"}`; Pass 2: `{"chapter": "<chunk-id>", "next_stage": "done"}` |
| hard rules | Runs in parallel chunk-mode (one instance per chunk); never edits the manuscript directly; every change must include `change_id`; two passes non-negotiable; never touch prose substance; run niqqud-pass ONLY when `book.yaml: niqqud: true` and only AFTER the main pass; do NOT write `.book-producer/state.json` |

---

### typesetting-agent

| Field | Value |
|---|---|
| name | `typesetting-agent` |
| model | sonnet |
| tools | Read, Write, Bash |
| reads (input artefacts) | `${CLAUDE_PLUGIN_ROOT}/skills/hebrew-typography/references/fonts.md`, `${CLAUDE_PLUGIN_ROOT}/skills/hebrew-typography/references/layout-rules.md`, `.ctx/hebrew-linguistic-reference.md`, `book.yaml`, `.book-producer/state.json` |
| writes (output artefacts) | `TYPESETTING_BRIEF.md`, `TYPESETTING_NOTES.md`; triggers state update to `proofread-2-pending` via production-manager signal |
| emits (state transitions) | `{"chapter": "<id>", "next_stage": "proofread-2-pending"}` per chapter typeset |
| hard rules | No PDF rendering — produces specification only; Frank Ruhl Libre is default; even-page chapter starts always; re-trigger proofreader pass 2 after typesetting |

---

### production-manager

| Field | Value |
|---|---|
| name | `production-manager` |
| model | opus |
| tools | Bash, Read, Glob, Agent |
| reads (input artefacts) | `book.yaml`, `.book-producer/state.json`, `AUTHOR_VOICE.md`, `.book-producer/memory.md`, sub-agent `changes.json` outputs |
| writes (output artefacts) | `.book-producer/state.json` (sole writer); `.book-producer/runs/<run-id>/<agent>/` (structured run artefacts) |
| emits (state transitions) | Commits state transitions; never emits upstream — it is the orchestrator |
| hard rules | Never edit prose; always update state after every spawn; read `changes.json` from each sub-agent — if parse fails, log to `.book-producer/runs/<run-id>/errors.log` and degrade to reading the `.md` for human review; do not auto-merge malformed runs |

---

### book-writer

| Field | Value |
|---|---|
| name | `book-writer` |
| model | opus |
| tools | Read, Write, Grep, Glob |
| reads (input artefacts) | `chapters/<id>.brief.md` (mandatory), `AUTHOR_VOICE.md`, `book.yaml`, `.ctx/writers-guide.md`, `.ctx/hebrew-linguistic-reference.md`, `.book-producer/profile.json` |
| writes (output artefacts) | `chapters/<id>.draft.md`, `chapters/<id>.decisions.md` |
| emits (state transitions) | None — book-writer is a pre-pipeline agent; it produces drafts at `stage: drafted` |
| hard rules | Never generate from blank — brief is mandatory; never edit existing prose; one brief, one chapter, one draft; verify Jewish primary sources via Sefaria MCP |

---

### voice-miner

| Field | Value |
|---|---|
| name | `voice-miner` |
| model | opus (heavy path); sonnet (light path) |
| tools | Read, Write, Bash, Grep, Glob |
| reads (input artefacts) | `book.yaml`, `past-books/` (heavy path), current manuscript chapters (light path), `.ctx/hebrew-linguistic-reference.md` |
| writes (output artefacts) | `AUTHOR_VOICE.md` (new project) or `AUTHOR_VOICE.draft.md` (existing project); `.book-producer/profile.json` |
| emits (state transitions) | None — voice-miner runs before the pipeline |
| hard rules | Never invent a banned phrase; never overwrite an existing `AUTHOR_VOICE.md`; heavy path on opus, light path on sonnet |

---

## Handoff Schemas

### `changes.json` — Editor Output Schema

All three editorial agents (literary-editor, linguistic-editor, proofreader) emit `changes.json` alongside their `.md` notes. Production-manager reads this for transparent merging. **See `skills/changes-schema/SKILL.md` for the full JSON Schema fragment and sample objects.**

Top-level shape:

```json
{
  "agent": "literary-editor | linguistic-editor | proofreader",
  "chapter": "<chapter id>",
  "run_id": "<ISO-timestamp run-id>",
  "changes": [ /* array of change objects */ ],
  "state_transition": {"chapter": "<id>", "next_stage": "<state>"},
  "summary": "<5-line Hebrew report>"
}
```

### State Transition Signal

Every editorial agent returns this signal in its final report (not writing it to disk):

```json
{"chapter": "<id>", "next_stage": "<state>"}
```

Valid `next_stage` values (verbatim): `literary`, `linguistic`, `proofread-1`, `typeset`, `proofread-2-pending`, `done`

### `report.md` Shape

Every agent ends its turn with a 5-line Hebrew summary. Format (adapt to role):

```
סוכן: <agent name>
פרק: <chapter id> — <one-line what was done>
שינויים: <N changes applied | N issues flagged>
שלב הבא: <next_stage>
הערה: <ONE open question for the author, OR "אין הערות">
```

---

## Cross-Agent Invariants

These rules apply across the entire pipeline. No single agent can document them alone.

1. **`.book-producer/state.json` is written ONLY by `production-manager`.** Editors emit state-transition signals; they never write this file directly.

2. **`AUTHOR_VOICE.md` is written ONLY by `voice-miner` / `express-voice`.** All other agents read it; none write to it. If an editor wants to record a voice observation, it goes in `LINGUISTIC_NOTES.md` or `LITERARY_NOTES.md`.

3. **File naming:**
   - `chapters/<id>.md` — the live manuscript (edited in place).
   - `chapters/<id>.draft.md` — output of `book-writer` (never edited by editors).
   - `chapters/<id>.brief.md` — author-written input to `book-writer` (never touched by the pipeline).

4. **Sefaria MCP is the sole validator for Jewish primary sources.** No agent invents or paraphrases a Hazal quotation. Unverifiable: tag `[UNVERIFIED — MCP unavailable]` or `[UNVERIFIED]`.

5. **`changes.json` ownership:** editors write it to `.book-producer/runs/<run-id>/<agent>/changes.json`; production-manager reads and merges it. The file is never written to the project root.

---

## Failure Modes

### `.ctx/` cache is missing

All agents check for `.ctx/` at session start. If the cache is absent:
```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/load-candlekeep-guide.sh
```
The loader is idempotent. Log a warning but do not block the pipeline.

### Sefaria MCP is unavailable

Any agent that would call Sefaria must instead tag the reference:
```
[UNVERIFIED — MCP unavailable]
```
Never invent or paraphrase. Surface in the agent's report so the author can manually validate.

### Sub-agent returns malformed `changes.json`

Production-manager's recovery path:
1. Attempt JSON parse of `changes.json`.
2. If parse fails → log to `.book-producer/runs/<run-id>/errors.log` with the raw content.
3. Degrade to reading the agent's `.md` notes file for human review.
4. Do NOT auto-merge. Surface the error to the user and ask how to proceed.
5. Never crash — the pipeline continues with the remaining agents.
