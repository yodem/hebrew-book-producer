# Workflow — Full Production Pipeline

The end-to-end flow that `/ship` orchestrates. Used by production-manager and documented here for reference.

## Pipeline diagram

```
┌─────────────────┐
│   manuscript    │  (author's draft)
│      .md        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   /lector       │  agent: lector
│  read-only      │  output: LECTOR_REPORT.md
└────────┬────────┘
         │   ⚡ user reviews report
         │   ⚡ author rewrites if "go with major revisions"
         ▼
┌─────────────────┐  agent: literary-editor (opus)
│   literary      │  reads: writers-guide Ch. 4, 5, 8, 9, 11
│     edit        │  output: manuscript edited in place
│                 │  + LITERARY_NOTES.md
└────────┬────────┘
         │   metaswarm: $plan-review-gate before this stage
         ▼
┌─────────────────┐  agent: linguistic-editor (sonnet)
│  linguistic     │  uses: review-style, voice-preserver,
│      edit       │        connectives, cite-master
│                 │  reads: AUTHOR_VOICE.md, .book-producer/memory.md
│                 │  output: manuscript edited in place
│                 │  + LINGUISTIC_NOTES.md
└────────┬────────┘
         │   ⚡ user approval checkpoint
         ▼
┌─────────────────┐  agent: proofreader (sonnet)
│   proofread     │  4 levels: אות / מילה / משפט / רעיון
│     pass 1      │  + niqqud-pass (if niqqud:true)
│                 │  + hazal-citation (if religious source)
│                 │  output: manuscript edited
│                 │  + PROOF_NOTES.md
└────────┬────────┘
         │
         ▼
┌─────────────────┐  agent: typesetting-agent (sonnet)
│   typeset       │  uses: hebrew-typography skill
│     brief       │  output: TYPESETTING_BRIEF.md
│                 │  + TYPESETTING_NOTES.md
└────────┬────────┘
         │   metaswarm: $design-review-gate before this stage
         │   ⚡ user takes brief → InDesign / LaTeX → typeset proof
         ▼
┌─────────────────┐  agent: proofreader (sonnet)
│   proofread     │  pass 2: layout artefacts only
│     pass 2      │  output: manuscript final
└────────┬────────┘
         │
         ▼
   ✅  PRINT-READY
```

## State transitions per chapter

```
drafted → literary → linguistic → proofread-1 → typeset → proofread-2-pending → done
```

`production-manager` writes one of these stages to `.book-producer/state.json` for every chapter, after every agent completes. Never any other agent.

## User checkpoints

The pipeline pauses for explicit user approval at:

1. After `/lector` — verdict review.
2. After `/edit` — restructure approval.
3. After `/proof` pass 1 — final-content approval.
4. After `/typeset` — design approval.
5. After `/proof` pass 2 — release approval.

Each checkpoint is a yes / no / discuss prompt. Never auto-proceed.

## Resumption

If a session ends mid-pipeline, `/ship` reads `.book-producer/state.json` on the next invocation and resumes from the chapter's current stage. No lost work.

## Estimated duration (heuristic)

For a 60,000-word non-fiction book (~3 sheets):

| Stage | Wall-clock |
|---|---|
| /lector | 5–10 min |
| /edit (literary + linguistic) | 30–60 min per chapter, x N chapters |
| /proof pass 1 | 10–15 min per chapter |
| /typeset | 5 min |
| /proof pass 2 | 5 min per chapter (after human typesetting) |

These are AI-execution times. Author review time is much longer and is not included.
