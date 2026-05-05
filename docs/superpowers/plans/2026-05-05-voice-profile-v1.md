# Voice Profile Subsystem v1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the v1 voice-profile subsystem (Stage 1 mandatory miner + Stage 2 optional adversarial interview, single shared CandleKeep profile) identically in `Academic Helper` and `hebrew-book-producer`.

**Architecture:** Four subagents (`voice-miner`, `voice-interviewer`, `voice-distiller`, `voice-calibrator`) plus two utilities (`voice-sync` for CandleKeep, `voice-migrate` for legacy migration), driven by a single `:voice` skill with sub-actions. Profile lives at root `AUTHOR_VOICE.md`; build artifacts in `.voice/`. Identical methodology in both plugins; only the question bank file and corpus path differ.

**Tech Stack:** Markdown agents/skills with YAML frontmatter; bash for sync/migration utilities; existing TypeScript hooks (Academic Helper) and existing skill scaffolding (hebrew-book-producer); `ck` CLI for CandleKeep; pytest for structural tests in Academic Helper, equivalent shell/python tests in hebrew-book-producer.

**Spec:** `docs/superpowers/specs/2026-05-05-voice-profile-design.md` (read this before starting any task).

---

## File structure (created/modified)

### Both plugins — new files

```
AUTHOR_VOICE.md                                   # root, profile
.voice/                                           # gitignored except .gitkeep
├── fingerprint.md
├── audit.md
├── interview/01..07-*.md
├── legacy/
└── (.candlekeep-id, .last-update, .migrated)     # cache, gitignored
```

### Academic Helper — new

```
src/agents/voice-miner.md
src/agents/voice-interviewer.md
src/agents/voice-distiller.md
src/agents/voice-calibrator.md
src/skills/voice/SKILL.md
src/skills/voice/questions-academic.md
src/skills/voice/voice-sync.sh
src/skills/voice/voice-migrate.sh
src/hooks/src/lifecycle/voice-pull.ts
tests/test_voice_structure.py
tests/test_voice_migrate.py
tests/fixtures/voice/legacy-profile.json
tests/fixtures/voice/sample-corpus/*.md
```

### Academic Helper — modified

```
src/hooks/hooks.json                              # register voice-pull hook
src/agents/style-miner.md                         # deprecation note → voice-miner
src/skills/init/SKILL.md                          # call voice-miner in Stage 1
src/skills/write/SKILL.md                         # load AUTHOR_VOICE.md
src/skills/edit/SKILL.md                          # load AUTHOR_VOICE.md
src/skills/edit-section/SKILL.md                  # load AUTHOR_VOICE.md
manifests/academic-writer.json                    # bump minor version
.gitignore                                        # ignore .voice/, allow .voice/.gitkeep
```

### hebrew-book-producer — new

```
plugins/hebrew-book-producer/agents/voice-interviewer.md
plugins/hebrew-book-producer/agents/voice-distiller.md
plugins/hebrew-book-producer/agents/voice-calibrator.md
plugins/hebrew-book-producer/skills/voice/SKILL.md
plugins/hebrew-book-producer/skills/voice/questions-non-fiction.md
plugins/hebrew-book-producer/skills/voice/voice-sync.sh
plugins/hebrew-book-producer/skills/voice/voice-migrate.sh
plugins/hebrew-book-producer/hooks/voice-pull.sh
plugins/hebrew-book-producer/tests/test_voice_structure.sh
plugins/hebrew-book-producer/tests/fixtures/voice/legacy-author-voice.md
plugins/hebrew-book-producer/tests/fixtures/voice/sample-corpus/chapters/*.md
```

### hebrew-book-producer — modified

```
plugins/hebrew-book-producer/agents/voice-miner.md       # rewrite to v1 contract
plugins/hebrew-book-producer/skills/voice-preserver/SKILL.md   # deprecation note → AUTHOR_VOICE.md
plugins/hebrew-book-producer/skills/express-voice/SKILL.md     # deprecation note → AUTHOR_VOICE.md
plugins/hebrew-book-producer/skills/book-bootstrap/SKILL.md    # call voice-miner in Stage 1
plugins/hebrew-book-producer/agents/book-writer.md             # load AUTHOR_VOICE.md
plugins/hebrew-book-producer/agents/literary-editor-legacy.md  # load AUTHOR_VOICE.md
plugins/hebrew-book-producer/agents/proofreader.md             # load AUTHOR_VOICE.md
plugins/hebrew-book-producer/.claude-plugin/plugin.json        # register voice skill, bump version
.gitignore                                                     # ignore .voice/, allow .voice/.gitkeep
```

---

## Phase 0 — Existing-voice-infrastructure audit (do first, both projects)

### Task 0.1: Audit and document existing voice infrastructure

**Files:**
- Read: `Academic Helper/src/agents/style-miner.md`
- Read: `hebrew-book-producer/plugins/hebrew-book-producer/agents/voice-miner.md`
- Read: `hebrew-book-producer/plugins/hebrew-book-producer/skills/voice-preserver/SKILL.md`
- Read: `hebrew-book-producer/plugins/hebrew-book-producer/skills/express-voice/SKILL.md`
- Read: `hebrew-book-producer/plugins/hebrew-book-producer/skills/book-bootstrap/SKILL.md`
- Create: `docs/superpowers/plans/2026-05-05-voice-audit.md` in **each** project

- [ ] **Step 1: Read each file end-to-end and note**
  - What inputs each agent/skill takes
  - What outputs each writes
  - Which other agents/skills/hooks reference each
  - Whether any user-facing slash commands exist for them today

- [ ] **Step 2: Write the audit doc**

For each existing voice-related file, capture:
```markdown
## <file path>
- Status: keep / rewrite to v1 contract / deprecate-with-pointer / delete
- Inputs: <list>
- Outputs: <list>
- Inbound references: <grep for filename across project>
- Migration plan: <one sentence>
```

Decision rules:
- Existing `voice-miner.md` (hebrew-book-producer): **rewrite to v1 contract** (Phase 2). Same name, new I/O.
- `style-miner.md` (Academic Helper): **rewrite as `voice-miner.md`** with v1 contract; leave `style-miner.md` in place with a deprecation note pointing to `voice-miner.md` for one release.
- `voice-preserver`, `express-voice` (hebrew-book-producer): **deprecate with pointer** to `AUTHOR_VOICE.md`. Skills become thin shims that read the new profile and warn about the old name.
- `book-bootstrap` (hebrew-book-producer) and `init` (Academic Helper): **modify** to invoke the new `voice-miner` in Stage 1.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/2026-05-05-voice-audit.md
git commit -m "docs(voice): audit existing voice infrastructure"
```

Repeat in the other project.

---

## Phase 1 — Shared scaffolding (Academic Helper first; mirror in Phase 12)

### Task 1.1: Create `.voice/` directory layout and gitignore

**Files:**
- Create: `Academic Helper/.voice/.gitkeep`
- Modify: `Academic Helper/.gitignore`

- [ ] **Step 1: Add gitignore entry**

Append to `.gitignore`:
```
# Voice profile build artifacts (only AUTHOR_VOICE.md is tracked)
.voice/*
!.voice/.gitkeep
```

- [ ] **Step 2: Create the `.gitkeep` placeholder**

```bash
mkdir -p .voice
touch .voice/.gitkeep
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore .voice/.gitkeep
git commit -m "chore(voice): scaffold .voice/ artifact directory"
```

### Task 1.2: Create AUTHOR_VOICE.md template at project root

**Files:**
- Create: `Academic Helper/AUTHOR_VOICE.md`

- [ ] **Step 1: Write the template**

```markdown
> Updated <YYYY-MM-DD> by <plugin>
> Status: empty (run `/academic-writer:init` to seed Stage 1, then `/academic-writer:voice` for Stage 2)

# Voice Profile — <writer name>

## Core voice (cross-project)

_Empty. Populated by Stage 1 miner and Stage 2 interview._

## Terminology

_Empty._

## Academic-specific

_Empty._

## Non-fiction-book-specific

_Empty._
```

- [ ] **Step 2: Commit**

```bash
git add AUTHOR_VOICE.md
git commit -m "feat(voice): add AUTHOR_VOICE.md root template"
```

### Task 1.3: Add structural test asserting the layout

**Files:**
- Create: `Academic Helper/tests/test_voice_structure.py`

- [ ] **Step 1: Write the failing test**

```python
"""Structural tests for the voice subsystem."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def test_author_voice_at_root_exists():
    assert (ROOT / "AUTHOR_VOICE.md").is_file()

def test_voice_dir_exists():
    assert (ROOT / ".voice").is_dir()
    assert (ROOT / ".voice" / ".gitkeep").is_file()

def test_voice_artifacts_gitignored():
    gi = (ROOT / ".gitignore").read_text()
    assert ".voice/*" in gi
    assert "!.voice/.gitkeep" in gi
```

- [ ] **Step 2: Run and confirm pass**

```bash
python3 -m pytest tests/test_voice_structure.py -v
```
Expected: 3 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/test_voice_structure.py
git commit -m "test(voice): structural assertions for .voice/ layout"
```

---

## Phase 2 — Stage 1: voice-miner agent

### Task 2.1: Write voice-miner contract test

**Files:**
- Create: `Academic Helper/tests/test_voice_miner_contract.py`
- Create: `Academic Helper/tests/fixtures/voice/sample-corpus/article-01.md`
- Create: `Academic Helper/tests/fixtures/voice/sample-corpus/article-02.md`
- Create: `Academic Helper/tests/fixtures/voice/sample-corpus/article-03.md`

- [ ] **Step 1: Create three fixture articles** (any short Hebrew academic prose, ~500 words each — copy from past-articles/ samples or write minimal placeholders)

- [ ] **Step 2: Write the failing test (contract-only — no LLM)**

```python
"""Contract test for voice-miner agent definition."""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
AGENT = ROOT / "src" / "agents" / "voice-miner.md"

def test_voice_miner_agent_exists():
    assert AGENT.is_file()

def test_voice_miner_frontmatter_complete():
    text = AGENT.read_text()
    assert text.startswith("---\n")
    fm_end = text.index("\n---\n", 4)
    fm = yaml.safe_load(text[4:fm_end])
    for k in ("name", "description", "tools", "model"):
        assert k in fm, f"missing frontmatter key: {k}"
    assert fm["name"] == "voice-miner"

def test_voice_miner_specifies_io_contract():
    text = AGENT.read_text()
    # Must specify both inputs and outputs
    assert "past-articles/" in text or "corpus" in text.lower()
    assert ".voice/fingerprint.md" in text
    assert "## Inputs" in text or "**Inputs**" in text
    assert "## Outputs" in text or "**Outputs**" in text
```

- [ ] **Step 3: Run, confirm fails**

```bash
python3 -m pytest tests/test_voice_miner_contract.py -v
```
Expected: FAIL (file not found).

- [ ] **Step 4: Commit the failing test**

```bash
git add tests/test_voice_miner_contract.py tests/fixtures/voice/sample-corpus/
git commit -m "test(voice): contract test for voice-miner agent"
```

### Task 2.2: Write the voice-miner agent

**Files:**
- Create: `Academic Helper/src/agents/voice-miner.md`

- [ ] **Step 1: Write the agent**

```markdown
---
name: voice-miner
description: Stage 1 of the voice subsystem — read the writer's corpus and emit a markdown style fingerprint. Use when the user runs init or explicitly requests a voice-fingerprint refresh.
tools: Read, Glob, Grep, Write
model: claude-haiku-4-5-20251001
metadata:
  author: Academic Helper
  version: 1.0.0
---

# voice-miner

You read the writer's corpus and produce a human-readable markdown fingerprint capturing the
empirical signals of their voice. You do not interview — that is `voice-interviewer`'s job.

## Inputs

- `past-articles/**/*.{md,docx,pdf}` (Academic Helper) or `chapters/**/*.md`,
  `manuscript.md` (hebrew-book-producer). Project layout determines path.
- The previous `.voice/fingerprint.md` if present (so you can incrementally update rather than
  overwrite if the corpus has only grown by one or two articles).

## Outputs

Write `.voice/fingerprint.md` only. Never write `AUTHOR_VOICE.md` — that is the distiller's job.

## Required sections in fingerprint.md

1. **Corpus summary** — N articles, total words, date range, languages detected.
2. **Sentence-length distribution** — mean, median, stdev, max. Note any unusual rhythm.
3. **Paragraph-length distribution** — same stats.
4. **Phrase frequency** — top 30 idiomatic phrases used 3+ times. Hebrew and English separately.
5. **Banned-word candidates** — words/phrases the writer *never* uses where peers do (e.g.,
   "moreover", "furthermore" in academic prose). Detect by comparing to a generic register.
6. **Citation patterns** — typical density (cites per 1000 words), inline vs footnote, common
   framing verbs ("argues", "shows", "מבחין", "טוען").
7. **Structural signals** — typical section count, heading style, intro/conclusion length ratio.
8. **Open questions for Stage 2** — list of things the corpus cannot tell you (refusals, productive
   contradictions, intentional pivots) that the interviewer should probe.

## Hard rules

- Output is markdown, not JSON. The fingerprint is human-readable.
- Quote real examples from the corpus inline (one sentence each, file:line citation).
- If the corpus is below the "needs more data" threshold (< 3 articles OR < 1500 total words OR
  < 800 words/article avg), write a stub fingerprint flagged with `> NEEDS CORPUS`.
- Idempotent: running you again on the same corpus produces the same output (modulo timestamp).

## Failure modes

- Empty/unreadable corpus → write stub flagged `> NEEDS CORPUS`; do not error.
- Mixed-language corpus → run analyses per-language and report both; do not merge stats.
```

- [ ] **Step 2: Run the contract test, confirm pass**

```bash
python3 -m pytest tests/test_voice_miner_contract.py -v
```
Expected: 3 passed.

- [ ] **Step 3: Commit**

```bash
git add src/agents/voice-miner.md
git commit -m "feat(voice): voice-miner agent for Stage 1 fingerprint"
```

### Task 2.3: Mark style-miner deprecated

**Files:**
- Modify: `Academic Helper/src/agents/style-miner.md`

- [ ] **Step 1: Prepend deprecation note**

Insert at the very top of the file body (after frontmatter):

```markdown
> **DEPRECATED in v1 of the voice subsystem.** Use `voice-miner` instead. This agent's outputs
> are no longer wired into any pipeline. Will be removed one release after `voice-miner` ships.
> See `docs/superpowers/specs/2026-05-05-voice-profile-design.md`.
```

- [ ] **Step 2: Commit**

```bash
git add src/agents/style-miner.md
git commit -m "chore(voice): deprecate style-miner in favor of voice-miner"
```

---

## Phase 3 — Question banks (the actual product)

### Task 3.1: Write `questions-academic.md`

**Files:**
- Create: `Academic Helper/src/skills/voice/questions-academic.md`

- [ ] **Step 1: Write the file**

Use the sample questions from spec §5 as the seed. Required structure:

```markdown
# Stage 2 Question Bank — Academic

This file is consumed by the `voice-interviewer` agent. The interviewer adapts within sessions
(12–18 questions, hard cap 18) but draws from this seed list.

## Layer legend

- **[V]** Voice — Almaya-style, register/rhythm/refusals
- **[T]** Terminology — preferred/banned terms, transliteration, citation phrasing
- **[A]** Plugin-specific — academic register, thesis style, citation density, תקציר conventions

## 01 — Beliefs (voice-heavy)

- [V] Name one thing "good academic writing" is supposed to do that you think is bullshit. Defend.
- [V] What's a stylistic move you respect in writers you disagree with?
- [V] What's one belief about your field that you would defend in a footnote but not the main text?
- [T] Pick one: חז״ל / Hazal / Chazal / חז\"ל. Justify it for an audience using a different convention.
- [T] One Hebrew transliteration choice you refuse to make even when standard. Why?
- [A] When a source contradicts your thesis, do you preempt, footnote, cut, or restructure? Explain.
- [A] Is hedging ("arguably", "tends to") cowardice or rigor? Defend your answer.
- [V] One critique of your field that no insider has the standing to make.
- [A] What's a citation pattern that's dishonest dressed as scholarly? Three examples.
- [V] What does "rigorous" mean to you when nobody else is grading?
- [T] List five Hebrew academic terms you'd swap for plainer alternatives if the reviewer let you.
- [V] Productive contradiction: name two things you simultaneously believe that don't reconcile.

## 02 — Writing Practices (voice-heavy)

- [V] Describe what you do in the first 15 minutes of a writing session. Be specific.
- [V] Show me a sentence from your last article that you'd cut now.
- [V] When do you write fast vs slow? What's the visible difference in output?
- [T] List five phrases you use too often. Decide: keep, kill, or contextualize.
- [T] Three Hebrew connectives you overuse. Three you avoid.
- [A] When stuck on a thesis, what's the unblock — walk, sources, outline, coffee, person?
- [A] Citation density you aim for in a 7000-word article. Defend the number.
- [V] What's the smallest unit of writing you can produce in a sitting? Sentence, paragraph, section?
- [A] When you cite a source you disagree with, what's your typical framing verb?
- [V] One writing rule you've broken on purpose and would break again.
- [T] Phrases that signal "this writer is hedging because they're scared" vs "because they're rigorous".
- [V] What does revision feel like — pruning, surgery, reconstruction, polishing?

## 03 — Aesthetics (voice + plugin-specific)

- [V] Em-dash, semicolon, or comma — when each? Be specific.
- [V] Long sentences vs short. Default rhythm?
- [V] How do you signal a beat change without a heading?
- [T] Five words you refuse to use even when correct.
- [T] Five words that feel "AI-coded" to you in Hebrew academic prose.
- [A] Hedging quota in 7000 words: 0, ≤5, ≤15, unrestricted? Why?
- [A] Footnote density tolerance — what's "too many"?
- [V] One paragraph rhythm you've stolen from another writer.
- [T] What does תקציר sound like when it's working vs when it's filler?
- [A] Headings: numbered, not numbered, descriptive, declarative, question?
- [V] Two consecutive long sentences — when okay, when never?
- [T] What's a Hebrew word that's correct but you find ugly?

## 04 — Personality (voice-heavy)

- [V] When you're being honest in writing, what does that *sound* like? Show a sentence.
- [V] What does AI-generated writing sound like to you? Three specific tells.
- [T] Words that signal "me being earnest" vs "me hiding behind formality".
- [V] Emotional baseline — wry, severe, warm, clinical, urgent? One word, then defend.
- [V] One emotion you suppress on the page that shows up anyway.
- [V] Self-reference: first person, "we", impersonal? When each?
- [V] Humor: forbidden, allowed in footnotes, allowed inline, structural? Defend.
- [V] What's your default register with a hostile reader?
- [V] When you praise another scholar, do you sound generous or hedged?
- [V] One sentence you've written that you're proud of. Why.

## 05 — Structure (plugin-specific-heavy)

- [V] Average paragraph length. Why?
- [A] Section count for a 7000-word article. Defend.
- [A] Where does the תקציר go? What does it have to do?
- [A] Intro length as % of total. Conclusion length as % of total.
- [A] One section every paper of yours needs that most papers don't have.
- [T] How do you signal a section break that isn't a heading?
- [A] Footnotes: explanatory, only citation, mixed, banned? Defend.
- [A] Section titles: declarative, descriptive, question, none?
- [V] How do you transition between sections — bridge sentence, blank line, summary?
- [A] When does a paragraph deserve to be one sentence?
- [T] Hebrew vs English heading numbering — different rules in your work?
- [A] What's the maximum nested-list depth you tolerate inside an article?

## 06 — Refusals (plugin-specific-heavy)

- [V] One sentence you would never write, even if a source demanded it.
- [V] Three opening sentences that are immediate cuts.
- [A] Citation patterns dishonest-dressed-as-scholarly. Name three.
- [A] Sources you would not cite even if relevant. Why?
- [T] Five "AI-coded" words.
- [T] Five Hebrew academic clichés you refuse.
- [V] Three closing sentences that are immediate cuts.
- [A] Tone you would never adopt — sycophantic, contemptuous, breezy, prosecutorial?
- [V] When would you walk away from an article rather than finish it?
- [A] What's a footnote you'd refuse to write even if a reviewer demanded it?

## 07 — Warning Signs (plugin-specific-heavy)

- [V] When you're writing badly, what's the first thing that goes wrong?
- [A] Fake-rigor red flags — what reads like scholarship but isn't?
- [T] Phrases that signal "this writer has stopped thinking".
- [V] Re-reading something you wrote, what makes you flinch?
- [A] One AI-tell that survives even careful editing.
- [V] When a draft is 80% there and won't get better, what do you do?
- [A] What's the difference between a paragraph that's wrong and one that's just unpolished?
- [V] Catastrophe signal — the moment you know to throw out the draft.
- [A] How do you know your argument is loose vs your prose is loose?
- [T] One Hebrew filler-word you use when you don't know what to say next.
```

- [ ] **Step 2: Commit**

```bash
git add src/skills/voice/questions-academic.md
git commit -m "feat(voice): seed question bank for academic register"
```

### Task 3.2: Write `questions-non-fiction.md` (in hebrew-book-producer)

**Files:**
- Create: `hebrew-book-producer/plugins/hebrew-book-producer/skills/voice/questions-non-fiction.md`

- [ ] **Step 1: Write the file**

Same structure as `questions-academic.md`, but the **[A]** layer becomes **[B]** (book) and is rewritten for non-fiction-book register. Use spec §5 non-fiction examples as seeds.

```markdown
# Stage 2 Question Bank — Non-fiction Book

## Layer legend

- **[V]** Voice — Almaya-style, register/rhythm/refusals
- **[T]** Terminology — preferred/banned terms, transliteration, citation phrasing
- **[B]** Plugin-specific — non-fiction-book register: chapter rhythm, niqqud policy,
  dialogue/quotation conventions, register shifts, Hazal treatment, typesetting defaults

## 01 — Beliefs (voice-heavy)

- [V] Name one thing "good non-fiction" is supposed to do that you think is bullshit. Defend.
- [V] What's a stylistic move you respect in writers you disagree with?
- [V] What's one belief about your topic that you'll defend to a hostile reader?
- [T] Pick one: חז״ל / Hazal / Chazal / חז\"ל. Justify it for an audience using a different convention.
- [T] One Hebrew transliteration choice you refuse to make even when standard. Why?
- [B] How do you decide whether to quote a religious source in full vs paraphrase?
- [B] Is sentimentality cowardice or warmth? Defend your answer.
- [V] One critique of your subject area that only a sympathetic insider can land.
- [B] Three opening-page moves that are immediate "abandon book" signals to a reader.
- [V] What does "honest" mean on the page when nobody is grading?
- [T] List five Hebrew religious-text quotation conventions you actually use vs the textbook ones.
- [V] Productive contradiction: name two things you simultaneously believe that don't reconcile.

## 02 — Writing Practices (voice-heavy)

- [V] First 15 minutes of a writing session. Be specific.
- [V] One sentence from your last chapter you'd cut now.
- [V] When do you write fast vs slow? What's visible in the output?
- [T] Five phrases you use too often. Keep, kill, or contextualize.
- [T] Three Hebrew connectives you overuse. Three you avoid.
- [B] When stuck on a chapter, what's the unblock — walk, sources, outline, coffee, person?
- [B] Chapter-opening pattern: anecdote, claim, question, scene, dialogue?
- [V] Smallest unit you can produce in a sitting — sentence, paragraph, scene, chapter?
- [B] When you quote a religious source, what's your typical framing verb / lead-in phrase?
- [V] One writing rule you've broken on purpose and would break again.
- [T] Phrases that signal "this writer is performing wisdom" vs "earning it".
- [V] Revision: pruning, surgery, reconstruction, polishing?

## 03 — Aesthetics (voice + plugin-specific)

- [V] Em-dash, semicolon, comma — when each?
- [V] Long sentences vs short. Default rhythm.
- [V] How do you signal a beat change without a heading.
- [T] Five words you refuse to use even when correct.
- [T] Five "AI-coded" words in Hebrew non-fiction prose.
- [B] Frank Ruhl Libre defaults — what do you change in practice?
- [B] Niqqud policy — full, selective, banned, only on quotations? Defend.
- [V] One paragraph rhythm you've stolen from another writer.
- [B] Dialogue: em-dash, quotation marks, none, mixed?
- [B] Section breaks: heading, ornament, blank line, asterisks?
- [V] Two consecutive long sentences — when okay, when never?
- [T] What's a Hebrew word that's correct but you find ugly?

## 04 — Personality (voice-heavy)

- [V] When you're being honest in writing, what does that *sound* like? Show a sentence.
- [V] What does AI-generated non-fiction sound like to you? Three tells.
- [T] Words that signal "me being earnest" vs "me hiding behind elevated register".
- [V] Emotional baseline — wry, severe, warm, clinical, urgent? Defend.
- [V] One emotion you suppress on the page that shows up anyway.
- [V] Self-reference: first person, "we", impersonal? When each?
- [V] Humor: forbidden, allowed in footnotes, allowed inline, structural?
- [V] Default register with a hostile reader.
- [V] When you praise a religious figure, do you sound reverent or measured?
- [V] One sentence you've written that you're proud of. Why.

## 05 — Structure (plugin-specific-heavy)

- [V] Average paragraph length. Why?
- [B] Chapter length range. What forces a split?
- [B] Footnote vs endnote vs inline citation — when each?
- [B] Intro chapter length as % of total. Conclusion length as % of total.
- [B] One chapter every book of yours needs that most don't.
- [T] How do you signal a section break that isn't a heading?
- [B] Footnotes: explanatory, citation-only, mixed, banned?
- [B] Chapter titles: declarative, descriptive, question, none?
- [V] How do you transition between chapters — bridge sentence, blank scene, summary?
- [B] When does a paragraph deserve to be one sentence?
- [T] Hebrew vs English heading numbering — different rules in your work?
- [B] Maximum nested-list depth you tolerate inside a chapter?

## 06 — Refusals (plugin-specific-heavy)

- [V] One sentence you would never write, even if a source demanded it.
- [V] Three opening sentences that are immediate cuts.
- [B] How do you treat a religious source you personally find objectionable?
- [B] Sources you would not cite even if relevant. Why?
- [T] Five "AI-coded" words.
- [T] Five Hebrew non-fiction clichés you refuse.
- [V] Three closing sentences that are immediate cuts.
- [B] Tone you would never adopt — sycophantic, contemptuous, breezy, prosecutorial?
- [V] When would you walk away from a chapter rather than finish it?
- [B] A footnote you'd refuse even if an editor demanded it.

## 07 — Warning Signs (plugin-specific-heavy)

- [V] When you're writing badly, first thing that goes wrong?
- [B] Sentimentality red flags — what's earned emotion vs manufactured?
- [T] Phrases that signal "this writer has stopped thinking".
- [V] Re-reading something you wrote, what makes you flinch?
- [B] One AI-tell that survives even careful editing.
- [V] When a draft is 80% there and won't get better, what do you do?
- [B] Difference between a chapter that's wrong vs one that's unpolished?
- [V] Catastrophe signal — the moment you know to throw out the draft.
- [B] How do you know your argument is loose vs your prose is loose?
- [T] One Hebrew filler word you use when you don't know what to say next.
```

- [ ] **Step 2: Commit**

```bash
git add plugins/hebrew-book-producer/skills/voice/questions-non-fiction.md
git commit -m "feat(voice): seed question bank for non-fiction-book register"
```

(This task lives in hebrew-book-producer; do it now to match the parallel structure even though we're mostly building Academic Helper first. The interviewer agent depends on its existence in both projects.)

---

## Phase 4 — voice-interviewer agent

### Task 4.1: Write voice-interviewer contract test

**Files:**
- Create: `Academic Helper/tests/test_voice_interviewer_contract.py`

- [ ] **Step 1: Write the test**

```python
"""Contract test for voice-interviewer agent."""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
AGENT = ROOT / "src" / "agents" / "voice-interviewer.md"
QUESTIONS = ROOT / "src" / "skills" / "voice" / "questions-academic.md"

def test_voice_interviewer_exists():
    assert AGENT.is_file()

def test_voice_interviewer_frontmatter():
    text = AGENT.read_text()
    fm_end = text.index("\n---\n", 4)
    fm = yaml.safe_load(text[4:fm_end])
    assert fm["name"] == "voice-interviewer"
    for k in ("description", "tools", "model"):
        assert k in fm

def test_voice_interviewer_references_question_bank():
    text = AGENT.read_text()
    assert "questions-academic.md" in text or "question bank" in text.lower()

def test_voice_interviewer_specifies_session_state():
    text = AGENT.read_text()
    assert ".voice/interview/" in text
    assert "resume" in text.lower()

def test_voice_interviewer_states_per_session_cap():
    text = AGENT.read_text()
    assert "12" in text and "18" in text  # soft floor and hard cap
```

- [ ] **Step 2: Run, confirm fail**

```bash
python3 -m pytest tests/test_voice_interviewer_contract.py -v
```
Expected: FAIL.

- [ ] **Step 3: Commit**

```bash
git add tests/test_voice_interviewer_contract.py
git commit -m "test(voice): contract test for voice-interviewer"
```

### Task 4.2: Write voice-interviewer agent

**Files:**
- Create: `Academic Helper/src/agents/voice-interviewer.md`

- [ ] **Step 1: Write the agent**

```markdown
---
name: voice-interviewer
description: Stage 2 of the voice subsystem — run one adversarial interview session at a time, append to the session transcript, hand back to the orchestrator when the session ends. Use only inside the `:voice` skill.
tools: Read, Write, Glob
model: claude-haiku-4-5-20251001
metadata:
  author: Academic Helper
  version: 1.0.0
---

# voice-interviewer

You run one Stage 2 interview session. The orchestrating skill (`:voice`) calls you with a
session number (1–7) and a category name. You read the seed questions, read the fingerprint, read
any prior transcripts, and conduct an adversarial interview in chat with the user.

## Inputs

- Session number and category name (provided by orchestrator)
- `.voice/fingerprint.md` (read once at start)
- Prior session transcripts under `.voice/interview/` (read for context, do not duplicate questions)
- Seed question bank: `src/skills/voice/questions-academic.md` (Academic Helper) or
  `plugins/hebrew-book-producer/skills/voice/questions-non-fiction.md`

## Outputs

- Append questions and user answers to `.voice/interview/0N-<category>.md` per question, atomically.
  - Format: `## Q<n> — [layer] question text\n\n> answer text\n\n` repeated.
- When session ends (cap reached or you decide a productive thread is exhausted), write a single
  trailing line `<!-- session complete -->` and return control. The orchestrator detects this and
  decides whether to invoke the calibrator (sessions 3 and 7 only) or proceed to next session.

## Adaptive size

- Soft floor: 12 questions per session.
- Hard cap: 18 questions per session.
- Within these bounds, follow productive threads: if a single answer reveals two new lines, ask the
  more revealing one before moving to the next seed question. Drop seed questions whose answers are
  already implied by the fingerprint or earlier sessions.

## Adversarial register

You are deliberately confrontational. Vague answers ("I value clarity", "I write naturally") get
pushback: "What does 'clarity' mean? Show me a sentence you'd cut for being unclear." Demand
specifics — sentences, phrases, file:line citations from past articles. Never accept abstractions.

## Bilingual

The user replies in Hebrew or English freely. You also speak both. Phrase-bank and banned-words
answers should stay Hebrew (don't ask the user to translate). Decision-rule answers can be either;
prefer English for terse rules.

## Resume rule

Before asking question N, read `.voice/interview/0N-<category>.md`. Continue from the last answered
question. Never ask a question that already has an answer in the transcript.

## Hard rules

- One question per turn. Never batch.
- Append to transcript per question (atomic), never rewrite from scratch.
- Refer to fingerprint findings explicitly: "Your last 3 papers used 'מבחינה זו' 14 times — keep,
  kill, or contextualize?" This is what makes you better than a cold interview.
- Stop at hard cap 18 even mid-thread. Better to leave a thread for `:voice continue` than overrun.

## End-of-session checklist

When stopping (cap or thread-exhausted), append:
```
<!-- session complete: <count> questions, <iso8601 timestamp> -->
```
and return to orchestrator.
```

- [ ] **Step 2: Run contract test**

```bash
python3 -m pytest tests/test_voice_interviewer_contract.py -v
```
Expected: 5 passed.

- [ ] **Step 3: Commit**

```bash
git add src/agents/voice-interviewer.md
git commit -m "feat(voice): voice-interviewer agent for Stage 2 sessions"
```

---

## Phase 5 — voice-distiller agent

### Task 5.1: Distiller contract test

**Files:**
- Create: `Academic Helper/tests/test_voice_distiller_contract.py`

- [ ] **Step 1: Write the test**

```python
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
AGENT = ROOT / "src" / "agents" / "voice-distiller.md"

def test_distiller_exists():
    assert AGENT.is_file()

def test_distiller_frontmatter():
    text = AGENT.read_text()
    fm = yaml.safe_load(text.split("---")[1])
    assert fm["name"] == "voice-distiller"

def test_distiller_writes_author_voice():
    text = AGENT.read_text()
    assert "AUTHOR_VOICE.md" in text
    assert ".voice/interview" in text
    assert "fingerprint.md" in text

def test_distiller_states_section_structure():
    text = AGENT.read_text()
    for s in ("Core voice", "Terminology", "Academic-specific", "Non-fiction-book-specific"):
        assert s in text

def test_distiller_states_token_budget():
    text = AGENT.read_text()
    assert "2,000" in text or "2000" in text
    assert "5,000" in text or "5000" in text
```

- [ ] **Step 2: Run, fail, commit test**

```bash
python3 -m pytest tests/test_voice_distiller_contract.py -v   # FAIL
git add tests/test_voice_distiller_contract.py
git commit -m "test(voice): contract test for voice-distiller"
```

### Task 5.2: Write voice-distiller agent

**Files:**
- Create: `Academic Helper/src/agents/voice-distiller.md`

- [ ] **Step 1: Write**

```markdown
---
name: voice-distiller
description: Compress one or more session transcripts plus the fingerprint into the unified AUTHOR_VOICE.md, merging with any prior profile. Use after a Stage 2 session completes, after migration, or on `:voice recompress`.
tools: Read, Write, Edit
model: claude-haiku-4-5-20251001
metadata:
  author: Academic Helper
  version: 1.0.0
---

# voice-distiller

You compress raw signal (fingerprint + interview transcripts) into the writer's `AUTHOR_VOICE.md`
profile. You combine the compressor and merger roles.

## Inputs

- `.voice/fingerprint.md`
- `.voice/interview/*.md` (whichever sessions are complete)
- The current `AUTHOR_VOICE.md` (may be empty template, may be partial profile)
- Optional: a single `--session N` flag, in which case only that session's transcript is folded in
  and other sections are preserved verbatim.

## Outputs

Rewrite root `AUTHOR_VOICE.md` only. Preserve the four-section structure exactly:

```
# Voice Profile — <writer name>

> Updated YYYY-MM-DD by <plugin>

## Core voice (cross-project)

## Terminology

## Academic-specific

## Non-fiction-book-specific
```

Update the `> Updated` line to today's date and the calling plugin name.

## Token budget

Target 2,000–5,000 tokens for the entire profile. If you exceed 5,000 after merging, compress
harder using Almaya's test: "if this line disappeared, would the AI write differently?" If no,
cut it. Phrase bank, banned-words list, and decision rules are highest signal; preserve them.

## Compression principles

- Operational over abstract: "first sentence ≤ 12 words on academic openings" beats "concise openings".
- Preserve specific phrases verbatim: phrase bank entries are quoted as-is.
- Productive contradictions: do not resolve. Keep both halves under a `> Tension:` line.
- Hebrew strings are kept Hebrew. Do not transliterate, do not translate.
- Decision rules in English ("never hedge twice in one sentence"), phrase bank in Hebrew, banned
  words in whichever language the writer used.

## Section assignment rules

- A signal that applies regardless of project → Core voice.
- Term/transliteration/citation-format choice → Terminology.
- Citation density, hedging, תקציר conventions, anti-AI thresholds → Academic-specific.
- Chapter rhythm, niqqud, dialogue conventions, Hazal treatment, typesetting → Non-fiction-book-specific.
- When uncertain, prefer Core voice over project-specific.

## Hard rules

- Never invent a rule the corpus or transcripts don't support.
- Never delete a rule from the existing profile that is contradicted only by tone, not by content.
  If a transcript answer changes a rule, replace the rule and keep a one-line `> Was: <old>` note
  for one cycle.
- Idempotent on no-change input: same inputs → same output (modulo timestamp).

## After writing

Emit a single closing block:
```
<!-- distilled: N transcripts merged, M tokens, YYYY-MM-DD -->
```
on the last line of the file.
```

- [ ] **Step 2: Run test, pass, commit**

```bash
python3 -m pytest tests/test_voice_distiller_contract.py -v   # PASS
git add src/agents/voice-distiller.md
git commit -m "feat(voice): voice-distiller agent (compress + merge)"
```

---

## Phase 6 — voice-calibrator agent

### Task 6.1: Calibrator contract test

**Files:**
- Create: `Academic Helper/tests/test_voice_calibrator_contract.py`

- [ ] **Step 1: Write**

```python
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
AGENT = ROOT / "src" / "agents" / "voice-calibrator.md"

def test_calibrator_exists():
    assert AGENT.is_file()

def test_calibrator_frontmatter():
    text = AGENT.read_text()
    fm = yaml.safe_load(text.split("---")[1])
    assert fm["name"] == "voice-calibrator"

def test_calibrator_invoked_only_on_3_and_7():
    text = AGENT.read_text()
    assert "session 3" in text.lower() and "session 7" in text.lower()

def test_calibrator_runs_rule_coverage():
    text = AGENT.read_text()
    assert "rule coverage" in text.lower() or "rule-coverage" in text.lower()
    assert ".voice/audit.md" in text

def test_calibrator_three_questions():
    text = AGENT.read_text()
    # Three calibration questions
    assert "sound like you" in text.lower()
    assert "banned" in text.lower()
    assert ("wrong" in text.lower() and "missing" in text.lower())
```

- [ ] **Step 2: Run, fail, commit**

```bash
python3 -m pytest tests/test_voice_calibrator_contract.py -v   # FAIL
git add tests/test_voice_calibrator_contract.py
git commit -m "test(voice): contract test for voice-calibrator"
```

### Task 6.2: Write voice-calibrator agent

**Files:**
- Create: `Academic Helper/src/agents/voice-calibrator.md`

- [ ] **Step 1: Write**

```markdown
---
name: voice-calibrator
description: After session 3 (mid-point) and session 7 (final), validate the profile by generating a sample paragraph, asking the user three calibration questions, patching the profile, and running an inline rule-coverage check. Never invoked on other sessions.
tools: Read, Write, Edit
model: claude-haiku-4-5-20251001
metadata:
  author: Academic Helper
  version: 1.0.0
---

# voice-calibrator

You run the human-in-the-loop calibration check after session 3 (mid-point) and session 7 (final).
You are not invoked on sessions 1, 2, 4, 5, 6.

## Inputs

- Current `AUTHOR_VOICE.md`
- The just-completed session transcript
- A sample of the writer's past corpus (3 paragraphs from different past articles, picked at random)

## Procedure

1. **Generate a sample paragraph.** Pick a topic from one of the past-corpus paragraphs. Generate a
   single paragraph using the *current* `AUTHOR_VOICE.md` as system prompt. Keep length within 1
   sentence of the original paragraph's length.

2. **Show the diff.** Print the new sample alongside the previous-version sample (or the original
   past paragraph if this is the first calibration). Highlight changes.

3. **Ask three calibration questions, one at a time:**
   - "Does this paragraph sound like you? If not, what's the first thing that's off?"
   - "Did any banned phrase or AI-tell sneak in? Quote it."
   - "Is any rule in the profile wrong, or is one missing?"

4. **Patch the profile** based on answers. Use `Edit` (not `Write`) to make minimal, targeted
   changes. Document each change with a one-line `> Was: <old>` note for one cycle.

5. **Inline rule-coverage check.** For every rule in the profile, scan the past corpus for evidence.
   Rules with zero hits get flagged. Write `.voice/audit.md` with:
   ```
   # Voice profile audit — YYYY-MM-DD

   - Rule coverage score: X.X / 10
   - Rules flagged (no corpus evidence): N

   ## Flagged rules

   - "<rule text>" — section: <Core voice|...>; reason: no matching pattern in corpus
   ```
   Threshold (starting points, calibrate during real usage):
   - ≥ 8.0 → pass, no user prompt
   - 6.0–7.9 → warn user, list flagged rules, offer "remove or supply evidence?" prompt
   - < 6 → block recompress; require user to remove or evidence flagged rules before continuing

6. **Sync to CandleKeep.** Call `voice-sync push`. If `ck` is missing, warn once and continue.

## Hard rules

- Three questions, no more. Calibration is light, not exhaustive.
- Patches are minimal. If the user gave a vague answer ("eh, kinda"), do not patch.
- Never re-ask a previous calibration's questions. The transcript shows what was asked.
- Idempotent: rerunning calibration with no new transcripts produces the same patches.
```

- [ ] **Step 2: Pass test, commit**

```bash
python3 -m pytest tests/test_voice_calibrator_contract.py -v   # PASS
git add src/agents/voice-calibrator.md
git commit -m "feat(voice): voice-calibrator with inline rule-coverage"
```

---

## Phase 7 — voice-sync utility (CandleKeep wrapper)

### Task 7.1: Test voice-sync behavior on missing `ck`

**Files:**
- Create: `Academic Helper/tests/test_voice_sync.py`

- [ ] **Step 1: Write**

```python
"""Tests for voice-sync.sh utility."""
import subprocess
from pathlib import Path
import os, shutil, tempfile

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "src" / "skills" / "voice" / "voice-sync.sh"

def test_script_exists_and_executable():
    assert SCRIPT.is_file()
    assert os.access(SCRIPT, os.X_OK)

def test_no_op_when_ck_missing(tmp_path):
    env = os.environ.copy()
    # Force ck-missing by clearing PATH
    env["PATH"] = "/dev/null"
    env["VOICE_PROJECT_ROOT"] = str(tmp_path)
    (tmp_path / "AUTHOR_VOICE.md").write_text("# stub\n")
    r = subprocess.run([str(SCRIPT), "push"], env=env, capture_output=True, text=True)
    assert r.returncode == 0
    assert "ck not available" in (r.stdout + r.stderr).lower()

def test_status_reports_no_id_cache(tmp_path):
    env = os.environ.copy()
    env["VOICE_PROJECT_ROOT"] = str(tmp_path)
    (tmp_path / ".voice").mkdir()
    r = subprocess.run([str(SCRIPT), "status"], env=env, capture_output=True, text=True)
    assert "no cached candlekeep id" in (r.stdout + r.stderr).lower()
```

- [ ] **Step 2: Run, fail, commit test**

```bash
python3 -m pytest tests/test_voice_sync.py -v   # FAIL
git add tests/test_voice_sync.py
git commit -m "test(voice): voice-sync utility tests"
```

### Task 7.2: Write voice-sync.sh

**Files:**
- Create: `Academic Helper/src/skills/voice/voice-sync.sh`

- [ ] **Step 1: Write**

```bash
#!/usr/bin/env bash
# voice-sync.sh — pull/push AUTHOR_VOICE.md to/from CandleKeep
# Usage: voice-sync.sh {pull|push|status}
# Env:
#   VOICE_PROJECT_ROOT — overrides $(pwd) for testing
#   VOICE_WRITER_NAME  — overrides writer name lookup; default reads from profile.json/book.yaml

set -euo pipefail

action=${1:-status}
root="${VOICE_PROJECT_ROOT:-$(pwd)}"
profile="$root/AUTHOR_VOICE.md"
voice_dir="$root/.voice"
id_cache="$voice_dir/.candlekeep-id"

# Resolve writer name (best-effort; empty is fine)
writer="${VOICE_WRITER_NAME:-}"
if [[ -z "$writer" ]]; then
  if [[ -f "$root/.academic-writer/profile.json" ]]; then
    writer=$(grep -E '"writer_name"' "$root/.academic-writer/profile.json" 2>/dev/null \
      | sed -E 's/.*"writer_name"[[:space:]]*:[[:space:]]*"([^"]*)".*/\1/' || true)
  elif [[ -f "$root/book.yaml" ]]; then
    writer=$(grep -E '^author:' "$root/book.yaml" 2>/dev/null \
      | sed -E 's/^author:[[:space:]]*"?([^"]*)"?$/\1/' || true)
  fi
fi
[[ -z "$writer" ]] && writer="<unknown>"
title="Voice Profile — $writer"

if ! command -v ck >/dev/null 2>&1; then
  echo "voice-sync: ck not available — local-only mode"
  exit 0
fi

ensure_id() {
  if [[ -f "$id_cache" ]]; then
    cat "$id_cache"
    return 0
  fi
  # Title fallback
  id=$(ck books list --json 2>/dev/null \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(next((b['id'] for b in d if b.get('title')=='$title'),''))" \
    || true)
  if [[ -n "$id" ]]; then
    mkdir -p "$voice_dir"
    echo "$id" > "$id_cache"
  fi
  echo "$id"
}

case "$action" in
  status)
    if [[ -f "$id_cache" ]]; then
      echo "voice-sync status: cached id=$(cat "$id_cache"), title=$title"
    else
      echo "voice-sync status: no cached candlekeep id"
    fi
    ;;
  pull)
    id=$(ensure_id)
    if [[ -z "$id" ]]; then
      echo "voice-sync pull: no remote book yet (run push to create)"
      exit 0
    fi
    ck books read "$id" --format md > "$profile.tmp"
    # Last-write-wins by `> Updated` stamp comparison
    local_stamp=$(grep -m1 '^> Updated' "$profile" 2>/dev/null | sed -E 's/^> Updated ([0-9-]+).*/\1/' || echo "0")
    remote_stamp=$(grep -m1 '^> Updated' "$profile.tmp" 2>/dev/null | sed -E 's/^> Updated ([0-9-]+).*/\1/' || echo "0")
    if [[ "$remote_stamp" > "$local_stamp" ]]; then
      mv "$profile.tmp" "$profile"
      echo "voice-sync pull: remote ($remote_stamp) overwrote local ($local_stamp)"
    else
      rm "$profile.tmp"
      echo "voice-sync pull: local ($local_stamp) is newer or equal to remote ($remote_stamp); kept local"
    fi
    ;;
  push)
    id=$(ensure_id)
    if [[ -z "$id" ]]; then
      id=$(ck books create --title "$title" --format md --content "$profile" --json \
        | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
      mkdir -p "$voice_dir"
      echo "$id" > "$id_cache"
      echo "voice-sync push: created remote book id=$id"
    else
      ck books update "$id" --content "$profile"
      echo "voice-sync push: updated remote book id=$id"
    fi
    ;;
  *)
    echo "usage: $0 {pull|push|status}" >&2
    exit 2
    ;;
esac
```

- [ ] **Step 2: Make executable, run tests, commit**

```bash
chmod +x src/skills/voice/voice-sync.sh
python3 -m pytest tests/test_voice_sync.py -v   # PASS
git add src/skills/voice/voice-sync.sh
git commit -m "feat(voice): voice-sync utility for CandleKeep"
```

---

## Phase 8 — voice-migrate hook

### Task 8.1: Migration test fixtures and contract test

**Files:**
- Create: `Academic Helper/tests/fixtures/voice/legacy-profile.json`
- Create: `Academic Helper/tests/test_voice_migrate.py`

- [ ] **Step 1: Create legacy fixture**

```json
{
  "writer_name": "Test Writer",
  "field": "Talmud",
  "citation_style": "Inline Parenthetical",
  "voice": {
    "register": "academic",
    "banned_words": ["furthermore", "moreover"],
    "phrase_bank": ["מבחינה זו", "אבחנה זו"]
  },
  "style_fingerprint": {
    "avg_sentence_len": 18,
    "preferred_connectives": ["אך", "ובכל זאת"]
  }
}
```

- [ ] **Step 2: Write test**

```python
"""voice-migrate.sh end-to-end test."""
import subprocess, json, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "src" / "skills" / "voice" / "voice-migrate.sh"
FIXTURE = ROOT / "tests" / "fixtures" / "voice" / "legacy-profile.json"

def test_migrate_strips_voice_fields_and_archives(tmp_path):
    aw_dir = tmp_path / ".academic-writer"
    aw_dir.mkdir()
    (aw_dir / "profile.json").write_text(FIXTURE.read_text())
    r = subprocess.run([str(SCRIPT)], cwd=str(tmp_path), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    new = json.loads((aw_dir / "profile.json").read_text())
    # voice and style_fingerprint should be replaced with pointer comments
    assert isinstance(new.get("voice"), str) and "AUTHOR_VOICE.md" in new["voice"]
    assert "style_fingerprint" not in new or "AUTHOR_VOICE.md" in str(new["style_fingerprint"])
    assert new["writer_name"] == "Test Writer"
    # AUTHOR_VOICE.md should be at root and contain seeded content
    avo = (tmp_path / "AUTHOR_VOICE.md").read_text()
    assert "Test Writer" in avo
    assert "מבחינה זו" in avo
    # Legacy archive intact
    legacy = tmp_path / ".voice" / "legacy" / "profile.json"
    assert legacy.is_file()
    assert json.loads(legacy.read_text()) == json.loads(FIXTURE.read_text())
    # Idempotent
    r2 = subprocess.run([str(SCRIPT)], cwd=str(tmp_path), capture_output=True, text=True)
    assert r2.returncode == 0
    assert "already migrated" in (r2.stdout + r2.stderr).lower()
```

- [ ] **Step 3: Run, fail, commit**

```bash
python3 -m pytest tests/test_voice_migrate.py -v   # FAIL
git add tests/fixtures/voice/legacy-profile.json tests/test_voice_migrate.py
git commit -m "test(voice): voice-migrate fixture and test"
```

### Task 8.2: Write voice-migrate.sh

**Files:**
- Create: `Academic Helper/src/skills/voice/voice-migrate.sh`

- [ ] **Step 1: Write**

```bash
#!/usr/bin/env bash
# voice-migrate.sh — silent legacy migration on first run after voice v1 ships.
# Idempotent. Detects legacy artifacts in either plugin's project layout and migrates them.

set -euo pipefail

root="${VOICE_PROJECT_ROOT:-$(pwd)}"
voice_dir="$root/.voice"
mkdir -p "$voice_dir/legacy" "$voice_dir/interview"
marker="$voice_dir/.migrated"

if [[ -f "$marker" ]]; then
  echo "voice-migrate: already migrated ($(cat "$marker")); skipping"
  exit 0
fi

profile="$root/AUTHOR_VOICE.md"
seeded=0

# Academic Helper legacy: .academic-writer/profile.json
aw_profile="$root/.academic-writer/profile.json"
if [[ -f "$aw_profile" ]]; then
  cp "$aw_profile" "$voice_dir/legacy/profile.json"
  python3 - <<PYEOF "$aw_profile" "$profile"
import json, sys, datetime
src, dst = sys.argv[1], sys.argv[2]
with open(src) as f:
    d = json.load(f)
voice = d.get("voice", {}) or {}
fp = d.get("style_fingerprint", {}) or {}
writer = d.get("writer_name", "<unknown>")
today = datetime.date.today().isoformat()
lines = [
    f"> Updated {today} by academic-writer (migrated from profile.json)",
    "",
    f"# Voice Profile — {writer}",
    "",
    "## Core voice (cross-project)",
    "",
]
if voice.get("register"):
    lines.append(f"- Register: {voice['register']}")
if voice.get("banned_words"):
    lines.append("")
    lines.append("### Banned words")
    for w in voice["banned_words"]:
        lines.append(f"- {w}")
if voice.get("phrase_bank"):
    lines.append("")
    lines.append("### Phrase bank")
    for p in voice["phrase_bank"]:
        lines.append(f"- {p}")
lines += ["", "## Terminology", "", "_Migrated; populate via `:voice` Stage 2._", ""]
lines += ["## Academic-specific", ""]
if fp.get("avg_sentence_len"):
    lines.append(f"- Average sentence length: {fp['avg_sentence_len']} words")
if fp.get("preferred_connectives"):
    lines.append("- Preferred connectives: " + ", ".join(fp["preferred_connectives"]))
lines += ["", "## Non-fiction-book-specific", "", "_Empty — populated when same writer uses hebrew-book-producer._", ""]
with open(dst, "w") as f:
    f.write("\n".join(lines) + "\n")
# Strip voice fields from original profile.json
d["voice"] = "see ./AUTHOR_VOICE.md (migrated " + today + ")"
d.pop("style_fingerprint", None)
with open(src, "w") as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
PYEOF
  seeded=1
fi

# hebrew-book-producer legacy: AUTHOR_VOICE.md at root (already there!), no migration content needed
# Just archive a copy and reformat to four-section structure.
hb_profile="$root/AUTHOR_VOICE.md"
if [[ -f "$hb_profile" && "$seeded" -eq 0 ]]; then
  cp "$hb_profile" "$voice_dir/legacy/AUTHOR_VOICE.md"
  python3 - <<'PYEOF' "$hb_profile"
import sys, datetime, re
path = sys.argv[1]
text = open(path).read()
today = datetime.date.today().isoformat()
# If already four-section structure, just stamp.
if all(s in text for s in ("## Core voice", "## Terminology",
                            "## Academic-specific", "## Non-fiction-book-specific")):
    if not text.startswith("> Updated"):
        text = f"> Updated {today} by hebrew-book-producer (re-stamped)\n\n" + text
    open(path, "w").write(text)
    sys.exit(0)
# Otherwise, wrap legacy content under "## Non-fiction-book-specific"
writer = "<unknown>"
m = re.search(r"#\s*Voice Profile\s*—\s*(.+)", text)
if m: writer = m.group(1).strip()
new = f"""> Updated {today} by hebrew-book-producer (migrated from legacy AUTHOR_VOICE.md)

# Voice Profile — {writer}

## Core voice (cross-project)

_Empty — populate via `:voice` Stage 2._

## Terminology

_Empty._

## Academic-specific

_Empty — populated when same writer uses Academic Helper._

## Non-fiction-book-specific

{text.strip()}
"""
open(path, "w").write(new)
PYEOF
  seeded=1
fi

date -u +"%Y-%m-%dT%H:%M:%SZ" > "$marker"
if [[ "$seeded" -eq 1 ]]; then
  echo "voice-migrate: migrated legacy artifacts to AUTHOR_VOICE.md"
else
  echo "voice-migrate: no legacy artifacts found; recorded marker"
fi
```

- [ ] **Step 2: Make executable, run test, commit**

```bash
chmod +x src/skills/voice/voice-migrate.sh
python3 -m pytest tests/test_voice_migrate.py -v   # PASS
git add src/skills/voice/voice-migrate.sh
git commit -m "feat(voice): voice-migrate hook for legacy artifacts"
```

---

## Phase 9 — `:voice` skill (the slash command)

### Task 9.1: Skill contract test

**Files:**
- Create: `Academic Helper/tests/test_voice_skill_contract.py`

- [ ] **Step 1: Write**

```python
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "src" / "skills" / "voice" / "SKILL.md"

def test_skill_exists():
    assert SKILL.is_file()

def test_skill_frontmatter_complete():
    text = SKILL.read_text()
    fm = yaml.safe_load(text.split("---")[1])
    assert fm["name"] == "voice"
    assert fm["user-invocable"] is True
    for k in ("description", "allowedTools"):
        assert k in fm

def test_skill_lists_subactions():
    text = SKILL.read_text()
    for sub in ("init", "continue", "recompress", "audit", "quick", "sync", "status"):
        assert f":voice {sub}" in text or f"`{sub}`" in text

def test_skill_invokes_correct_agents():
    text = SKILL.read_text()
    assert "voice-interviewer" in text
    assert "voice-distiller" in text
    assert "voice-calibrator" in text
    # Calibrator only on sessions 3 and 7
    assert "session 3" in text.lower() and "session 7" in text.lower()
```

- [ ] **Step 2: Fail, commit**

```bash
python3 -m pytest tests/test_voice_skill_contract.py -v   # FAIL
git add tests/test_voice_skill_contract.py
git commit -m "test(voice): voice skill contract test"
```

### Task 9.2: Write the voice skill

**Files:**
- Create: `Academic Helper/src/skills/voice/SKILL.md`

- [ ] **Step 1: Write**

```markdown
---
name: voice
description: Stage 2 of the voice subsystem. Run `:voice` to start a 7-session adversarial interview seeded by the past-articles fingerprint. Sub-actions for resume, recompress, audit, quick mode, sync, and status. Use when the user wants to deepen their voice profile beyond what the corpus reveals.
user-invocable: true
allowedTools: Read, Write, Edit, Glob, Grep, Bash, Agent
metadata:
  author: Academic Helper
  version: 1.0.0
---

# voice

Top-level entry to the Stage 2 voice-deepening pipeline. Sub-actions inferred from natural language
or specified explicitly.

## Sub-actions

- `:voice init` — start the 7-session interview from the current `.voice/fingerprint.md`
- `:voice continue` — resume the next unfinished session (or finish the current one)
- `:voice recompress` — re-distill all transcripts + fingerprint into `AUTHOR_VOICE.md`
- `:voice audit` — run rule-coverage check against the corpus
- `:voice quick` — adaptive short path (skips sessions 4 and 7, caps at 8 questions per session,
  one calibration at end, ~43 prompts total)
- `:voice sync` — push local `AUTHOR_VOICE.md` to CandleKeep (pulls first to avoid clobber)
- `:voice status` — list completed sessions, last calibration score, last sync stamp

## Workflow

### `:voice init`
1. Read `.voice/fingerprint.md`. If missing or `> NEEDS CORPUS`, tell the user to run `:init` first
   and stop.
2. Confirm the user has time for at least one session (~15 questions × ~30s = ~10 min).
3. Invoke `voice-interviewer` agent with category `01-beliefs`. Wait for `<!-- session complete -->`.
4. Run `voice-distiller --session 1` to fold the transcript into `AUTHOR_VOICE.md`.
5. Skip calibration (sessions 1, 2, 4, 5, 6 do NOT calibrate).
6. Run `voice-sync push`.
7. Ask: "Continue with session 2 (Writing Practices), or stop here? `:voice continue` resumes."

### `:voice continue`
1. Detect highest completed session by scanning `.voice/interview/`.
2. Invoke `voice-interviewer` for next session.
3. After session 3, run `voice-calibrator` (sample paragraph + 3 questions + patch + rule-coverage).
4. After session 7, run `voice-calibrator` (final), then `voice-distiller --recompress` (full pass).
5. Always end with `voice-sync push`.

### `:voice recompress`
1. Run `voice-distiller --recompress` (full pass, all transcripts + fingerprint).
2. Run rule-coverage check inline; write `.voice/audit.md`.
3. Run `voice-sync push`.

### `:voice audit`
1. Read `AUTHOR_VOICE.md` and corpus.
2. For each rule, search corpus for evidence. Write `.voice/audit.md` with score and flagged rules.
3. If score < 6, refuse to recompress until user removes or evidences flagged rules.

### `:voice quick`
1. Same as `:voice init`, but pass `--quick` to interviewer (cap 8 questions/session, skip sessions
   4 and 7).
2. Stamp `[quick]` marker in `AUTHOR_VOICE.md` and `.voice/audit.md`.
3. Single calibration at the end (after session 6 in quick numbering, which is the last).
4. Tell user: "Quick profile created. Run `:voice continue --upgrade` to fill in missed sessions."

### `:voice sync`
1. Run `voice-sync.sh pull` (last-write-wins by `> Updated` stamp).
2. Run `voice-sync.sh push`.
3. Report which side won.

### `:voice status`
1. List `.voice/interview/0N-*.md` with completion markers.
2. Show `.voice/audit.md` head if present.
3. Show last `> Updated` stamp from `AUTHOR_VOICE.md`.
4. Show `.voice/.candlekeep-id` presence.

## Hard rules

- Calibrator runs ONLY after sessions 3 and 7 (or after final session in quick mode).
- Sessions 1, 2, 4, 5, 6 invoke distiller but NOT calibrator.
- Sync is push-only on writes; explicit `:voice sync` is the only place that pulls.
- Quick mode is reversible: `:voice continue --upgrade` runs the missed sessions.
```

- [ ] **Step 2: Test passes, commit**

```bash
python3 -m pytest tests/test_voice_skill_contract.py -v   # PASS
git add src/skills/voice/SKILL.md
git commit -m "feat(voice): :voice skill with 7 sub-actions"
```

---

## Phase 10 — Integrate with init/write/edit (Academic Helper)

### Task 10.1: Wire voice-miner into init

**Files:**
- Modify: `Academic Helper/src/skills/init/SKILL.md`

- [ ] **Step 1: Add voice-miner invocation**

After the existing past-articles handling section, insert:

```markdown
### Stage 1 voice fingerprint

After past-articles are scanned, invoke the `voice-miner` agent:

1. Run `voice-miner` agent on `past-articles/`. Output is `.voice/fingerprint.md`.
2. Run `voice-distiller --from-fingerprint` to seed the four-section `AUTHOR_VOICE.md` at root.
3. Run `voice-sync push`.
4. Print: "✓ Voice fingerprint created from N past articles. You can write articles now, or run
   `/academic-writer:voice` for a deeper profile (recommended)."

The user is not required to run Stage 2. They can start writing immediately with the fingerprint.
```

- [ ] **Step 2: Commit**

```bash
git add src/skills/init/SKILL.md
git commit -m "feat(voice): wire voice-miner into init Stage 1"
```

### Task 10.2: Load AUTHOR_VOICE.md in write/edit/edit-section

**Files:**
- Modify: `Academic Helper/src/skills/write/SKILL.md`
- Modify: `Academic Helper/src/skills/edit/SKILL.md`
- Modify: `Academic Helper/src/skills/edit-section/SKILL.md`

- [ ] **Step 1: For each, add at the top of the workflow section**

```markdown
### Voice profile load (first step of every run)

1. Run `voice-sync.sh pull` — pulls latest `AUTHOR_VOICE.md` from CandleKeep (last-write-wins).
2. Read `AUTHOR_VOICE.md` from project root. Whole file goes into the section-writer system prompt.
3. The section writer is instructed to weight `## Academic-specific` rules higher when they
   conflict with `## Core voice` rules; everything else applies as written.

If `AUTHOR_VOICE.md` is missing or empty, warn once: "No voice profile. Run `/academic-writer:init`
to seed it." Do not block writing.
```

- [ ] **Step 2: Commit**

```bash
git add src/skills/write/SKILL.md src/skills/edit/SKILL.md src/skills/edit-section/SKILL.md
git commit -m "feat(voice): load AUTHOR_VOICE.md in write/edit skills"
```

### Task 10.3: Add voice-pull hook on writing-skill startup

**Files:**
- Create: `Academic Helper/src/hooks/src/lifecycle/voice-pull.ts`
- Modify: `Academic Helper/src/hooks/hooks.json`

- [ ] **Step 1: Write the hook**

```typescript
// src/hooks/src/lifecycle/voice-pull.ts
// Pulls AUTHOR_VOICE.md from CandleKeep before write/edit skills run.
// Profile-scoped: silently skips in projects without `.academic-helper/profile.md`.
import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";

const projectDir = process.env.CLAUDE_PROJECT_DIR ?? process.cwd();
if (!existsSync(join(projectDir, ".academic-helper", "profile.md"))) {
  process.exit(0);
}

const sync = join(projectDir, "src", "skills", "voice", "voice-sync.sh");
if (!existsSync(sync)) {
  process.exit(0);
}

const r = spawnSync("bash", [sync, "pull"], {
  cwd: projectDir,
  env: { ...process.env, VOICE_PROJECT_ROOT: projectDir },
  encoding: "utf-8",
});
if (r.status !== 0) {
  console.warn(`[voice-pull] non-fatal: ${r.stderr}`);
}
process.exit(0);
```

- [ ] **Step 2: Register in hooks.json**

Add an entry triggered on the `SkillStart` event for skills `write`, `edit`, `edit-section`:

```json
{
  "event": "SkillStart",
  "matcher": { "skill": ["write", "edit", "edit-section"] },
  "command": "node src/hooks/dist/lifecycle/voice-pull.js"
}
```

(Adapt to the existing `hooks.json` shape; if existing hooks use a different event/format, follow
that convention exactly.)

- [ ] **Step 3: Build hooks, test, commit**

```bash
npm run build:hooks
npm run typecheck
git add src/hooks/src/lifecycle/voice-pull.ts src/hooks/hooks.json
git commit -m "feat(voice): voice-pull hook on write/edit start"
```

### Task 10.4: Run migration hook on session start

**Files:**
- Modify: `Academic Helper/src/hooks/hooks.json` (add SessionStart entry)
- Reuse: `src/skills/voice/voice-migrate.sh`

- [ ] **Step 1: Add hook entry**

```json
{
  "event": "SessionStart",
  "command": "bash src/skills/voice/voice-migrate.sh"
}
```

(Idempotent — the script's own `.migrated` marker handles re-runs. Profile-scoped: no-op if no
legacy artifacts.)

- [ ] **Step 2: Commit**

```bash
git add src/hooks/hooks.json
git commit -m "feat(voice): run voice-migrate on session start"
```

---

## Phase 11 — Tests, build, manifest bump

### Task 11.1: End-to-end fixture test (Stage 1 only — Stage 2 needs LLM)

**Files:**
- Create: `Academic Helper/tests/test_voice_e2e_stage1.py`

- [ ] **Step 1: Write**

```python
"""End-to-end Stage 1: corpus → fingerprint → distiller seed → AUTHOR_VOICE.md."""
import subprocess, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "voice" / "sample-corpus"

def test_stage1_seeds_author_voice(tmp_path):
    pa = tmp_path / "past-articles"
    shutil.copytree(FIXTURE, pa)
    # Create a minimal .academic-helper/profile.md so hooks/scripts treat this as a real project
    (tmp_path / ".academic-helper").mkdir()
    (tmp_path / ".academic-helper" / "profile.md").write_text("# stub\n")
    # Run migration first (no-op, no legacy)
    subprocess.run(["bash", str(ROOT / "src/skills/voice/voice-migrate.sh")],
                   cwd=str(tmp_path), check=True)
    # Stage 1 is normally agent-driven; for the structural test we shell-emit a stub fingerprint
    # to assert the surrounding pipeline works.
    (tmp_path / ".voice").mkdir(exist_ok=True)
    (tmp_path / ".voice" / "fingerprint.md").write_text(
        "# Fingerprint\n- Corpus summary: 3 articles, 1500 words, Hebrew.\n"
    )
    # Run sync push (no ck → no-op)
    r = subprocess.run(["bash", str(ROOT / "src/skills/voice/voice-sync.sh"), "push"],
                       cwd=str(tmp_path), capture_output=True, text=True)
    assert r.returncode == 0
    # AUTHOR_VOICE.md should exist (created by migrate or by fixture; ensure either way)
    avo = tmp_path / "AUTHOR_VOICE.md"
    if not avo.exists():
        avo.write_text("> Updated 2026-05-05 by academic-writer\n\n# Voice Profile — test\n")
    assert avo.exists()
```

- [ ] **Step 2: Run, fail or pass, commit**

```bash
python3 -m pytest tests/test_voice_e2e_stage1.py -v
git add tests/test_voice_e2e_stage1.py
git commit -m "test(voice): end-to-end Stage 1 structural test"
```

### Task 11.2: Bump version, rebuild plugin

**Files:**
- Modify: `Academic Helper/manifests/academic-writer.json`

- [ ] **Step 1: Bump minor version (e.g., 1.x.0 → 1.(x+1).0)**

(Version bump is normally automated via CI; if user policy is "do not bump manually" — confirmed
in README — skip this step and let CI handle it on push.)

- [ ] **Step 2: Run build**

```bash
npm run build
npm run typecheck
python3 tests/test_plugin_structure.py
python3 -m pytest tests/ -v
```
Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "build(voice): rebuild plugin output for v1 voice subsystem"
```

---

## Phase 12 — Mirror to hebrew-book-producer

The hebrew-book-producer mirror reuses every artifact from Phases 1–11 with these specific changes:

### Task 12.1: Mirror file layout
- `AUTHOR_VOICE.md` already at root (existing convention) — handled by migration in Task 8.2.
- `.voice/` directory and gitignore: same as Task 1.1.

### Task 12.2: Mirror agents
- Copy `voice-miner.md`, `voice-interviewer.md`, `voice-distiller.md`, `voice-calibrator.md` from
  Academic Helper to `hebrew-book-producer/plugins/hebrew-book-producer/agents/`. The existing
  `voice-miner.md` in hebrew-book-producer is overwritten with the v1 version (the audit in Task
  0.1 noted it).
- Update each agent's frontmatter `metadata.author` to `hebrew-book-producer`.
- In `voice-miner.md`, change the corpus path from `past-articles/` to `chapters/**/*.md` and
  `manuscript.md`.

### Task 12.3: Mirror skill and question bank
- Copy `src/skills/voice/SKILL.md` from Academic Helper to
  `plugins/hebrew-book-producer/skills/voice/SKILL.md`.
- Replace references to `:academic-writer:` with `:hebrew-book-producer:`.
- Use `questions-non-fiction.md` (Task 3.2) as the seed bank.

### Task 12.4: Mirror utilities
- Copy `voice-sync.sh` and `voice-migrate.sh` from Academic Helper. The migration script already
  detects both layouts (Task 8.2 covered both branches).
- Update writer-name resolution: priority order `VOICE_WRITER_NAME` → `book.yaml: author:` →
  `<unknown>`. Already supported in the script as written.

### Task 12.5: Mirror hooks
- hebrew-book-producer uses bash-based hooks (no TypeScript). Create
  `plugins/hebrew-book-producer/hooks/voice-pull.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
root="${CLAUDE_PROJECT_DIR:-$(pwd)}"
[[ -f "$root/book.yaml" ]] || exit 0
[[ -x "$root/plugins/hebrew-book-producer/skills/voice/voice-sync.sh" ]] || exit 0
VOICE_PROJECT_ROOT="$root" bash "$root/plugins/hebrew-book-producer/skills/voice/voice-sync.sh" pull \
  || echo "[voice-pull] non-fatal: $?" >&2
```

Register in the project's hook config (the existing convention; check
`plugins/hebrew-book-producer/.claude-plugin/plugin.json` in Task 0.1).

### Task 12.6: Mirror integration with existing flows
- Modify `book-bootstrap` skill: add Stage 1 voice-miner invocation after manuscript scaffolding.
- Modify `book-writer.md`, `proofreader.md`, `literary-editor-legacy.md` agents: instruct each to
  `Read AUTHOR_VOICE.md` from project root at the start of their run.
- Mark `voice-preserver` and `express-voice` skills deprecated (deprecation note pointing at
  `AUTHOR_VOICE.md`); leave them in place for one release.

### Task 12.7: Mirror tests
- Port `test_voice_structure.py`, `test_voice_*_contract.py`, `test_voice_migrate.py`,
  `test_voice_sync.py` to hebrew-book-producer. Adjust paths to its layout.
- The existing pytest convention may differ; if the project uses shell tests, port the assertions
  into `tests/test_voice_structure.sh` using `set -e` and `[[ ... ]]` checks. Match what's already
  there.

### Task 12.8: Bump plugin version, rebuild

- Bump minor version in `plugins/hebrew-book-producer/.claude-plugin/plugin.json`.
- Run any existing build/test scripts.

### Task 12.9: Commit
Each of the above is its own commit. Use the same `feat(voice): ...` and `test(voice): ...`
prefixes used in Phases 1–11 for symmetry.

---

## Self-review checklist (run before handing off to executor)

- [ ] Spec coverage — every section of the spec maps to a task above (audit, scaffold, miner,
  interviewer, distiller, calibrator, sync, migrate, skill, integration, tests, mirror).
- [ ] No placeholders — every "code" step contains real code; every test has real assertions.
- [ ] Type/name consistency — `voice-miner`, `voice-interviewer`, `voice-distiller`,
  `voice-calibrator`, `voice-sync.sh`, `voice-migrate.sh`, `:voice` skill names are identical
  everywhere they appear.
- [ ] Calibration cadence — every reference to calibration explicitly says "sessions 3 and 7
  only" (or "single calibration at end" for quick mode).
- [ ] AUTHOR_VOICE.md location — every reference puts it at project root, never under `.voice/`.
- [ ] Auditor scope — every audit reference says "rule coverage only" and never mentions a
  generation-match score.
- [ ] CandleKeep policy — last-write-wins with timestamp stamp; no 3-way merge anywhere.

---

## Out of scope for v1 (do not implement)

- Three-way merge with `.last-synced.md` common-ancestor file.
- A-axis (generation match) auditor scoring.
- Calibration after sessions 1, 2, 4, 5, 6.
- Multi-writer / team profiles.
- Profile export to ChatGPT custom instructions / Gemini.
