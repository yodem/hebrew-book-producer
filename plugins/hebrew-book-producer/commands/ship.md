---
description: Run the full pipeline end-to-end with checkpoints. Lector → edit → proof (1) → typeset → proof (2). Pauses for user approval at each gate.
argument-hint: <manuscript-file>
---

# /ship — full pipeline

Take a manuscript through the entire production pipeline.

## Pipeline

```
/lector <file>            ← read-only appraisal; produces LECTOR_REPORT.md
   ↓
[CHECKPOINT — user approval required]
   ↓
/edit                     ← literary + linguistic edits
   ↓
[CHECKPOINT — user approval required]
   ↓
/proof                    ← proofreading pass 1
   ↓
[CHECKPOINT — user approval required]
   ↓
/typeset                  ← typesetting brief
   ↓
[USER goes to InDesign / LaTeX, produces a typeset proof]
   ↓
/proof                    ← proofreading pass 2 (post-typesetting)
   ↓
DONE
```

## Why the checkpoints

Each transition is a major editorial decision. The author confirms before proceeding. **Never auto-proceed past a checkpoint** — the cost of wrong-direction editing is high (Ch. 5 of writers-guide).

## What this command does

Production-manager orchestrates the entire pipeline. After each agent completes:

1. Update `.book-producer/state.json`.
2. Summarise outcome to the user.
3. Ask: "Proceed to next stage? (yes / no / discuss)"
4. If yes → continue. If no → pause and wait. If discuss → enter Q&A mode.

## Resume behaviour

If `/ship` is interrupted (session ends, error), it resumes from `.book-producer/state.json` on the next invocation. The author does not have to start over.
