---
description: Show plugin help — what hebrew-book-producer does and how to use it.
---

# /help — hebrew-book-producer

A Claude Code plugin for the Israeli book-production pipeline in Hebrew. Lector → literary edit → linguistic edit → proofread → typeset.

## The one-command entry-point

| Command | Purpose |
|---|---|
| **`/start <action> [chapter]`** | **Auto-bootstrap + dispatch.** Use this 99% of the time. Or just type a freeform Hebrew/English sentence — the natural-language router (in CLAUDE.md) maps it to `/start <action>` automatically. |

Examples:
- *"תוכל להגיה את הספר שלי?"* → `/start proofread`
- *"תכתוב לי פרק 3"* → `/start write ch3`
- *"תקרא ותגיד לי מה אתה חושב"* → `/start lector`

## Underlying slash commands (advanced)

| Command | Purpose |
|---|---|
| `/init` | Interactive long-form project bootstrap (`/start init` is the short form) |
| `/init-voice` | Full 10-question voice fingerprint (`/start` uses the 3-question express path) |
| `/lector <file>` | Manuscript appraisal — produces LECTOR_REPORT.md |
| `/edit [chapter]` | Literary + linguistic edit |
| `/proof [chapter]` | Proofreading (pass 1 or 2 — auto-detected) |
| `/typeset` | Typesetting brief (Frank Ruhl Libre, RTL, גיליון דפוס) |
| `/draft <chapter>` | Book-writer drafts a chapter from a brief |
| `/ship <file>` | Full pipeline with checkpoints |
| `/voice` | Update AUTHOR_VOICE.md from accumulated feedback |
| `/thesis [append\|show\|refresh]` | Manage the author's CandleKeep thesis notebook for this book |
| `/help` | This help |

## Agents

- **production-manager** (opus) — orchestrator; never writes prose.
- **lector** (opus) — manuscript appraisal.
- **literary-editor** (opus) — macro-level structure, voice, theme.
- **linguistic-editor** (sonnet) — sentence-level Hebrew, register, AI-marker removal.
- **proofreader** (sonnet) — typos, niqqud, layout artefacts. Two passes.
- **typesetting-agent** (sonnet) — typesetting brief.
- **voice-miner** (opus) — author voice/style fingerprint extraction (heavy/light auto-detect).
- **book-writer** (opus) — drafts a chapter from a brief, with per-genre conventions (biography / philosophy / religious / popular-science).

## Skills

- book-bootstrap — auto-detects manuscript and scaffolds a project. Used by `/start`.
- express-voice — 3-question fast voice fingerprint (vs `/init-voice`'s 10).
- review-style — Burstiness, AI-marker detection.
- voice-preserver — enforces AUTHOR_VOICE.md rules.
- cite-master — citation consistency (Chicago / APA / Hazal). Includes inline Sefaria-MCP verification routine for religious primary sources.
- hebrew-connectives — logical connector reference.
- hebrew-typography — fonts, margins, layout.
- niqqud-pass — vowel-pointing proofread (poetry / religious).
- candlekeep-writers-guide — loads the canonical writer's guide + Hebrew Linguistic Reference at session start.

## Runtime dependencies

- **CandleKeep** — author's curated knowledge layer (writer's guide, thesis notebook, craft extras). Plugin runs in degraded mode without it.
- **Sefaria MCP** — canonical-text validator for every Hazal citation (sole validator). Citations that can't be validated get marked `[UNVERIFIED]`.

## Genre support

`philosophy` / `autobiography` / `religious` / `popular-science` / `mixed`. Set in `book.yaml`. Different genres activate different skill combinations — see `CLAUDE.md`.

## More

- Architecture in Hebrew: see `README.he.md` in plugin root.
- Architecture in English: see `README.md` in plugin root.
