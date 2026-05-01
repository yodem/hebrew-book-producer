---
name: candlekeep-writers-guide
description: Bridge skill that loads the AUTHOR'S CURATED KNOWLEDGE LAYER from CandleKeep at session start — Writer's Guide (King/Zinsser/Penn/Shapiro), Agent-Team guide, the author's per-project thesis notebook (optional), and any craft_extras the author lists in book.yaml. NOT used for canonical religious texts — those go through Sefaria. Caches everything under .ctx/ so all editing agents share one read.
user-invocable: false
---

# candlekeep-writers-guide — load the master guide

## When to invoke

- Once per session, at the start. The CLAUDE.md loads this skill via `scripts/load-candlekeep-guide.sh`.
- On user request: `/help writers-guide`.

## What it does

Runs (delegated to `scripts/load-candlekeep-guide.sh`):

```bash
mkdir -p .ctx
ck items get cmok9h0m10ahik30zt8yt0lt2 > .ctx/writers-guide.md
ck items get cmnudfue5003rmy0zlxt7ioa1 > .ctx/agent-team-guide.md
ck items get cmomjonvy0fdmk30zwef79c48 > .ctx/hebrew-linguistic-reference.md
```

The third item is the shared **Hebrew Linguistic Reference** book (id `cmomjonvy0fdmk30zwef79c48`) — synced from the public GitHub repo [yodem/hebrew-linguistics-data](https://github.com/yodem/hebrew-linguistics-data). It is also consumed by the `academic-writer` plugin so the two plugins share one source of truth for Hebrew editorial knowledge.

If `ck` is not on PATH, or the item is not accessible, write a minimal stub to `.ctx/writers-guide.md`:

```markdown
# Writer's Guide — STUB

CandleKeep is not available. The plugin runs in degraded mode without
craft references. Install CandleKeep CLI and run `ck auth login` to enable.
```

…and continue without blocking.

## What's in the guide (when loaded)

The full v2 of the user's writer's compendium. 11 chapters + 2 appendices:

| Chapter | What it covers | Cite from when… |
|---|---|---|
| Ch. 1 — The Great Commandment | Read a lot, write a lot, 2,000 words/day | Author asks about discipline |
| Ch. 2 — The Writer's Toolbox | Vocabulary, grammar, adverbs, paragraph rhythm | Linguistic-editor needs sentence-level rules |
| Ch. 3 — On the Page | Description, dialogue, character | Literary-editor working on autobiography |
| Ch. 4 — Story First, Theme After | Situation vs. plot, fossil metaphor | Literary-editor finding the spine |
| Ch. 5 — The Two-Draft Method | Closed-door / open-door, 6-week rest, 10% formula | Production-manager scheduling rounds |
| Ch. 6 — The Four Stages of Editing | Developmental → line → copy → proof | Pipeline state-management |
| Ch. 7 — Editing in Hebrew | עריכה ספרותית / לשונית / הגהה — the 4 levels of proofreading | Linguistic-editor + proofreader |
| Ch. 8 — Non-Fiction Structure | Thesis vs. topic, 5 core structures, chapter promises | Lector + literary-editor |
| Ch. 9 — Zinsser's Principles of Non-Fiction | Simplicity, clutter, style, audience | Linguistic-editor's primary reference |
| Ch. 10 — Penn's Practical Pipeline | Research, AI tools, professional editing | Production-manager + author onboarding |
| Ch. 11 — Shapiro on the Writing Life | Toehold, habit, blank page | Author psychology / writer's block |
| Appendix A | 30-rule quick reference | Quick lookup for any agent |
| Appendix B | 37+ source citations | Recommending further reading |

## How agents use it

In every editing agent's session-start:

```
Read .ctx/writers-guide.md (full file is ~85 KB / ~1,500 lines)
When you need a specific rule, jump to the chapter named in the table above.
Quote it with chapter reference, e.g.:
  "Per writers-guide Ch. 5 §5, apply the 10% formula: 2nd draft = 1st draft − 10%."
```

## Hard rules

- **Cache once per session.** Re-fetching CandleKeep on every agent spawn is wasteful.
- **Fail open.** If CandleKeep is unavailable, write the stub and continue. Do not block the pipeline.
- **Don't paste it into manuscripts.** The guide informs decisions; it is not source material to quote inside the book.
- **Don't mutate it.** The guide is updated separately via the `/learn-toolkit:learn` workflow on the user's CandleKeep, not from this plugin.
