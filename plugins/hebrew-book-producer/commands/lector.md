---
description: Run an initial manuscript appraisal (קריאת לקטור) on a draft. Outputs LECTOR_REPORT.md with go / no-go recommendation.
argument-hint: <manuscript-file>
---

# /lector — manuscript appraisal

Run the **lector** agent on a draft manuscript file.

## Pre-flight

- Verify `book.yaml` exists. If not — refuse and tell the user to run `/init` first.
- Verify the argument file exists.
- The `SessionStart` hook normally caches `.ctx/writers-guide.md`. If missing, fall back to `bash ${CLAUDE_PLUGIN_ROOT}/scripts/load-candlekeep-guide.sh`.

## What happens

Spawn the `lector` agent with the manuscript file as input. The lector reads the entire manuscript and produces `LECTOR_REPORT.md` in the project root.

When the agent returns, summarise the report in 5 lines for the user and recommend the next action:

- If verdict is **Go** → `/edit`
- If verdict is **Go with major revisions** → describe what the author needs to fix first; do NOT auto-proceed.
- If verdict is **No-go** → describe why; offer to discuss before any further work.

Do NOT touch the manuscript itself. Lectorship is read-only.
