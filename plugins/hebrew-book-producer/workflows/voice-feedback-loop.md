# Workflow — Author Voice Feedback Loop

How the plugin learns the author's voice over time, without ever overriding the author.

## The three-file pattern

| File | Versioned? | Written by | Read by |
|---|---|---|---|
| `AUTHOR_VOICE.md` | yes (project root) | Author + `/voice` command (with approval) | Every editing agent at session start |
| `.book-producer/memory.md` | no (gitignored) | `post-edit-feedback.sh` hook | Linguistic-editor at session start (last 50 lines) |
| `.book-producer/memory-archive.md` | no | `/voice` command (after compaction) | (rarely; debugging) |

## How feedback flows

```
┌──────────────────────────────────────────────┐
│  Linguistic-editor proposes Edit:            │
│    "אבל" → "אולם"                            │
│  Voice-preserver checks AUTHOR_VOICE.md.     │
│  No conflict. Edit applied.                  │
└────────┬─────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────┐
│  post-edit-feedback.sh hook fires.           │
│  Diff appended to .book-producer/memory.md.         │
└────────┬─────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────┐
│  Author reads diff. Decides: this is wrong.  │
│  Author manually reverts: "אולם" → "אבל".    │
│  post-edit-feedback.sh fires again, logging  │
│  the revert.                                 │
└────────┬─────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────┐
│  Next session: linguistic-editor reads       │
│  last 50 lines of .book-producer/memory.md.         │
│  Sees the revert. Adjusts behaviour.         │
│  Same conversation: maybe converts back to   │
│  "אבל". The author isn't pestered again.     │
└────────┬─────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────┐
│  After ~3 reverts of the same kind, /voice   │
│  proposes a permanent rule:                  │
│    "Add 'אולם' to BANNED PHRASES?"           │
│  Author approves once. Rule lands in         │
│  AUTHOR_VOICE.md (versioned).                │
└──────────────────────────────────────────────┘
```

## When to run /voice

- After every 5–10 hours of editing — when `.book-producer/memory.md` accumulates ~200 lines.
- Before starting a new chapter (so any patterns get baked in).
- Before sharing the project with collaborators (so the voice rules are codified).

## What /voice does NOT do

- It does not auto-add rules. Every rule requires author approval.
- It does not read the past. It looks at the recent log only.
- It does not delete from `AUTHOR_VOICE.md`. Existing rules stay unless explicitly removed.

## The compaction step

After `/voice` runs:
- Processed lines move from `.book-producer/memory.md` → `.book-producer/memory-archive.md`.
- The active log is truncated.
- The next session starts with a clean slate, but with the codified rules in `AUTHOR_VOICE.md`.

## Hard rules

- **Author approval is the source of truth.** No automatic learning.
- **AUTHOR_VOICE.md is sacred.** Never silently modified.
- **Memory is bounded.** ~200 lines max in active log; everything older is in archive.
