---
description: Proofreading pass. Runs proofreader pass 1 (pre-typesetting) or pass 2 (post-typesetting) automatically based on .book-producer/state.json.
argument-hint: [chapter-id]
---

# /proof — proofreading

Run the **proofreader** agent.

## Pre-flight

- `book.yaml` must exist.
- The chapter must be at stage `proofread-1` (after `/edit`) or `proofread-2-pending` (after `/typeset`).

## Pass detection

The proofreader detects which pass to run by reading `.book-producer/state.json`:

- Stage `proofread-1` → pass 1 (pre-typesetting). Catches typos, punctuation, hyphenation.
- Stage `proofread-2-pending` → pass 2 (post-typesetting). Catches layout artefacts, broken quotation marks, RTL/LTR drift.

## Conditional skills

- If `book.yaml` has `niqqud: true` → run the `niqqud-pass` skill as a separate sweep AFTER the main proofread (never during).
- If religious primary sources detected → verify each reference inline via `mcp__claude_ai_Sefaria__get_text`; tag `[UNVERIFIED]` on anything that fails to resolve.

## Output

- The manuscript modified in place (typos fixed).
- `PROOF_NOTES.md` updated with level-4 idea-flags (things the proofreader noticed but cannot auto-fix).
- State updated:
  - After pass 1 → `typeset` (next: `/typeset`).
  - After pass 2 → `done`.

## Report

Five-line summary:

- Pass run (1 or 2).
- Total fixes by level (אות / מילה / משפט / רעיון).
- Niqqud pass run? Citations verified?
- Next action.
