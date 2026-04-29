---
description: Show plugin help — what hebrew-book-producer does and how to use it.
---

# /help — hebrew-book-producer

A Claude Code plugin for the Israeli book-production pipeline in Hebrew. Lector → literary edit → linguistic edit → proofread → typeset.

## Commands

| Command | Purpose |
|---|---|
| `/init` | Bootstrap a new project (book.yaml, AUTHOR_VOICE.md, .claude/) |
| `/lector <file>` | Initial manuscript appraisal — produces LECTOR_REPORT.md |
| `/edit [chapter]` | Literary + linguistic edit |
| `/proof [chapter]` | Proofreading (pass 1 or 2 — auto-detected) |
| `/typeset` | Typesetting brief (Frank Ruhl Libre, RTL, גיליון דפוס) |
| `/ship <file>` | Full pipeline with checkpoints |
| `/voice` | Update AUTHOR_VOICE.md from accumulated feedback |
| `/help` | This help |

## Agents

- **production-manager** (opus) — orchestrator; never writes prose.
- **lector** (opus) — manuscript appraisal.
- **literary-editor** (opus) — macro-level structure, voice, theme.
- **linguistic-editor** (sonnet) — sentence-level Hebrew, register, AI-marker removal.
- **proofreader** (sonnet) — typos, niqqud, layout artefacts. Two passes.
- **typesetting-agent** (sonnet) — typesetting brief.

## Skills

- review-style — Burstiness, AI-marker detection.
- voice-preserver — enforces AUTHOR_VOICE.md rules.
- cite-master — citation consistency (Chicago / APA / Hazal).
- hebrew-connectives — logical connector reference.
- hebrew-typography — fonts, margins, layout.
- niqqud-pass — vowel-pointing proofread (poetry / religious).
- hazal-citation — religious-source citation conventions.
- candlekeep-writers-guide — loads the canonical writer's guide at session start.

## Runtime dependencies

- **CandleKeep** — for the writer's guide. Plugin runs in degraded mode without it.
- **Superpowers** — for plan-review-gate / design-review-gate.
- **Metaswarm** — for multi-agent orchestration.

## Genre support

`philosophy` / `autobiography` / `religious` / `popular-science` / `mixed`. Set in `book.yaml`. Different genres activate different skill combinations — see `CLAUDE.md`.

## More

- Architecture in Hebrew: see `README.he.md` in plugin root.
- Architecture in English: see `README.md` in plugin root.
