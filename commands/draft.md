---
description: Draft a Hebrew book chapter. Reads chapters/<id>.brief.md (which the author writes — bullets, sources, the one non-negotiable beat) and produces chapters/<id>.draft.md plus chapters/<id>.decisions.md. Per-genre conventions (philosophy → dialectical, autobiography → scene-driven, religious → primary-source weave with Sefaria verification, popular-science → hooks-and-implications). Never generates from blank.
argument-hint: <chapter-id> [--new]
---

# /draft — book-writer for one chapter

Hand off to the **book-writer** agent.

## Pre-flight

- `book.yaml` must exist. If not → run `/start init` first.
- `AUTHOR_VOICE.md` must exist. If not → run `/init-voice` (or let `/start` handle it via express-voice).
- For the default form: `chapters/<id>.brief.md` must exist. The brief is the input; the agent expands it.

## Two forms

### `/draft <id>`

Standard. The author has already written `chapters/<id>.brief.md`. The agent reads the brief, drafts the chapter, writes `chapters/<id>.draft.md` and `chapters/<id>.decisions.md`.

### `/draft <id> --new`

Interactive. No brief exists yet. The agent walks the author through 5 Hebrew questions and writes `chapters/<id>.brief.md` first, then drafts.

The 5 questions (one at a time, conversational tone):

1. **תקציר במשפט אחד** — "תאר במשפט אחד מה הפרק הזה עושה בתוך הספר."
2. **3–5 סצנות / רעיונות עיקריים** — "מה הדברים הכי חשובים שצריכים להיכנס לפרק? תן לי 3–5 שורות."
3. **מקורות לציטוט (אם יש)** — "מקורות שאתה רוצה לצטט? תנ"ך, חז"ל, מאמרים, ספרים — שמות בלבד; אני מוודא בעצמי."
4. **הדבר היחיד שחייב להיכנס** — "אם הכול חוץ מדבר אחד נופל בסבב עריכה — מה הדבר שחייב להישאר?"
5. **יעד אורך** — "כמה מילים בערך? (ברירת מחדל: יחס לפי `book.yaml: target_words`.)"

The agent saves the answers as `chapters/<id>.brief.md`, then proceeds with the standard draft flow.

## Pass-through to book-writer

The `book-writer` agent is the workhorse. This command is a thin wrapper. See `agents/book-writer.md` for the full drafting process — outline → source verification → prose → 5-dimension anti-AI self-check → decisions log → 5-line Hebrew report.

## Output

- `chapters/<id>.draft.md` — the chapter draft. Never overwrites; produces `.draft.v2.md`, `.draft.v3.md`, … on re-runs.
- `chapters/<id>.decisions.md` — what scenes/sources/quotes were used, what was deferred, what required interpretation.

## Report

5-line Hebrew summary from book-writer:
1. Word count vs target.
2. Register classification.
3. Sources cited (verified vs `[UNVERIFIED]`).
4. Anti-AI score (out of 50, threshold 35).
5. One question for the author about anything ambiguous in the brief — or "אין שאלות — מוכן לעריכה ספרותית."

## Suggested next action

After `/draft <id>`, the typical flow is:

1. The author reads `chapters/<id>.draft.md` and the decisions log.
2. The author corrects what they want directly in the draft (or moves it to `chapters/<id>.md` once approved).
3. `/start edit <id>` for the literary + linguistic editorial pass.
4. `/start proofread <id>` for the proofreader.

## Hard rules

- **Brief is mandatory.** Refuse to draft without one. Use `--new` if needed.
- **One chapter per invocation.** No batch drafting.
- **Never overwrites a prior draft.** Versions accumulate; the author chooses which to promote.
