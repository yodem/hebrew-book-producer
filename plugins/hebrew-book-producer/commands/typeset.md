---
description: Generate a typesetting brief (TYPESETTING_BRIEF.md) for hand-off to InDesign or LaTeX. Does NOT render PDF.
---

# /typeset — typesetting brief

Run the **typesetting-agent**.

## Pre-flight

- All chapters must be at stage `typeset` (i.e. proofread pass 1 complete).
- If any chapter is still at `linguistic` or earlier — refuse; tell the user to finish `/proof` first.

## Gate

Production-manager invokes Metaswarm `$design-review-gate` before the typesetting agent runs.

## What happens

The typesetting-agent reads:

- `book.yaml` — for trim size, niqqud, genre.
- `skills/hebrew-typography/references/fonts.md` — for font selection.
- `skills/hebrew-typography/references/layout-rules.md` — for margins, headers, chapter breaks.

…and produces `TYPESETTING_BRIEF.md` in the project root.

## Output

- `TYPESETTING_BRIEF.md` — the specification.
- `TYPESETTING_NOTES.md` — open questions, author-facing decisions.
- State update: every chapter goes to `proofread-2-pending`.

## Report

- Trim size chosen.
- Body font + size.
- Total expected page count (rough estimate).
- Total in printing sheets (גיליון דפוס).
- Next action: `/proof` for pass 2 once the human typesetter has produced an actual proof.
