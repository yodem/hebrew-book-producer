---
name: express-voice
description: Three-question Hebrew interview that produces a minimum-viable AUTHOR_VOICE.md when the author hasn't run /init-voice yet. Invoked by book-bootstrap only, when AUTHOR_VOICE.md is missing. Do NOT use when AUTHOR_VOICE.md already exists — book-bootstrap guards this gate.
user-invocable: false
---

# express-voice — minimum-viable voice fingerprint

## Why this exists

The full `/init-voice` flow asks 10 questions and runs a computational fingerprint over `past-books/`. That's the right depth for an author who's settling in. But for a user who just typed *"תוכל להגיה את הספר שלי?"* and wants results, 10 questions is a wall.

This skill collects the **three highest-leverage** voice signals in under a minute. The proofreader and linguistic-editor produce useful output even from this sparse input — what they really can't do is operate with `AUTHOR_VOICE.md` *missing*, which would disable voice-preserver entirely.

## When to invoke

- `book-bootstrap` step 5, when `AUTHOR_VOICE.md` is missing.
- The user explicitly says *"רוצה לדלג, רק קצר"* during a voice flow.

## The three questions

Ask one at a time, in Hebrew, conversational tone. Wait for each answer before the next.

### Q1 — Persona
> "במשפט אחד, מי המספר של הספר הזה ולמי הוא מדבר?"

→ Stored verbatim under `## Persona`.

### Q2 — Register
> "באיזה משלב? אקדמי, ספרותי, יומיומי, או מעורב?"

→ Stored under `## Register`. Map the answer to the five-tier taxonomy from `hebrew-linguistic-reference.md` chapter `hebrew-author-register` (high / academic / journalistic / everyday / colloquial). Multi-word answers → `mixed` with the dominant first.

### Q3 — One banned phrase
> "ביטוי אחד שאתה לא תכתוב לעולם, שמעצבן אותך לראות בטיוטה?"

→ Verbatim under `## Banned phrases`. This single entry gates the linguistic-editor immediately; many authors find that one explicit ban catches 30% of AI-flat fixes on its own.

## Output — `AUTHOR_VOICE.md`

Template lives at `references/templates/author-voice-skeleton.md` — load when generating output.

## Output — `.book-producer/profile.json`

If a manuscript exists in the current project (book-bootstrap detected at least one file), **also** run the extractor on a sample to seed computational fields:

```bash
python3 $CLAUDE_PLUGIN_ROOT/scripts/extract-voice-fingerprint.py \
  --input <one of the manuscript files> \
  --baseline .ctx/hebrew-linguistic-reference.md \
  --output .book-producer/profile.json
```

This gives downstream agents real burstiness, sentence-length, and TTR numbers — even when the author hasn't done the heavy interview. If extraction fails or no manuscript exists, write a stub using the template at `references/templates/profile-stub.json`.

## Hard rules

- **Three questions, no more.** If the user volunteers extra info ("גם, אני שונא להשתמש ב X"), capture it as additional banned phrases — but never ask a fourth scripted question.
- **Verbatim storage.** Don't paraphrase the author's own words. Their phrasing IS the voice.
- **Hebrew throughout.** Both questions and stored answers.
- **Don't overwrite.** If `AUTHOR_VOICE.md` already exists when this skill runs, abort and tell the caller — `book-bootstrap` should have skipped this skill.

## Reporting back

One-line return to the caller:
> "הקול נשמר. {persona-1-word}, משלב {register}, ביטוי אסור אחד."
