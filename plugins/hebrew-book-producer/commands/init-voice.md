---
description: Build the author's voice/style fingerprint. Hybrid auto-detect — runs the full computational fingerprint over past-books/ if any are present, otherwise runs a 10-question Hebrew interview + sample of the in-progress manuscript. Produces .book-producer/profile.json + AUTHOR_VOICE.md (or AUTHOR_VOICE.draft.md if one already exists).
argument-hint: (no arguments — auto-detects)
---

# /init-voice — bootstrap or refresh the author's voice fingerprint

Hand off to the **voice-miner** agent.

## Pre-flight

- `book.yaml` must exist. If not, ask the user to run `/init` first.
- The shared CandleKeep book *Hebrew Linguistic Reference* must be cached at `.ctx/hebrew-linguistic-reference.md`. The `load-candlekeep-guide.sh` script handles this; voice-miner re-runs it if missing.

## Auto-detect

The voice-miner agent counts files in `past-books/`:

- `past-books/*.{pdf,docx,md,txt}` exists with ≥1 file → **heavy path** (full computational fingerprint vs the shared baseline).
- otherwise → **light path** (3-chapter manuscript sample + 10-question Hebrew interview).

## What this produces

| File | Created by | Editable by hand |
|---|---|---|
| `.book-producer/profile.json` | voice-miner | no — re-run `/init-voice` to refresh |
| `AUTHOR_VOICE.md` (if missing) | voice-miner | yes |
| `AUTHOR_VOICE.draft.md` (if `AUTHOR_VOICE.md` already exists) | voice-miner | yes — author manually merges into the canonical file |

## When to re-run

- After completing 1–2 chapters of a draft (light → heavy: drop the chapters into `past-books/` and re-run).
- After significant rewrites that shift voice.
- When the linguistic-editor flags a register drift the author wants to relearn.

## Report

5-line summary (in Hebrew):

1. Path used (heavy / light) + what was sampled.
2. Detected register.
3. Banned-phrase count + preferred-phrase count.
4. Burstiness score (and a one-word interpretation: flat / human / very-varied).
5. Next action — `/lector <file>` if a draft is ready, otherwise a writing prompt.
