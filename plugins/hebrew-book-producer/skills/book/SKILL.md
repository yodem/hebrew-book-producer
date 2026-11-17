---
name: book
description: "One entry point for the Hebrew book-production pipeline, run one stage at a time. Use when the author wants to bootstrap a book project or start from a plain request, write a chapter from a brief, get a lector appraisal of a manuscript (קריאת לקטור), run the literary and linguistic edit, proofread (הגהה), apply a reviewed Word file back into the chapters, prepare a typesetting brief for InDesign or LaTeX, run the whole pipeline with checkpoints, manage the author's thesis notebook, or see the plugin help."
user-invocable: true
argument-hint: "<stage> [args]"
metadata: {author: "Yotam Fromm", version: "0.10.0"}
---

# Hebrew Book Producer: the book pipeline

This skill is a router. Pick one stage, read its file, and follow it. Never load more than one stage file per run.

## Phases

| Phase | When to use | File |
|---|---|---|
| `start` | Single entry point: auto-bootstrap the project, then dispatch an action (proofread, edit, typeset, lector, write, init, ship): `<action> [target]` | `phases/start.md` |
| `init` | Bootstrap a new Hebrew book project: book.yaml, CandleKeep author profile, .book-producer/ | `phases/init.md` |
| `lector` | Manuscript appraisal (קריאת לקטור): parallel readers plus a synthesizer, writes LECTOR_REPORT.md: `<manuscript-file-or-folder> [--no-split] [--resume]` | `phases/lector.md` |
| `thesis` | The author's CandleKeep thesis notebook: append an idea, show it, or refresh it: `[append\|show\|refresh] [text...]` | `phases/thesis.md` |
| `draft` | Draft one chapter from its brief with the book-writer agent: `<chapter-id> [--new]` | `phases/draft.md` |
| `edit` | Literary then linguistic edit of the manuscript: `[literary\|linguistic\|all] [chapter-id] [--no-split]` | `phases/edit.md` |
| `proof` | Proofreading (הגהה), pass 1 or 2 detected from state, parallel per chunk: `[chapter-id]` | `phases/proof.md` |
| `apply` | Round-trip a reviewed .docx with accepted and rejected tracked changes back into the chapter markdown: `[chapter-id] [--accept-all]` | `phases/apply.md` |
| `typeset` | Generate TYPESETTING_BRIEF.md for hand-off to InDesign or LaTeX (no PDF) | `phases/typeset.md` |
| `ship` | Run the full pipeline end to end with approval gates: `<manuscript-file>` | `phases/ship.md` |
| `help` | Show what the plugin does and how to use it | `phases/help.md` |

## How to run

1. The first word of the arguments is the stage. Everything after it is the stage's arguments.
2. Check in this order. Arguments that are more than one bare word (a sentence or request such as "תוכל להגיה את הספר שלי?" or "can you proofread my book") have no stage word: infer the stage from the request and run `start` with that action. If two stages fit, ask the author which one. Do not guess. No arguments at all: run `help`.
3. Only when the arguments are a single bare word, with no sentence around it, and that word is not in the table: print the table and stop. Never apply this rule to a sentence.
4. Read exactly one file, `${CLAUDE_SKILL_DIR}/phases/<phase>.md`, and follow it as if it were this skill's body. The paths inside it that start with `${CLAUDE_SKILL_DIR}` or `${CLAUDE_PLUGIN_ROOT}` are already correct.

## Natural-language requests

Most authors will not remember stage names. A freeform Hebrew or English request that matches one of these runs the stage at once, without asking which one was meant (the bootstrap inside `start` asks at most one Hebrew confirmation). A chapter ID implied by the request ("פרק 3", "chapter 4") is passed on as the target.

| The author says | Run |
|---|---|
| תוכל להגיה, תעבור על הספר, proofread | `start proofread` |
| תוכל לערוך, עריכה ספרותית או לשונית, edit my book | `start edit` |
| תעמיד, תכין לדפוס, typeset, print-ready | `start typeset` |
| תקרא, לקטור, חוות דעת, appraise | `start lector` |
| תכתוב לי פרק, draft chapter, write me chapter X | `start write` |
| ספר חדש, new book, start a project | `start init` |
| ship it, run the full pipeline | `start ship` |

If the author types a stage directly (`proof ch3`), honour it and do not re-route through `start`. If ambiguous, ask one Hebrew clarification.

## Reference files

The skills that agents used to invoke by name are plain files now, read by path: `${CLAUDE_PLUGIN_ROOT}/references/<name>/README.md` for `book-bootstrap`, `candlekeep-writers-guide`, `changes-schema`, `cite-master`, `hebrew-connectives`, `hebrew-typography`, `niqqud-pass` and `review-style`. Stage files and agents name the ones they need.
