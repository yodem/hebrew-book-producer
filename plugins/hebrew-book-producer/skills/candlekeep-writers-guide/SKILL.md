---
name: candlekeep-writers-guide
description: Loads the author's curated knowledge layer (Writer's Guide, Agent-Team guide, Hebrew Linguistic Reference) from CandleKeep into .ctx/ at session start — delegated to the SessionStart hook so agents share one cached read. Invoked when .ctx/ cache is missing or stale. Do NOT use to fetch canonical religious texts — those go through Sefaria MCP.
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

The full v2 of the user's writer's compendium — 11 chapters + 2 appendices. Chapter index lives at `references/writers-guide-index.md` — load when an agent needs to know which chapter covers a given topic.

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
