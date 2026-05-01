# CandleKeep Author Profile — Design Spec
_Date: 2026-05-01_

## Problem

`AUTHOR_VOICE.md` and `.book-producer/profile.json` are local files scoped to a single book project. An author working on multiple books must copy or rebuild the profile for each project. The flat 200-line MD format also caps the richness of the voice fingerprint.

## Solution

Store the author profile as a multi-page CandleKeep book. It belongs to the author, not to any book project. All book projects for the same author reference it by ID. The `SessionStart` hook pulls `overview.md` into `.ctx/` each session; agents load deeper pages on demand. Every `/voice` correction auto-pushes to CandleKeep immediately.

---

## CandleKeep Book Structure

Book slug: `author-profile-<author-slug>` (e.g. `author-profile-yotam-fromm`)

| Page | Content | Loaded by |
|---|---|---|
| `overview.md` | Register, stance, banned/preferred phrase summary — replaces current AUTHOR_VOICE.md | Every agent via `.ctx/author-profile.md` |
| `voice-fingerprint.md` | Statistical data: sentence length distribution, burstiness score, vocabulary richness, paragraph shape | voice-miner (on update) |
| `reference-paragraphs.md` | 20–30 verbatim representative passages | book-writer, lector |
| `banned-phrases.md` | Full list with context: why banned, wrong form vs right form | linguistic-editor, proofreader |
| `preferred-phrases.md` | Preferred collocations with example sentences | book-writer, literary-editor |
| `chapter-patterns.md` | How author opens/closes chapters, transitions between ideas | book-writer |
| `source-style.md` | How author integrates Hazal citations, block quotes, inline references | cite-master |
| `register-examples.md` | Concrete examples of register shifts — when and how the author goes high/low | linguistic-editor |

---

## book.yaml Schema Change

Add one field:

```yaml
author_profile_book: "author-profile-yotam-fromm"  # CandleKeep book ID; empty = no profile yet
```

---

## Data Flow

### Session start
```
SessionStart hook
  → ck read author-profile-<slug>/overview.md
  → write to .ctx/author-profile.md
```
Deep pages are pulled on-demand by individual agents during the session.

### /init — existing author (profile exists)
```
/init
  → reads book.yaml → finds author_profile_book
  → pulls overview.md from CandleKeep
  → writes to .ctx/author-profile.md
  → skips AUTHOR_VOICE.md skeleton and voice interview entirely
  → stores author_profile_book in new project's book.yaml
```

### /init — new author (no profile)
```
/init
  → book.yaml has no author_profile_book
  → triggers voice-miner (heavy if past-books/ has files, light otherwise)
  → voice-miner creates CandleKeep book with all pages
  → stores returned book ID in book.yaml as author_profile_book
```

### /voice (correction accepted)
```
/voice update
  → updates .ctx/author-profile.md locally
  → immediately pushes diff to the relevant CandleKeep page (auto-sync)
  → no manual publish step
```

### voice-miner (refresh)
```
/voice refresh  (or re-run voice-miner)
  → reads past-books/ OR CandleKeep source books
  → regenerates all pages
  → updates CandleKeep book (never deletes, always merges)
```

---

## Component Changes

| Component | Change |
|---|---|
| `hooks/session-start` | Pull `overview.md` into `.ctx/author-profile.md` after existing CandleKeep loads |
| `commands/init.md` | Check `author_profile_book` field; skip AUTHOR_VOICE.md skeleton if found; trigger voice-miner for new authors |
| `agents/voice-miner.md` | Write output to CandleKeep pages instead of local AUTHOR_VOICE.md + profile.json |
| `commands/voice.md` | After local `.ctx/` update, push diff to CandleKeep immediately |
| All agents | Already read `.ctx/author-profile.md`; add on-demand deep page loading where needed |
| `book.yaml` schema | Add `author_profile_book` field (empty string = no profile) |

---

## What Does NOT Change

- Agents continue to read `.ctx/author-profile.md` for `overview.md` — no agent refactoring needed for basic operation
- `past-books/` local folder still works as input source for voice-miner heavy path
- `.book-producer/memory.md` still accumulates corrections between `/voice` runs

---

## Out of Scope

- Migration of existing local `AUTHOR_VOICE.md` files to CandleKeep (manual one-time step for existing projects)
- Multi-author profiles (one author per project, always)
- Conflict resolution if two sessions push simultaneously (last-write-wins, acceptable for single-author use)
