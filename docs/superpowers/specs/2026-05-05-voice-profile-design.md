# Voice Profile Subsystem — Design Spec

**Date:** 2026-05-05
**Scope:** Identical voice-profile subsystem shipped in both `Academic Helper` and `hebrew-book-producer`.
**Inspiration:** [Almaya — Creating AI Voice Profile](https://almaya.ai/blog/creating-ai-voice-profile) (interview → compress → portable markdown).
**Status:** Draft for user review.

---

## 1. Goal

Capture the writer's voice (rhythm, register, refusals, terminology, decision rules, productive contradictions) into a compact markdown profile that loads into every prompt. The profile is shared across both plugins via a single CandleKeep book keyed by writer name, so deepening voice in one plugin enriches the other.

## 2. Non-goals

- Replacing the existing past-articles style miner. It becomes Stage 1 and remains mandatory.
- Project-specific voice files. There is one shared profile with project-tagged sections.
- Versioned snapshots beyond what git and CandleKeep already provide.
- A JSON schema for the profile. All artifacts are markdown.

## 3. Two-stage pipeline

### Stage 1 — past-articles/books miner (mandatory, runs in `:init`)

- Reads the corpus (`past-articles/` for Academic Helper; `chapters/` or `manuscript.md` for hebrew-book-producer).
- Produces `.voice/fingerprint.md` — human-readable markdown extracting style signals from the corpus.
- Synced to CandleKeep.
- Sufficient on its own to start writing. User may stop here.

### Stage 2 — adversarial interview (optional, `:voice` command)

- Seeded by `fingerprint.md`. Interviewer reads it first and asks gap-filling / contradiction-challenging questions, never re-asking what the corpus already proves.
- 7 sessions × ~15 questions, mapping to Almaya's seven categories: Beliefs, Writing Practices, Aesthetics, Personality, Structure, Refusals, Warning Signs.
- Each session question bank has three layers: voice (Almaya-style), terminology (preferred/banned terms, transliteration, citation phrasing), plugin-specific (academic vs non-fiction-book register).
- Bilingual: user replies in whichever language they think in. Phrase bank and banned-words list stay Hebrew; meta-instructions and decision rules stay English.
- Resumable across days. State persisted per session.
- Quick mode (`:voice quick`): adaptive ~30 questions, gap-filling only.

## 4. Per-session feedback loop

After each session ends, before the next begins:

1. Compress the just-finished transcript into a draft section of `profile.md`.
2. Generate a sample paragraph using the *current full profile* on a topic from the writer's past corpus.
3. Show sample + diff against previous profile.
4. Ask 3 calibration questions: "does this sound like you?", "any banned phrase sneak in?", "any rule wrong/missing?".
5. Patch profile based on answers, run rule-coverage mini-audit, sync to CandleKeep.

Effect: writer steers the profile while the interview is fresh; partial completion is immediately useful.

## 5. File layout (both plugins, identical)

```
.voice/
├── profile.md              # compressed 2–5k token, hot path, synced to CandleKeep
├── fingerprint.md          # Stage 1 miner output, human-readable
├── audit.md                # latest auditor scorecard (A + C)
├── .last-synced.md         # common ancestor for 3-way merge with CandleKeep
├── legacy/                 # silent migration archive of legacy artifacts
└── interview/
    ├── 01-beliefs.md
    ├── 02-writing-practices.md
    ├── 03-aesthetics.md
    ├── 04-personality.md
    ├── 05-structure.md
    ├── 06-refusals.md
    └── 07-warning-signs.md
```

## 6. Shared profile structure

A single CandleKeep book `Voice Profile — <writer name>` is the cross-project source of truth. Both plugins pull-merge-push.

```markdown
# Voice Profile — <writer name>

## Core voice (cross-project)
rhythm, register, refusals, phrase bank, decision rules, productive contradictions

## Terminology
preferred/banned terms, transliteration (e.g., חז״ל vs Hazal), citation phrasing

## Academic-specific
thesis style, hedging tolerance, citation density, תקציר conventions, anti-AI thresholds

## Non-fiction-book-specific
chapter rhythm, niqqud policy, dialogue/quotation conventions, register shifts,
Hazal treatment, typesetting defaults
```

Each plugin loads the whole file and weights its project section higher in system prompt.

## 7. Components (identical in both plugins)

| Component | Type | Role |
|---|---|---|
| `voice` skill | user-invocable skill | Top-level `:voice` command; sub-actions init/continue/recompress/audit/quick/sync/status |
| `voice-miner` agent | subagent | Stage 1: reads corpus → writes `fingerprint.md` |
| `voice-interviewer` agent | subagent | Stage 2: runs one session at a time, bilingual, adversarial, project-aware |
| `voice-compressor` agent | subagent | Distills one transcript → draft section of `profile.md` |
| `voice-merger` agent | subagent | Pulls latest from CandleKeep, merges, writes unified `profile.md` |
| `voice-auditor` agent | subagent | A (generation match) + C (rule coverage); writes `audit.md` |
| `voice-calibrator` agent | subagent | Per-session feedback loop: sample + 3 questions + patch |
| `voice-sync` util | shell util | CandleKeep pull-merge-push wrapper |
| `voice-migrate` startup hook | hook | Auto-detects legacy files on session start, migrates silently |
| `questions-academic.md` | data | Stage 2 question bank for Academic Helper |
| `questions-non-fiction.md` | data | Stage 2 question bank for hebrew-book-producer |

## 8. Auditor methodology (A + C)

- **A — Generation match**: auditor uses the profile to generate a paragraph on a topic drawn from a past article, diffs against the real paragraph. Scores: lexical overlap, sentence-length distribution, banned-word violations, phrase-bank usage rate.
- **C — Rule coverage**: every rule in the profile is checked against the corpus; rules with no corpus evidence are flagged.

A and C run as a single pass at session end (rule-coverage only, "mini-audit") and as a full pass after session 7 or `:voice recompress`. Score and weak-category flags written to `audit.md`. Below-threshold scores trigger an offer to re-interview the weak categories.

## 9. Slash-command surface

One verb, sub-actions inferred from natural language:

- `:voice init` — start the 7-session interview from current fingerprint
- `:voice continue` — resume next unfinished session
- `:voice recompress` — re-distill all transcripts + fingerprint into `profile.md`
- `:voice audit` — run the full A+C scorecard
- `:voice quick` — adaptive short path (~30 questions, gap-filling only)
- `:voice sync` — push current `profile.md` to CandleKeep
- `:voice status` — show which sessions are done, current audit score

Existing `:init` continues to handle Stage 1 silently; it does not call `:voice init` automatically.

## 10. CandleKeep sync semantics

- One book per writer, shared across both plugins: `Voice Profile — <writer name>`.
- Pull-merge-push wraps every write. Common ancestor stored in `.voice/.last-synced.md` for 3-way merge on conflict.
- Conflicts surface as `<<<` markers in local `profile.md`; user picks a side; merger writes resolved file and pushes.
- On every session start, plugin pulls latest before loading profile into prompt.
- `ck` CLI missing or unauthed → sync becomes a no-op with one-time warning; resumes automatically once authed.

## 11. Migration of existing voice data

Silent auto-migration on first session start after this ships:

- **Academic Helper**: voice/style sections of `.academic-writer/profile.json` are extracted into `.voice/profile.md` and `.voice/fingerprint.md`. The original `profile.json` is left untouched in place (it remains the source for non-voice meta — field, citation style, tool flags); a pre-migration copy is archived to `.voice/legacy/profile.json`. New code reads `.voice/profile.md` as authoritative for voice; legacy fields in `profile.json` are ignored.
- **hebrew-book-producer**: `AUTHOR_VOICE.md` content seeds `.voice/profile.md`; original archived to `.voice/legacy/AUTHOR_VOICE.md`. References to `AUTHOR_VOICE.md` in agents updated to `.voice/profile.md`. The legacy file is left in place but no longer authoritative.
- Migration hook is idempotent: detects `.voice/.migrated` marker and exits.
- Migration push to CandleKeep: each plugin's first migration uploads its own seed. Because the two plugins migrate complementary content (academic-side fields vs non-fiction-book-side fields), the second migration runs the merger to combine them rather than overwrite. Common ancestor is the empty profile, so the 3-way merge cleanly unions both sides.

## 12. UX summary

**First-time install (no prior data)** — user runs `:init`, drops corpus into expected folder. Stage 1 runs silently. User sees one line: "✓ Voice fingerprint created. Run `:voice` for a deeper profile (recommended)." Done.

**Stage 2 opt-in** — user runs `:voice`. Plugin explains the 7-session structure, offers quick mode, starts session 1. Each question is one message; user answers freely in Hebrew or English. After 15 questions, calibration loop runs (sample + 3 questions). User can stop anytime; `:voice continue` resumes.

**Subsequent sessions** — silent pull-merge from CandleKeep at session start; profile loads into context; writing/editing just works.

**Voice maintenance** — `:voice recompress` after months of new writing. Auditor flags drift; targeted re-interview tops up.

**Things the user never does** — edit JSON, manage transcripts, move legacy files, sync CandleKeep manually, choose between plugins.

## 13. Error handling

| Failure | Behavior |
|---|---|
| Empty/unreadable corpus in Stage 1 | Stub `fingerprint.md` with `needs corpus` flag; warn once; writing not blocked. Stage 2 interviewer asks broader questions. |
| Malformed legacy file in migration | Migrate parseable parts; leave rest in `.voice/legacy/` untouched; write `migration-notes.md`; warn once. |
| `ck` CLI missing/unauthed | `voice-sync` no-op with one-time warning; resumes on next call once authed. |
| CandleKeep merge conflict | 3-way merge via `.last-synced.md`; remaining conflicts surface as `<<<` markers; user picks side. Never silent overwrite. |
| Interviewer crashes mid-session | Transcript appended per question; `:voice continue` resumes at last completed question. |
| Audit score below threshold | Calibrator flags weak categories; offers `:voice continue --category=<name>`. Not an error. |
| User abandons after N sessions | Profile marked `[partial]` in `audit.md`; plugins weight it lower in prompt. |
| Hebrew/English text direction | All artifacts are pure UTF-8 markdown; rendered output uses `direction: auto`. |

## 14. Testing

| Layer | Test |
|---|---|
| Structural | `tests/test_voice_structure.py` asserts `.voice/` layout, agent files exist, question banks parse, slash command registers. |
| Migration | Fixtures with old `profile.json` / `AUTHOR_VOICE.md` → run migrate hook → assert new layout, legacy archive intact, idempotent on re-run. |
| Miner | Hebrew fixture corpus → assert `fingerprint.md` non-empty, expected sections present, no JSON. |
| Interviewer | Mocked LLM transcript → assert session file written, resume picks up at right question, calibrator runs after session end. |
| Compressor + Merger | Snapshot test: fixed transcript + fixed prior profile → stable output across runs at low temperature. |
| Auditor | Known-good vs known-bad profile against corpus → known-good scores higher on both A and C. |
| CandleKeep sync | Mock `ck` CLI → assert pull-merge-push order, conflict markers on divergence, no-op on missing CLI. |
| End-to-end | Full Stage 1 + Stage 2 (3 sessions) on fixture project; assert profile valid, audit has score, no orphaned transcripts. |

## 15. Resolved implementation parameters

**Question bank distribution (per session)**: adaptive 12–18 questions, soft floor 12 / hard cap 18. Seed distribution is category-weighted across three layers (voice / terminology / plugin-specific): Beliefs and Aesthetics lean voice-heavy; Structure and Refusals lean plugin-specific-heavy; Terminology gets a small dedicated subsection (~3 questions) in every session. Interviewer may drop or extend within a session to chase a productive thread, respecting the cap.

**Audit score thresholds (separate axes)**:
- A (generation match) good ≥ 6.5 / weak < 5
- C (rule coverage) good ≥ 8 / weak < 6
- "Needs more data" short-circuit: corpus has < 3 articles OR < 1500 total words OR < 800 words per article on average; auditor writes a "needs corpus" note instead of scoring.
- Below-threshold on either axis surfaces the offending category to the calibrator; the lower-scoring axis is named in the user-facing offer.

**CandleKeep book ID resolution**: ID-with-title-fallback. First push creates the book and saves the ID to `.voice/.candlekeep-id` (gitignored, per-machine cache). Subsequent calls go straight to the ID. On 404 or missing cache file, fall back to title lookup (`Voice Profile — <writer name>`); on hit, repopulate the ID file; on miss, create new and save.

**CandleKeep refresh cadence**:
- **Pull** once at the start of any write/edit run (the first hook in `/...:write`, `/...:edit`, `/...:lector`, `/...:proof`, etc.). One `ck` call per writing session, not per section.
- **Push** only on `:voice` sub-actions that mutate `profile.md` (calibrator patch, recompress, audit-driven update).
- **Plugin session start**: no automatic pull. Cheap, uncluttered.
- **`:voice status`**: explicit pull-and-diff, no write.

**Loading model — what each agent reads**:
- Section writers (per-paragraph, per-section) read `.voice/profile.md` only. Whole file fits in every subagent prompt; no division of the profile into separate files.
- `voice-interviewer` reads `fingerprint.md` (to seed questions) and any prior `profile.md` sections.
- `voice-compressor` reads transcripts under `.voice/interview/`.
- `voice-merger` reads `profile.md` + new draft section + CandleKeep latest (via 3-way with `.last-synced.md`).
- `voice-auditor` reads `profile.md` + corpus.
- `voice-calibrator` reads `profile.md` + corpus + the just-finished session transcript.
- Section writers never read `fingerprint.md`, `audit.md`, transcripts, or any internal cache files.

**CandleKeep contents**: only `profile.md` is synced. The other `.voice/*` files are local rebuild-from-transcripts artifacts, not shared state.

## 16. Out of scope (deferred)

- Multi-writer / team voice profiles.
- Voice-profile diffing UI beyond raw git diff.
- Auto-detection of voice drift between recompressions.
- Profile portability to ChatGPT custom instructions / Gemini (stretch goal: `:voice export --target=chatgpt`).
