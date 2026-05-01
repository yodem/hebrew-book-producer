---
description: Single entry-point that auto-bootstraps a book project (book.yaml, .book-producer/, AUTHOR_VOICE.md via express-voice) and dispatches to the requested action — proofread / edit / typeset / lector / write / init / ship. Used by the natural-language router in CLAUDE.md so the user never has to remember slash commands.
argument-hint: <action> [target]
---

# /start — auto-bootstrap and dispatch

The single entry-point command. Hides slash commands from the user. Always begins with the `book-bootstrap` skill, then dispatches.

## Usage

```
/start proofread          # bootstrap, then /proof on all chapters
/start proofread ch3      # bootstrap, then /proof ch3
/start edit               # bootstrap, then /edit
/start edit ch3           # bootstrap, then /edit ch3
/start lector             # bootstrap, then /lector <manuscript>
/start typeset            # bootstrap, then /typeset
/start write              # bootstrap, then /draft (interactive — picks chapter or runs --new)
/start write ch3          # bootstrap, then /draft ch3
/start init               # bootstrap only — no terminal action
/start ship               # bootstrap, then /ship
```

If `<action>` is omitted, ask one Hebrew question:

> "מה לעשות? (1) הגהה (2) עריכה (3) עימוד (4) לקטור (5) כתיבה (6) צילום פרצוף — הצג מצב"

Map answer 1→proofread, 2→edit, 3→typeset, 4→lector, 5→write, 6→init.

## Pre-flight

None. `book-bootstrap` is the pre-flight; everything else is its responsibility.

## Flow

```
1. Invoke skills/book-bootstrap → returns { status, scaffolded, manuscriptFiles, genre, ... }
2. If status != "ok": surface the error in Hebrew and abort.
3. Dispatch:
   proofread → for each chapter (or specified one): /proof <chapter-id>
   edit      → /edit <chapter-id> for each chapter
   typeset   → /typeset (operates on the whole project)
   lector    → /lector <first manuscript file>
   write     → /draft <chapter-id> if a brief exists, else /draft <id> --new
   init      → return success — bootstrap was the whole job
   ship      → /ship <first manuscript file>
4. Aggregate the dispatched action's report.
5. Print a single Hebrew summary line at the end:
   "<action> הושלם. <key-fact>. הצעה הבאה: <next-action>."
```

## What gets shown to the user

For a freshly-onboarded user running `/start proofread`:

```
[bootstrap]
זיהיתי 3 פרקים, סוגה: פילוסופיה, ניקוד: כבוי, יעד: 45,000 מילה. נכון? (כן / שנה / ביטול)
> כן

[express-voice]
1/3 — במשפט אחד, מי המספר של הספר הזה ולמי הוא מדבר?
> ...
2/3 — באיזה משלב? אקדמי, ספרותי, יומיומי, או מעורב?
> ...
3/3 — ביטוי אחד שאתה לא תכתוב לעולם?
> ...

[proof]
פרק 1: 23 תיקונים (אות 14 / מילה 6 / משפט 2 / רעיון 1)
פרק 2: 17 תיקונים
פרק 3: 9 תיקונים

[summary]
הגהה הושלמה — 49 תיקונים בסה"כ. הצעה הבאה: עברו על PROOF_NOTES.md ואז /start typeset.
```

Total user inputs: **1 sentence (the original request) + 1 confirmation + 3 voice answers**.

## Hard rules

- **Bootstrap always runs first.** No skipping, even if the user says "אני יודע מה אני עושה". Bootstrap is idempotent — if the project is already scaffolded, it costs ~1s and silently confirms.
- **One Hebrew confirmation only.** The bootstrap step asks; this command does not double-ask.
- **Failures are surfaced in Hebrew.** No raw stack traces, no English error codes for the user.
- **Don't replace the existing slash commands.** `/proof`, `/edit`, etc. remain available for power users who want to skip bootstrap.

## When NOT to use

- The user explicitly requested a slash command directly (e.g., they typed `/proof ch3`). Honour that — don't redirect into `/start`.
- The user is debugging a single sub-skill — they want the slash, not the wrapper.
