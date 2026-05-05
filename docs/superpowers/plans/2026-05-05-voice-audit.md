# Voice Infrastructure Audit — hebrew-book-producer
**Date:** 2026-05-05
**Phase:** 0.1 — Pre-work before voice-profile v1 implementation

---

## Summary

`hebrew-book-producer` has the richest existing voice surface of the two projects: a `voice-miner` agent (the primary fingerprint builder), two voice-related skills (`voice-preserver` and `express-voice`), and `book-bootstrap` (the project scaffolder that calls `express-voice` in Step 5). Additionally there are supporting files: `scripts/voice-interview.md`, `references/templates/author-voice-template.md`, `references/templates/author-voice-skeleton.md`, and `references/templates/profile-stub.json`. The user-facing command is `/init-voice`.

The current design writes `AUTHOR_VOICE.md` locally. The v1 design moves voice storage to CandleKeep (structured pages). The existing `voice-miner` already has partial CandleKeep output logic (IDs written to `book.yaml`), making it the closest existing file to the v1 contract.

---

## `plugins/hebrew-book-producer/agents/voice-miner.md`

- **Status:** rewrite to v1 contract (Phase 2). Same name, new I/O.
- **Inputs:**
  - `book.yaml` — project metadata (genre, title, niqqud, author_profile IDs)
  - `past-books/` — past book files for heavy path (≥1 file triggers full computational fingerprint)
  - In-progress manuscript chapters — for light path (3 sampled chapters)
  - CandleKeep `Hebrew Linguistic Reference` (cached at `.ctx/hebrew-linguistic-reference.md`)
  - `scripts/voice-interview.md` — 10 Hebrew interview questions (light path only)
  - `PIPELINE.md` — session-start contract
- **Outputs (current):**
  - CandleKeep items: Overview, Banned Phrases, Preferred Phrases, Reference Paragraphs, Voice Fingerprint, Chapter Patterns, Source Style, Register Examples (8 pages total)
  - `book.yaml` — updated `author_profile` block with 8 CandleKeep page IDs
  - `.ctx/author-profile.md` — local session cache of overview page
- **Outputs (v1 delta):**
  - Replace the 8-page CandleKeep structure with the v1 AUTHOR_VOICE.md page schema; write IDs to `book.yaml` under the v1 field names
- **Inbound references (grep result):**
  - `plugins/hebrew-book-producer/commands/init-voice.md` — primary user-facing command; delegates directly to voice-miner agent
  - `plugins/hebrew-book-producer/PIPELINE.md` — documents voice-miner in the pipeline manifest (§ voice-miner)
  - `plugins/hebrew-book-producer/CLAUDE.md` — `voice preservation is non-negotiable`; reads from `.ctx/author-profile.md`
  - `plugins/hebrew-book-producer/agents/production-manager.md` — reads author profile
  - `plugins/hebrew-book-producer/workflows/voice-feedback-loop.md` — workflow using voice-miner
  - `plugins/hebrew-book-producer/workflows/full-pipeline.md` — full pipeline workflow
  - `README.md`, `README.he.md`, `CHANGELOG.md`, `USER_GUIDE.he.md` — documentation
  - `docs/superpowers/plans/2026-05-05-voice-profile-v1.md` — plan document
  - `docs/superpowers/plans/2026-05-01-candlekeep-author-profile.md` — predecessor plan
  - `docs/superpowers/specs/2026-05-01-candlekeep-author-profile-design.md` — predecessor spec
  - `docs/superpowers/specs/2026-05-05-voice-profile-design.md` — v1 spec
- **User-facing slash command today:** `/init-voice` — delegates directly to voice-miner.
- **Migration plan:** Rewrite the CandleKeep output section to use the v1 AUTHOR_VOICE.md page schema; update field names in `book.yaml` `author_profile` block; keep the same heavy/light path logic and the same agent name.

---

## `plugins/hebrew-book-producer/skills/voice-preserver/SKILL.md`

- **Status:** deprecate with pointer to `AUTHOR_VOICE.md`.
- **Inputs:**
  - `AUTHOR_VOICE.md` — loaded at session start; banned and preferred phrases indexed
  - Proposed `new_string` from Edit calls
  - CandleKeep `hebrew-author-register` chapter for register classification
- **Outputs:**
  - BLOCK — when proposed edit uses a banned phrase
  - WARN — when proposed edit removes a preferred phrase or shifts register > ±1 step
  - PASS — when no constraint violated
  - No standalone output; acts as a gate inside other agents
- **Inbound references (grep result):**
  - `plugins/hebrew-book-producer/agents/linguistic-editor.md` — invokes voice-preserver before each Edit
  - `plugins/hebrew-book-producer/agents/literary-editor-legacy.md` — legacy reference
  - `plugins/hebrew-book-producer/PIPELINE.md` — documents voice-preserver contract
  - `plugins/hebrew-book-producer/skills/review-style/SKILL.md` — references voice-preserver
  - `plugins/hebrew-book-producer/skills/voice-preserver/references/templates/author-voice-template.md` — template file loaded by this skill
  - `docs/superpowers/plans/2026-05-03-02-docx-suggestion-mode-and-apply.md`, `docs/superpowers/specs/2026-05-02-parallel-lector-and-docx-suggestions-design.md` — planning docs
  - `docs/superpowers/plans/2026-05-05-voice-profile-v1.md`, `docs/superpowers/specs/2026-05-05-voice-profile-design.md` — v1 planning
- **User-facing slash command today:** None. `user-invocable: false`.
- **Migration plan:** Add deprecation notice at top of SKILL.md pointing to `AUTHOR_VOICE.md` as the source of truth; update linguistic-editor to read voice constraints from the v1 AUTHOR_VOICE.md CandleKeep page instead of a local file.

---

## `plugins/hebrew-book-producer/skills/express-voice/SKILL.md`

- **Status:** deprecate with pointer to `AUTHOR_VOICE.md`.
- **Inputs:**
  - Three Hebrew interview questions (asked interactively)
  - Optional manuscript file for computational seeding via `extract-voice-fingerprint.py`
  - CandleKeep `hebrew-author-register` and `hebrew-anti-ai-markers` chapters (via `.ctx/hebrew-linguistic-reference.md`)
  - Template: `references/templates/author-voice-skeleton.md`
  - Stub template: `references/templates/profile-stub.json`
- **Outputs:**
  - `AUTHOR_VOICE.md` — minimum-viable voice file (3 questions answered)
  - `.book-producer/profile.json` — sparse computational seed (if manuscript exists)
- **Inbound references (grep result):**
  - `plugins/hebrew-book-producer/skills/book-bootstrap/SKILL.md` — Step 5 calls express-voice when `AUTHOR_VOICE.md` is missing
  - `plugins/hebrew-book-producer/commands/start.md` — documents express-voice as part of bootstrap flow
  - `plugins/hebrew-book-producer/PIPELINE.md` — documents that `AUTHOR_VOICE.md` is written only by voice-miner / express-voice
  - `plugins/hebrew-book-producer/skills/express-voice/references/templates/author-voice-skeleton.md` — template loaded by this skill
  - `plugins/hebrew-book-producer/skills/express-voice/references/templates/profile-stub.json` — stub loaded by this skill
  - `docs/superpowers/plans/2026-05-05-voice-profile-v1.md`, `docs/superpowers/specs/2026-05-05-voice-profile-design.md`
- **User-facing slash command today:** None. `user-invocable: false`. Invoked only by book-bootstrap.
- **Migration plan:** Add deprecation notice pointing to `AUTHOR_VOICE.md`; in Phase 2 replace the 3-question flow with a call to the light path of the new `voice-miner` agent; update `book-bootstrap` Step 5 to call voice-miner directly.

---

## `plugins/hebrew-book-producer/skills/book-bootstrap/SKILL.md`

- **Status:** modify to invoke the new `voice-miner` in Stage 1 (Step 5 of bootstrap process).
- **Inputs:**
  - Current working directory (project root)
  - Optional pre-existing `book.yaml`, `AUTHOR_VOICE.md`, `.book-producer/`
  - Manuscript files (auto-detected in Steps 1–4)
  - CandleKeep references (loaded in Step 6 via `load-candlekeep-guide.sh`)
- **Outputs:**
  - `book.yaml` — auto-generated project metadata
  - `.book-producer/state.json`, `.book-producer/memory.md`, `.book-producer/snapshots/` — project state
  - `AUTHOR_VOICE.md` — minimum viable voice file (via express-voice in current Step 5)
  - `.book-producer/profile.json` — sparse computational fingerprint (via express-voice)
  - JSON result returned to caller: status, scaffolded files, genre, niqqud, summary
- **Inbound references (grep result):**
  - `plugins/hebrew-book-producer/commands/start.md` — calls book-bootstrap at the start of every `/start <action>`
  - `plugins/hebrew-book-producer/PIPELINE.md` — documents book-bootstrap in pipeline
  - `plugins/hebrew-book-producer/CLAUDE.md` — references `/start` which invokes book-bootstrap
  - `docs/superpowers/plans/2026-05-05-voice-profile-v1.md`, `docs/superpowers/specs/2026-05-05-voice-profile-design.md`
- **User-facing slash command today:** None. `user-invocable: false`. Invoked by `/start`.
- **Migration plan:** Replace Step 5 (`express-voice` call) with a call to the new `voice-miner` agent (light path); update Step 5's output contract to write CandleKeep page IDs to `book.yaml` instead of creating a local `AUTHOR_VOICE.md`.

---

## Additional voice-related files found (not in original list)

### `plugins/hebrew-book-producer/scripts/voice-interview.md`
Contains the 10 Hebrew interview questions used by voice-miner's light path. Will need updating in Phase 2 to align with the v1 interview structure.

### `plugins/hebrew-book-producer/skills/voice-preserver/references/templates/author-voice-template.md`
Template used when generating or validating `AUTHOR_VOICE.md` structure. Deprecate with pointer to v1 CandleKeep page schema.

### `plugins/hebrew-book-producer/skills/express-voice/references/templates/author-voice-skeleton.md`
Skeleton template for minimum-viable `AUTHOR_VOICE.md`. Deprecate with pointer to v1 CandleKeep page schema.

### `plugins/hebrew-book-producer/skills/express-voice/references/templates/profile-stub.json`
Stub for `.book-producer/profile.json` when extraction fails. Keep as fallback; update field names to v1 schema.

### `plugins/hebrew-book-producer/commands/init-voice.md`
User-facing command file for `/init-voice`. Delegates to voice-miner agent. Will need a comment update after voice-miner rewrite but no structural change needed.

### `plugins/hebrew-book-producer/workflows/voice-feedback-loop.md`
Workflow document describing the voice feedback loop. Review in Phase 2 to ensure it references v1 AUTHOR_VOICE.md page structure.

### `plugins/hebrew-book-producer/agents/linguistic-editor.md`
Invokes voice-preserver before every Edit call. In Phase 2, update to read voice constraints directly from the v1 AUTHOR_VOICE.md CandleKeep page.

---

## Decision summary

| File | v1 Decision |
|------|-------------|
| `agents/voice-miner.md` | Rewrite to v1 contract (same name, updated CandleKeep output schema) |
| `skills/voice-preserver/SKILL.md` | Deprecate with pointer to `AUTHOR_VOICE.md` |
| `skills/express-voice/SKILL.md` | Deprecate with pointer to `AUTHOR_VOICE.md`; replace with voice-miner light path call |
| `skills/book-bootstrap/SKILL.md` | Modify Step 5 to invoke voice-miner instead of express-voice |
| `commands/init-voice.md` | Keep; update comment after voice-miner rewrite |
| `scripts/voice-interview.md` | Keep; align with v1 interview structure in Phase 2 |
| `skills/voice-preserver/references/templates/author-voice-template.md` | Deprecate; pointer to v1 CandleKeep page schema |
| `skills/express-voice/references/templates/author-voice-skeleton.md` | Deprecate; pointer to v1 CandleKeep page schema |
| `skills/express-voice/references/templates/profile-stub.json` | Keep as fallback; update field names to v1 schema |
| `agents/linguistic-editor.md` | Update in Phase 2 to read from v1 AUTHOR_VOICE.md CandleKeep page |
| `workflows/voice-feedback-loop.md` | Review and update in Phase 2 |
