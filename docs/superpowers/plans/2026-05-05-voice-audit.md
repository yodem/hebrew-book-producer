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

---

## `plugins/hebrew-book-producer/commands/voice.md`

- **Status:** rewrite-or-replace as the v1 `:voice` skill (Phase 9).
- **Inputs:**
  - Last 200 lines of `.book-producer/memory.md` — rolling correction log written by the `post-edit-feedback.sh` hook
  - `book.yaml` `author_profile.*` IDs — CandleKeep page IDs for overview, banned_phrases, preferred_phrases
  - `.ctx/author-profile.md` — in-session working copy of the overview page
- **Outputs:**
  - CandleKeep pages updated in-place (banned_phrases, preferred_phrases, or overview), one item at a time with author approval
  - `.book-producer/memory.md` — processed lines archived to `.book-producer/memory-archive.md`; active log truncated
  - Hebrew confirmation message to author: "עדכנתי X כללים בפרופיל הקולי ב-CandleKeep."
- **Inbound references (grep result):**
  - No file in the plugin currently imports or calls `commands/voice.md` by name (it is user-invoked directly as `/voice`). It does cross-reference `book.yaml: author_profile` IDs and `.book-producer/memory.md`, both of which are also touched by `voice-miner` and the post-edit hook.
  - `plugins/hebrew-book-producer/commands/init.md` — tells the author to run `/voice` (as the profile update command) after project setup
- **User-facing slash command today:** Yes. `/voice` is a live slash command invoked by the author to compact `.book-producer/memory.md` corrections into the CandleKeep author profile.
- **Migration plan:** **CONFLICT: existing `/voice` command must be reconciled with planned `:voice` skill — surface to plan controller.**

  The existing `/voice` command and the planned `:voice` skill (Phase 9) have different purposes and different sub-actions:

  | Aspect | Existing `/voice` | Planned `:voice` skill (Phase 9) |
  |--------|-------------------|----------------------------------|
  | Primary function | Compact correction log from `memory.md` into CandleKeep | Drive 7-session adversarial interview; build full AUTHOR_VOICE.md |
  | Sub-actions | None (single behavior) | `init`, `continue`, `recompress`, `audit`, `quick`, `sync`, `status` |
  | Source of truth | `.book-producer/memory.md` rolling corrections | `.voice/` session transcripts + corpus fingerprint |
  | CandleKeep interaction | Direct item-level push per approved change | Full page-set write via voice-sync utility |
  | User approval granularity | Per candidate rule (y/n/edit) | Per session (review transcript → approve distillation) |

  The correction-compaction behavior of the existing `/voice` command is not represented anywhere in the Phase 9 `:voice` skill spec. It is a complementary workflow, not a duplicate. Recommended resolution: preserve the compaction logic either (a) as a `:voice calibrate` sub-action of the new skill, or (b) as a renamed internal command (`/voice-compact`), so it is not silently lost when Phase 9 lands. The new `:voice init` / `continue` / etc. sub-actions should become the entry point for the full interview workflow, but the correction-log compaction path must survive in some form.

---

## `plugins/hebrew-book-producer/scripts/extract-voice-fingerprint.py`

- **Status:** rewrite to v1 contract (called by voice-miner; needs field-name alignment with new fingerprint.md schema).
- **Inputs:**
  - `--input <path-or-dir>` — one or more text/markdown/PDF/DOCX files; supports `pdfplumber` and `python-docx` with graceful degradation
  - `--output <file.json>` — destination path for the JSON fingerprint
  - `--baseline <ck-cached-md>` (optional) — path to `.ctx/hebrew-linguistic-reference.md`; if present, extracts the baseline JSON block from chapter `08-style-fingerprint-baseline` and emits a contrastive deviation section
- **Outputs:**
  - JSON fingerprint at `--output` path with top-level fields: `version` (currently `"0.3.0"`), `extractedAt`, `inputCharCount`, `hebrewRatio`, `sentenceLevel` (mean/stdev/min/max length, distribution buckets, passiveVoiceFrequency, firstPersonFrequency, topFirstWords, topOpeners, burstiness_score), `vocabulary` (typeTokenRatio, avgWordLength, topContentWords, totalTokens, uniqueTokens), `paragraphStructure` (mean/stdev length, sentencesPerParagraph), `chapterShape` (stub fields — all null), `filesAnalyzed`, and optionally `contrastive` and `baselineVersion`
  - Prints a one-line progress message to stdout: `"Wrote <path> (<N> tokens analysed across <N> files)."`
- **Inbound references (grep result):**
  - `plugins/hebrew-book-producer/agents/voice-miner.md` — primary caller; invokes the script in both heavy path (`past-books/`) and light path (3 sampled chapters)
  - `plugins/hebrew-book-producer/skills/express-voice/SKILL.md` — also calls this script for optional computational seeding when a manuscript file is available
  - `plugins/hebrew-book-producer/skills/book-bootstrap/SKILL.md` — indirectly via express-voice in current Step 5
  - `plugins/hebrew-book-producer/scripts/voice-interview.md` — references the script by name in its usage notes
  - `CHANGELOG.md` — changelog entry for the script
  - `docs/superpowers/plans/2026-05-05-voice-audit.md` — this document (grep match)
- **Migration plan:** The script's output schema uses the same top-level shape as the Academic Helper `style-miner` fingerprint (field-name binary-compatibility is documented in the script's own docstring). The v1 voice-profile plan introduces `fingerprint.md` as the canonical schema. Before Phase 2 lands, align the script's output field names with `fingerprint.md`'s v1 contract: specifically verify that `sentenceLevel`, `vocabulary`, `paragraphStructure`, and `chapterShape` keys match the v1 schema and that `burstiness_score` is renamed if the spec uses a different key. Bump `version` from `"0.3.0"` to `"1.0.0"` once aligned. The `chapterShape` stub fields (currently all `null`) should be implemented or explicitly removed if the v1 schema drops them.

---

## `plugins/hebrew-book-producer/agents/book-writer.md`

- **Status:** modify (load `AUTHOR_VOICE.md` per Phase 12.6 of the plan — inbound consumer).
- **Inputs:**
  - `chapters/<id>.brief.md` — mandatory chapter brief (agent aborts if missing)
  - `.ctx/author-profile.md` — current voice cache; read at session start (`cat .ctx/author-profile.md` in step 4 of checklist)
  - `.book-producer/profile.json` — computational fingerprint (optional; read in step 5)
  - `book.yaml` — genre, target_words, author_profile CandleKeep IDs
  - `.ctx/writers-guide.md`, `.ctx/hebrew-linguistic-reference.md` — style references
  - Deep profile CandleKeep pages loaded on demand: `reference_paragraphs`, `preferred_phrases`, `chapter_patterns`
- **Outputs:**
  - `chapters/<id>.draft.md` — prose draft
  - `chapters/<id>.decisions.md` — decisions audit log
  - 5-line Hebrew summary printed to the orchestrator
- **Inbound references (grep result):**
  - `plugins/hebrew-book-producer/PIPELINE.md` — documents book-writer in pipeline manifest
  - `plugins/hebrew-book-producer/commands/draft.md` — user-facing `/draft` command invokes book-writer
  - `plugins/hebrew-book-producer/commands/help.md` — mentions book-writer
  - `plugins/hebrew-book-producer/.claude-plugin/plugin.json` — agent registration
- **Migration plan:** Per Phase 12.6 of the v1 plan, book-writer must load the v1 `AUTHOR_VOICE.md` profile at session start in place of (or in addition to) `.ctx/author-profile.md`. Currently step 4 of the session-start checklist reads `cat .ctx/author-profile.md` — update this step to also read the v1 AUTHOR_VOICE.md sections (banned phrases, preferred phrases, register examples) once the v1 CandleKeep page schema is finalized. The deep-profile CandleKeep load block (step 4 sub-steps) should be updated to match the v1 field names in `book.yaml: author_profile`.

---

## `plugins/hebrew-book-producer/skills/changes-schema/SKILL.md`

- **Status:** keep (uses `voice-flag` change type; no migration needed).
- **Inputs:**
  - Invoked by editorial agents (literary-editor, linguistic-editor, proofreader) when writing `changes.json` output
  - Invoked by production-manager when validating or merging an incoming `changes.json`
- **Outputs:**
  - Defines the `changes.json` schema contract; no file output of its own
  - Schema includes the `voice-flag` change type: a flag (no auto-apply) that surfaces potential voice violations in `PROOF_NOTES.md` or `LITERARY_NOTES.md` for human review
- **Inbound references (grep result):**
  - `plugins/hebrew-book-producer/PIPELINE.md` — references changes-schema contract
  - `plugins/hebrew-book-producer/agents/literary-synthesizer.md` — uses schema
  - `plugins/hebrew-book-producer/agents/proofreader.md` — uses schema
  - `plugins/hebrew-book-producer/agents/literary-editor-legacy.md` — legacy reference
  - `plugins/hebrew-book-producer/agents/literary-reader.md` — uses schema
  - `plugins/hebrew-book-producer/agents/linguistic-editor.md` — uses schema
- **Migration plan:** No migration needed for v1. The `voice-flag` change type is the correct integration point between the editorial pipeline and the voice subsystem — it surfaces violations without auto-applying changes. After v1 lands, verify that `voice-flag` rationale strings reference `AUTHOR_VOICE.md` sections by name (e.g., "voice-flag: banned phrase — see AUTHOR_VOICE.md § Banned Phrases") so authors can trace flags back to the profile.

---

## `plugins/hebrew-book-producer/commands/init.md`

- **Status:** modify (per plan task 12.6, init invokes new voice-miner).
- **Inputs:**
  - Interactive author answers to 6 questions: title, author name, genre, target word count, citation style, niqqud, deadline
  - `book.yaml: author_profile.overview` ID (checked for existing cross-project profile)
  - CandleKeep (via `ck items get`) for loading existing profile if overview ID is non-empty
- **Outputs:**
  - `book.yaml` — scaffolded with `author_profile` block (all values empty string if no existing profile found)
  - `.book-producer/state.json`, `.book-producer/memory.md`, `.book-producer/snapshots/` — project state directory
  - `.gitignore` entries for `.book-producer/snapshots/`, `.book-producer/memory.md`, `.book-producer/state.json`, `.ctx/`
  - Hebrew confirmation or instruction: either "מצאתי פרופיל קולי קיים" (existing) or "לאחר הגדרת הפרויקט, הרץ /voice כדי לבנות את הפרופיל מהספרים שלך." (new)
- **Inbound references (grep result):**
  - `plugins/hebrew-book-producer/CLAUDE.md` — CLAUDE.md references `/init` indirectly via the natural-language router ("ספר חדש / new book / start a project" → `/start init`)
  - `plugins/hebrew-book-producer/commands/voice.md` — init tells the author to run `/voice` after setup
- **Current voice references in file:** The file currently tells the author to "run `/voice` to build the profile from your books" and explicitly states "Never create a blank AUTHOR_VOICE.md skeleton — the profile lives in CandleKeep, not in a local file." The `author_profile` block in `book.yaml` is described as "populated by voice-miner; empty = no profile yet."
- **Migration plan:** Per plan task 12.6, update init's final report (step 8) to instruct authors to run the new `:voice init` sub-action (Phase 9) instead of the legacy `/voice` command. Update the step 4 existing-profile detection to use the v1 `book.yaml` field names once voice-miner's rewrite (Phase 2) lands. The note "run `/voice` after setup" must be updated to "run `:voice init`" or `:voice quick`" depending on which path suits a new project.

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
| `commands/voice.md` | **CONFLICT — rewrite-or-replace as `:voice` skill (Phase 9); correction-log compaction logic must be preserved as sub-action or renamed command** |
| `scripts/extract-voice-fingerprint.py` | Rewrite to v1 field-name contract; bump version to 1.0.0 |
| `agents/book-writer.md` | Modify to load v1 AUTHOR_VOICE.md per Phase 12.6 |
| `skills/changes-schema/SKILL.md` | Keep; `voice-flag` type is correct; add profile-section reference to rationale strings post-v1 |
| `commands/init.md` | Modify final report to reference `:voice init` / `:voice quick` instead of `/voice` |
