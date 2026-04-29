---
description: Update AUTHOR_VOICE.md interactively from recent corrections in .book-producer/memory.md. Compacts the rolling log into stable voice rules.
---

# /voice — update author voice fingerprint

Refresh `AUTHOR_VOICE.md` from accumulated feedback.

## Pre-flight

- `AUTHOR_VOICE.md` must exist (created by `/init`).
- `.book-producer/memory.md` should have content; if not — nothing to do, exit.

## What happens

1. Read the last 200 lines of `.book-producer/memory.md`.
2. Identify recurring patterns:
   - Phrases the author has rejected more than 3 times → candidate for "banned phrases" in `AUTHOR_VOICE.md`.
   - Replacements the author has accepted more than 3 times → candidate for "preferred phrases."
   - Sentence-rhythm patterns (Burstiness, length distribution) of accepted prose → update reference paragraphs.
   - Register shifts the author has consistently rejected → tighten the register declaration.
3. Present each candidate change to the user one at a time. Format:

   ```
   PROPOSAL: add "בעולם המשתנה של היום" to BANNED PHRASES (rejected 5 times)
   Approve? [y/n/edit]
   ```

4. After each approval, append to `AUTHOR_VOICE.md`. Never silently rewrite — the file is sacred.
5. After all decisions: archive the processed lines from `.book-producer/memory.md` to `.book-producer/memory-archive.md` and truncate the active log.

## Output

- `AUTHOR_VOICE.md` updated with approved rules.
- `.book-producer/memory.md` truncated.
- `.book-producer/memory-archive.md` appended.
- Summary report to the user: "Added X banned phrases, Y preferred phrases, refined register."

## Hard rules

- **Author approval per item.** Never bulk-add.
- **Never delete** an existing rule from `AUTHOR_VOICE.md` without explicit approval.
- **Voice is the author's.** This command surfaces patterns, not opinions.
