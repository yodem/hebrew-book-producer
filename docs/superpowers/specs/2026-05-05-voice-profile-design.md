# Voice Profile Subsystem — Design Spec (v1)

**Date:** 2026-05-05
**Scope:** Identical voice-profile subsystem shipped in both `Academic Helper` and `hebrew-book-producer`.
**Inspiration:** [Almaya — Creating AI Voice Profile](https://almaya.ai/blog/creating-ai-voice-profile) (interview → compress → portable markdown).
**Status:** v1 design. Reviewed against the original Almaya method; deliberately scope-cut to avoid speculative complexity. Items marked *deferred* are out of v1 by choice, not omission.

---

## 1. Goal

Capture the writer's voice (rhythm, register, refusals, terminology, decision rules, productive contradictions) into a compact markdown profile that loads into every prompt. The profile is shared across both plugins via a single CandleKeep book keyed by writer name, so deepening voice in one plugin enriches the other.

## 2. Non-goals (v1)

- Replacing the existing past-articles style miner. It becomes Stage 1 and remains mandatory.
- Project-specific voice files. There is one shared profile with project-tagged sections.
- Versioned snapshots beyond what git and CandleKeep already provide.
- A JSON schema for the profile. All artifacts are markdown.
- Multi-axis statistical auditor (deferred — see §8).
- Three-way merge for concurrent edits across plugins (deferred — see §10).

## 3. Two-stage pipeline

### Stage 1 — past-articles/books miner (mandatory, runs in `:init`)

- Reads the corpus (`past-articles/` for Academic Helper; `chapters/` or `manuscript.md` for hebrew-book-producer).
- Produces `.voice/fingerprint.md` — human-readable markdown extracting style signals from the corpus.
- Synced to CandleKeep.
- Sufficient on its own to start writing. User may stop here.

### Stage 2 — adversarial interview (optional, `:voice` command)

- Seeded by `fingerprint.md`. Interviewer reads it first and asks gap-filling / contradiction-challenging questions, never re-asking what the corpus already proves.
- 7 sessions × 12–18 questions, mapping to Almaya's seven categories: Beliefs, Writing Practices, Aesthetics, Personality, Structure, Refusals, Warning Signs.
- Each session question bank has three layers: voice (Almaya-style), terminology (preferred/banned terms, transliteration, citation phrasing), plugin-specific (academic vs non-fiction-book register).
- Bilingual: user replies in whichever language they think in. Phrase bank and banned-words list stay Hebrew; meta-instructions and decision rules stay English.
- Resumable across days. State persisted per session.
- Quick mode (`:voice quick`): see §9 for exact behavior.

## 4. Calibration loop (sessions 3 and 7 only)

After session 3 and again after session 7, before continuing or finishing:

1. Distill the latest transcripts into the corresponding sections of `AUTHOR_VOICE.md`.
2. Generate a sample paragraph using the *current full profile* on a topic from the writer's past corpus.
3. Show sample + diff against previous profile.
4. Ask 3 calibration questions: "does this sound like you?", "any banned phrase sneak in?", "any rule wrong/missing?".
5. Patch profile based on answers, run inline rule-coverage check (§8), sync to CandleKeep.

Calibration runs twice (mid-point and final) rather than every session — the user's question budget is finite and the mid-point check catches early drift while the final check validates the full profile. Sessions 1, 2, 4, 5, 6 produce profile updates without calibration; the mid-point and final passes catch any errors that accumulated.

## 5. Sample question content (per category)

Drafted here so the design can be sanity-checked before plumbing is built. Final question banks live in `questions-academic.md` and `questions-non-fiction.md`; these are the seeds.

### Beliefs (voice-heavy)
- *Voice*: "Name one thing 'good academic writing' / 'good non-fiction' is supposed to do that you think is bullshit. Defend the position."
- *Voice*: "What's a stylistic move you respect in writers you disagree with?"
- *Terminology*: "Pick one: חז״ל / Hazal / Chazal / חז\"ל. Now justify it for an audience that uses a different convention."
- *Plugin-specific (academic)*: "When a source contradicts your thesis, do you (a) preempt the objection, (b) bury it in a footnote, (c) cut it, (d) restructure the argument? Pick and explain."
- *Plugin-specific (non-fiction-book)*: "How do you decide whether to quote a religious source in full vs paraphrase?"

### Writing Practices (voice-heavy)
- *Voice*: "Describe what you do in the first 15 minutes of a writing session. Be specific."
- *Voice*: "Show me a sentence from your last article that you'd cut now."
- *Terminology*: "List 5 phrases you use too often. Now decide: keep, kill, or contextualize."
- *Plugin-specific (academic)*: "When you're stuck on a thesis, what's the unblock — a walk, more sources, an outline, a coffee, a specific person to talk to?"
- *Plugin-specific (non-fiction-book)*: "What's your chapter-opening pattern? Anecdote, claim, question, scene?"

### Aesthetics (voice-heavy + plugin-specific)
- *Voice*: "Em-dash, semicolon, or comma — when each? Be specific."
- *Voice*: "Long sentences vs short. What's your default rhythm?"
- *Terminology*: "List 5 words you refuse to use even when correct."
- *Plugin-specific (academic)*: "Hedging: 'arguably' / 'tends to' / 'may suggest' — keep, kill, or quota?"
- *Plugin-specific (non-fiction-book)*: "Frank Ruhl Libre defaults — what do you change about them in practice?"

### Personality (voice-heavy)
- *Voice*: "When you're being honest in writing, what does that *sound* like? Show me a sentence."
- *Voice*: "What does AI-generated writing sound like to you? Three specific tells."
- *Terminology*: "Words that signal 'me being earnest' vs 'me hiding behind formality'."
- *Plugin-specific*: "What's the emotional baseline of your writing — wry, severe, warm, clinical, urgent?"

### Structure (plugin-specific-heavy)
- *Voice*: "How long is your average paragraph? Why?"
- *Plugin-specific (academic)*: "Section count for a 7,000-word article. Defend it."
- *Plugin-specific (academic)*: "Where does the תקציר go? What does it have to do?"
- *Plugin-specific (non-fiction-book)*: "Chapter length range. What forces a split?"
- *Plugin-specific (non-fiction-book)*: "Footnote vs endnote vs inline citation — when each?"
- *Terminology*: "How do you signal a section break that isn't a heading?"

### Refusals (plugin-specific-heavy)
- *Voice*: "What's a sentence you would never write, even if a source demanded it?"
- *Voice*: "Three opening sentences that are immediate cuts."
- *Plugin-specific (academic)*: "Citation patterns that are dishonest dressed as scholarly. Name three."
- *Plugin-specific (non-fiction-book)*: "How do you treat a religious source you personally find objectionable?"
- *Terminology*: "Words that are 'AI-coded' to you. List five."

### Warning Signs (plugin-specific-heavy)
- *Voice*: "When you're writing badly, what's the first thing that goes wrong?"
- *Plugin-specific (academic)*: "Fake-rigor red flags — what reads like scholarship but isn't?"
- *Plugin-specific (non-fiction-book)*: "Sentimentality red flags — what's earned emotion vs manufactured?"
- *Terminology*: "Phrases that signal 'this writer has stopped thinking'."
- *Voice*: "When you re-read something you wrote, what makes you flinch?"

## 6. File layout (both plugins, identical)

```
AUTHOR_VOICE.md             # ROOT — compressed 2–5k token profile, hot path,
                            # synced to CandleKeep, human-editable, in git
.voice/                     # internal artifacts only, gitignored
├── fingerprint.md          # Stage 1 miner output, human-readable
├── audit.md                # latest rule-coverage check
├── .candlekeep-id          # cached CandleKeep book ID (per-machine)
├── .last-update            # "Updated YYYY-MM-DD by <plugin>" stamp
├── legacy/                 # silent migration archive
└── interview/
    ├── 01-beliefs.md
    ├── 02-writing-practices.md
    ├── 03-aesthetics.md
    ├── 04-personality.md
    ├── 05-structure.md
    ├── 06-refusals.md
    └── 07-warning-signs.md
```

`AUTHOR_VOICE.md` lives at the project root in **both** plugins (matches hebrew-book-producer's existing convention; Academic Helper gains a new root file). The writer can hand-edit it. `.voice/` holds only build artifacts.

## 7. Shared profile structure

A single CandleKeep book `Voice Profile — <writer name>` is the cross-project source of truth. Both plugins read/write the same book.

```markdown
# Voice Profile — <writer name>

> Updated 2026-05-05 by hebrew-book-producer

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

Each plugin loads the whole file and weights its project section higher in system prompt. The first line is a pointer stamp (see §10) used as a soft conflict signal.

## 8. Components (4 agents, both plugins)

| Component | Type | Role |
|---|---|---|
| `voice` skill | user-invocable skill | Top-level `:voice` command; sub-actions init/continue/recompress/audit/quick/sync/status |
| `voice-miner` agent | subagent | Stage 1: reads corpus → writes `.voice/fingerprint.md` |
| `voice-interviewer` agent | subagent | Stage 2: runs one session at a time, bilingual, adversarial, project-aware |
| `voice-distiller` agent | subagent | Compresses transcripts and merges into `AUTHOR_VOICE.md` (compressor + merger combined; runs after each session and on `recompress`) |
| `voice-calibrator` agent | subagent | Calibration loop after sessions 3 and 7 only: sample + 3 questions + patch + inline rule-coverage |
| `voice-sync` util | shell util | CandleKeep pull-and-push wrapper |
| `voice-migrate` startup hook | hook | Auto-detects legacy files on session start, migrates silently |
| `questions-academic.md` | data | Stage 2 question bank for Academic Helper |
| `questions-non-fiction.md` | data | Stage 2 question bank for hebrew-book-producer |

The auditor is **not a standalone agent**. Rule-coverage runs inline inside `voice-calibrator` (sessions 3 and 7) and `voice-distiller` (on `:voice recompress`).

## 9. Auditor: rule-coverage only (axis C)

For every rule in the profile, check whether the corpus contains evidence supporting it. Rules with no corpus evidence are flagged in `.voice/audit.md` with the offending rule and an explanation.

The original two-axis design (A = generation match) is **deferred**. Generation-match scoring on a single paragraph against a single past paragraph has too much topic-driven variance to be reliable signal; the calibration loop already does a human "does this sound like you?" check at sessions 3 and 7, which is the only generation-quality check we trust in v1.

**Threshold (starting point, calibrate against a real corpus before locking)**:
- Rule coverage ≥ 8/10 → pass
- 6.0–7.9 → warn; calibrator surfaces unsupported rules
- < 6 → block recompress; user must remove or evidence the unsupported rules

**"Needs more data" short-circuit (starting point, calibrate)**:
- Corpus < 3 articles, OR < 1500 total words, OR < 800 words per article on average → auditor writes "needs corpus" and skips scoring.

All numeric thresholds in this section are **starting points pending real-corpus calibration during build**, not specifications.

## 10. Slash-command surface

One verb, sub-actions inferred from natural language:

- `:voice init` — start the 7-session interview from current fingerprint
- `:voice continue` — resume next unfinished session
- `:voice recompress` — re-distill all transcripts + fingerprint into `AUTHOR_VOICE.md`
- `:voice audit` — run the rule-coverage check
- `:voice quick` — adaptive short path; see §11
- `:voice sync` — push current `AUTHOR_VOICE.md` to CandleKeep (and pull-and-merge first)
- `:voice status` — show which sessions are done, current rule-coverage score, last-synced stamp

Existing `:init` continues to handle Stage 1 silently; it does not call `:voice init` automatically.

## 11. Quick mode behavior

`:voice quick` produces a profile in roughly one-third the time of the full interview by:

- **Skipping sessions 4 (Personality) and 7 (Warning Signs)** — these have the highest overlap with categories the fingerprint already proves.
- **Capping each remaining session at 8 questions** instead of 12–18.
- **Running calibration only at the end** (no mid-point).
- **Total**: 5 sessions × 8 questions + 1 calibration = ~43 user prompts (vs ~140 for full).

Quick mode emits a `[quick]` marker in the calibration block of `AUTHOR_VOICE.md` and in `.voice/audit.md` so subsequent recompresses know the profile is partial. `:voice continue --upgrade` runs the missing sessions to upgrade a quick profile to full.

## 12. CandleKeep sync semantics

- One book per writer, shared across both plugins: `Voice Profile — <writer name>`.
- **ID resolution**: try `.voice/.candlekeep-id` first; on miss/404, fall back to title lookup; on title hit repopulate the ID file; on miss create new and save.
- **v1 conflict policy**: **last-write-wins with a stamp**. Every sync writes a `> Updated YYYY-MM-DD by <plugin>` line at the top of `AUTHOR_VOICE.md`. On pull, if the remote stamp is newer than local's, local is overwritten. If the user is concerned about clobbering, they can `:voice sync` before editing or use git history to recover. (Three-way merge with common-ancestor file is **deferred** — solving a problem that is unlikely to fire for a single researcher running both plugins serially.)
- On every write/edit run start, plugin pulls latest before loading profile into prompt. One `ck` call per writing session, not per section.
- `ck` CLI missing or unauthed → `voice-sync` becomes a no-op with a single warning.

**Honest dependency note**: CandleKeep is *effectively required* for the cross-plugin shared-voice value. Without `ck`, the two plugins each maintain their own local `AUTHOR_VOICE.md` and will drift. The plugins still work standalone; the shared headline benefit does not.

## 13. Loading model — what each agent reads

- **Section writers** (per-paragraph, per-section): `AUTHOR_VOICE.md` only. Whole file fits in every subagent prompt; no division of the profile into separate files.
- **`voice-interviewer`**: `.voice/fingerprint.md` (to seed questions) and any prior `AUTHOR_VOICE.md` sections.
- **`voice-distiller`**: transcripts under `.voice/interview/` + previous `AUTHOR_VOICE.md`.
- **`voice-calibrator`**: `AUTHOR_VOICE.md` + corpus + the just-finished session transcript; runs inline rule-coverage check.
- **CandleKeep stores only `AUTHOR_VOICE.md`.** The other `.voice/*` files are local rebuild artifacts, not shared state.

## 14. Migration of existing voice data

Silent auto-migration on first session start after this ships:

- **Academic Helper**: voice/style sections of `.academic-writer/profile.json` are extracted into root `AUTHOR_VOICE.md` and `.voice/fingerprint.md`. The voice fields in `profile.json` are **stripped and replaced with a pointer comment** so no stale state remains:
  ```json
  "voice": "see ./AUTHOR_VOICE.md (migrated 2026-05-05)"
  ```
  Pre-migration copy of the full `profile.json` is archived to `.voice/legacy/profile.json`.
- **hebrew-book-producer**: existing `AUTHOR_VOICE.md` is **kept in place** (already at root) but parsed and reformatted into the new section structure. Pre-migration copy is archived to `.voice/legacy/AUTHOR_VOICE.md`.
- Migration hook is idempotent: detects `.voice/.migrated` marker and exits.
- Migration push to CandleKeep: each plugin's first migration uploads its own seed. The two plugins migrate complementary content (academic-side fields vs non-fiction-book-side fields); the second migration's `voice-distiller` merges them into the unified section structure.

## 15. UX summary

**First-time install (no prior data)** — user runs `:init`, drops corpus into expected folder. Stage 1 runs silently. User sees one line: "✓ Voice fingerprint created. Run `:voice` for a deeper profile (recommended)." Done.

**Stage 2 opt-in** — user runs `:voice`. Plugin explains: "7 sessions, ~15 questions each, calibration check at sessions 3 and 7. Or `:voice quick` for ~43 questions total. Resume anytime." Each question is one message; user answers freely in Hebrew or English. After session 3 and session 7, calibration loop runs (sample paragraph + 3 questions). User can stop anytime; `:voice continue` resumes.

**Subsequent sessions** — silent pull-and-load `AUTHOR_VOICE.md` at the start of any write/edit run; section writers read it locally; writing/editing just works.

**Voice maintenance** — `:voice recompress` after months of new writing. Inline rule-coverage flags drift; targeted re-interview tops up.

**Things the user never does** — edit JSON, manage transcripts, move legacy files, sync CandleKeep manually, choose between plugins.

## 16. Error handling

| Failure | Behavior |
|---|---|
| Empty/unreadable corpus in Stage 1 | Stub `fingerprint.md` with `needs corpus` flag; warn once; writing not blocked. Stage 2 interviewer asks broader questions. |
| Malformed legacy file in migration | Migrate parseable parts; leave rest in `.voice/legacy/` untouched; write `migration-notes.md`; warn once. |
| `ck` CLI missing/unauthed | `voice-sync` no-op with one-time warning. Each plugin's local `AUTHOR_VOICE.md` remains standalone (drift acknowledged). |
| Remote `AUTHOR_VOICE.md` newer than local | Last-write-wins: remote overwrites local. Local copy still in git, recoverable via `git restore` or CandleKeep history. |
| Interviewer crashes mid-session | Transcript appended per question; `:voice continue` resumes at last completed question. |
| Rule-coverage score below threshold | Calibrator/distiller surfaces unsupported rules; user removes or supplies evidence. Not an error. |
| User abandons after N sessions | Profile marked `[partial]` in `AUTHOR_VOICE.md`; plugins weight it lower in prompt. |
| Hebrew/English text direction | All artifacts are pure UTF-8 markdown; rendered output uses `direction: auto`. |

## 17. Testing

| Layer | Test |
|---|---|
| Structural | `tests/test_voice_structure.py` asserts root `AUTHOR_VOICE.md`, `.voice/` layout, agent files exist, question banks parse, slash command registers. |
| Migration | Fixtures with old `profile.json` / `AUTHOR_VOICE.md` → run migrate hook → assert new layout, voice fields stripped from `profile.json` and replaced with pointer, legacy archive intact, idempotent on re-run. |
| Miner | Hebrew fixture corpus → assert `fingerprint.md` non-empty, expected sections present, no JSON. |
| Interviewer | Mocked LLM transcript → assert session file written, resume picks up at right question, calibrator runs only after sessions 3 and 7. |
| Distiller | Snapshot test: fixed transcripts + fixed prior profile → stable output across runs at low temperature. |
| Rule coverage | Known-good vs known-bad profile against corpus → known-good scores higher; unsupported rules flagged correctly. |
| CandleKeep sync | Mock `ck` CLI → assert pull-and-push order, last-write-wins on stamp comparison, no-op on missing CLI. |
| Quick mode | Run `:voice quick` on fixture; assert sessions 4 and 7 skipped, per-session cap at 8, single calibration at end, `[quick]` marker present. |
| End-to-end | Full Stage 1 + Stage 2 (3 sessions, hits the mid-point calibration) on fixture project; assert profile valid, audit has score, no orphaned transcripts. |

## 18. Resolved implementation parameters (v1)

**Question bank distribution (per session)**: adaptive 12–18 questions, soft floor 12 / hard cap 18. Seed distribution category-weighted across three layers (voice / terminology / plugin-specific): Beliefs and Aesthetics lean voice-heavy; Structure, Refusals, Warning Signs lean plugin-specific-heavy; Terminology gets a small dedicated subsection (~3 questions) in every session. Sample questions per category in §5.

**Audit thresholds (rule coverage only, starting points)**: pass ≥ 8/10; warn 6.0–7.9; block < 6. "Needs more data" if corpus < 3 articles OR < 1500 total words OR < 800 words per article on average. **All numbers calibrate against fixture corpus during build, not in spec.**

**CandleKeep book ID resolution**: ID file with title fallback. `.voice/.candlekeep-id` is gitignored per-machine cache. On 404 or missing file, fall back to title lookup; on title hit, repopulate; on miss, create new and save.

**CandleKeep refresh cadence**: pull once at the start of any write/edit run (single `ck` call per writing session). Push only on `:voice` sub-actions that mutate `AUTHOR_VOICE.md`. Plugin session start does no automatic pull. `:voice status` does explicit pull-and-diff with no write.

**Calibration cadence**: sessions 3 and 7 only (mid-point + final). Other sessions update the profile via `voice-distiller` without calibration.

**Quick mode**: skips sessions 4 (Personality) and 7 (Warning Signs); caps remaining sessions at 8 questions; one calibration at the end; ~43 prompts total. `[quick]` marker in profile and audit. `:voice continue --upgrade` upgrades to full.

**File placement**: `AUTHOR_VOICE.md` at project root in both plugins (human-editable); `.voice/` for internal artifacts only.

## 19. Out of scope (deferred)

- Multi-writer / team voice profiles.
- Voice-profile diffing UI beyond raw git diff.
- Auto-detection of voice drift between recompressions.
- Profile portability to ChatGPT custom instructions / Gemini (stretch goal: `:voice export --target=chatgpt`).
- Three-way merge with common-ancestor file. Reintroduce only if last-write-wins clobbering becomes a real problem in practice.
- A-axis (generation match) auditor. Reintroduce only with a multi-sample statistical design and known-good baselines.
- Calibration after every session. Reintroduce only if mid-point + final proves too sparse in practice.
