---
description: Run the literary + linguistic edit pipeline on the manuscript. Production-manager schedules and merges.
argument-hint: [chapter-id]
---

# /edit — literary + linguistic edit

Run the literary-editor and then the linguistic-editor on the manuscript.

## Pre-flight

- `book.yaml` must exist.
- `LECTOR_REPORT.md` must exist with verdict `Go` or `Go with major revisions` (and revisions completed).
- If `LECTOR_REPORT.md` is missing — refuse; tell the user to `/lector` first.

## What happens

The `production-manager` agent runs the pipeline:

1. **literary-editor** runs first on the requested chapter (or all chapters if no argument given).
2. After literary-editor returns: production-manager updates `.book-producer/state.json`.
3. **linguistic-editor** runs second on the same chapters.
4. After linguistic-editor returns: state advances to `proofread-1` (proofreader's pre-typesetting pass).

## Argument

- No argument → all chapters at stage `drafted` get edited.
- A chapter ID (e.g. `ch04`) → only that chapter.

## Gates

Production-manager invokes Metaswarm `$plan-review-gate` before the literary-editor starts work, to ensure the planned restructuring is sound.

## Report

A single summary at the end:

- Chapters edited.
- Major restructuring decisions.
- Word count delta (target: −10% per Ch. 5 of writers-guide).
- Next action: `/proof` once linguistic-editor completes.
