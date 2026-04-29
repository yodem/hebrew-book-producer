# hebrew-book-producer

A Claude Code plugin that turns a Hebrew manuscript into a print-ready book through a fully orchestrated pipeline of specialist sub-agents — modelled on how an Israeli publishing house actually produces a book.

> ספרי עיון, אוטוביוגרפיה, פילוסופיה, וטקסטים דתיים. בעברית. מההערכה הראשונית של כתב היד עד הקובץ המוכן לדפוס.

## What it does

| Stage | Hebrew name | Agent | What it produces |
|---|---|---|---|
| Manuscript appraisal | קריאת לקטור | `lector` | `LECTOR_REPORT.md` |
| Literary editing | עריכה ספרותית | `literary-editor` | Track-changes draft + structural notes |
| Linguistic editing | עריכה לשונית | `linguistic-editor` | Sentence-level Hebrew edits |
| Proofreading | הגהה | `proofreader` | Two passes — pre-typesetting and post-typesetting |
| Typesetting brief | עימוד | `typesetting-agent` | InDesign / LaTeX hand-off brief (Frank Ruhl Libre, RTL) |
| Pipeline orchestration | ניהול הפקה | `production-manager` | Schedules sub-agents, tracks word count in גיליון דפוס (24,000 chars) |

## Runtime dependencies

This plugin **does not bundle** any of the following — they must be installed separately:

1. **CandleKeep** (`ck` CLI) — long-term project memory. The plugin reads the user's writing-craft compendium *The Writer's Guide: How to Write, Edit, and Proofread a Book* (item ID `cmok9h0m10ahik30zt8yt0lt2`) at session start. Falls back gracefully if missing.
2. **Superpowers** — provides `$plan-review-gate`, `$design-review-gate`, and the `writing-skills/anthropic-best-practices` reference used by the senior agents.
3. **Metaswarm** — provides `$start`, `$orchestrated-execution`, and the multi-agent spawn conventions used by `production-manager`.

If any are missing, the plugin still works in degraded single-agent mode.

## Install (local development)

```bash
cd ~/dev/hebrew-book-producer
claude plugin install --local .
# or symlink into ~/.claude/plugins/local/
```

## Quick start

```bash
cd /path/to/your/manuscript
/init                           # creates book.yaml + AUTHOR_VOICE.md skeleton
/lector manuscript.md           # initial appraisal
/edit                           # literary + linguistic edit
/proof                          # proofreading
/typeset                        # generate typesetting brief
/ship                           # full pipeline end-to-end
```

## Memory architecture

| File | Purpose | Versioned in git? |
|---|---|---|
| `book.yaml` | Project metadata: title, author, genre, citation style, word target, niqqud on/off | yes |
| `AUTHOR_VOICE.md` | Voice fingerprint: example paragraphs, preferred/banned phrases, register, persona | yes |
| `.book-producer/memory.md` | Rolling log of user corrections (what the AI got wrong) | no |
| `.book-producer/state.json` | Pipeline state per chapter | no |
| `.ctx/writers-guide.md` | Cached copy of the CandleKeep writer's guide | no |

## Hebrew architecture document

The full Hebrew design document is at [`README.he.md`](./README.he.md).

## Status

`v0.1.0` — scaffold only. Agents and skills have stub bodies; reference data (Hebrew connectives, typography rules) is filled in. See `CLAUDE.md` for what each component should grow into.

## License

MIT.
