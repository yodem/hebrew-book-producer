# ראיון קול — Voice Interview

A structured 10-question Hebrew conversational interview used by the **light path** of `/init-voice` — when the author has no `past-books/` and the manuscript itself is incomplete or in early drafts.

The voice-miner agent runs through the questions one at a time, in Hebrew, in conversational tone. Each answer feeds a section of `AUTHOR_VOICE.md` and the qualitative side of `.book-producer/profile.json`.

## Rules for the agent

- **Hebrew, one question at a time.** Wait for an answer before the next.
- **Don't paraphrase the author back.** Quote them verbatim into `AUTHOR_VOICE.md`.
- **No follow-ups longer than one sentence.** If an answer is unclear, ask a single clarifying sentence and move on.
- **Save partial answers.** If the author stops mid-interview, write what you have so far. They can resume later.
- **Show, don't summarize.** When the author hands a banned phrase, store it verbatim — never reword it into "this kind of phrase."

## The 10 questions

### 1. הפרסונה
> "במשפט אחד, איך היית מגדיר את המספר של הספר הזה — מי הוא, ומול איזה קורא הוא מדבר?"

→ Stored under `## Persona` in AUTHOR_VOICE.md.

### 2. המשלב
> "באיזה משלב אתה כותב — אקדמי, עיתונאי, ספרותי-גבוה, יומיומי, או משהו מעורב? אם מעורב, מה היחס?"

→ Stored under `## Register`. The agent uses the chapter `hebrew-author-register` (CandleKeep) to classify the answer into the five-tier taxonomy.

### 3. ביטויים מועדפים
> "ספר לי שלושה ביטויים, מילים או צירופים שאתה אוהב להשתמש בהם — שלך מובהקים. אל תתאמץ — תכתוב את הראשונים שעולים בראש."

→ Stored under `## Preferred phrases`. Verbatim list.

### 4. ביטויים אסורים
> "ספר לי שלושה ביטויים שאתה לא תכתוב לעולם — שיעצבנו אותך לראות בטיוטה."

→ Stored under `## Banned phrases`. Verbatim. These join the global anti-AI markers list as project-specific overrides.

### 5. הקצב
> "אתה כותב במשפטים קצרים וחדים, ארוכים ומשתרגים, או מערבב? אם מערבב — מתי ארוך ומתי קצר?"

→ Stored under `## Sentence rhythm`. Used to set the burstiness target band.

### 6. גוף ראשון
> "האם אתה משתמש ב'אני' בספר הזה? אם כן — באילו רגעים זה מתאים, ובאילו זה זר לך?"

→ Stored under `## First person`. Calibrates the firstPersonFrequency expectation.

### 7. ציטוטים
> "איך אתה אוהב להציג ציטוטים — בתוך הפסקה, בבלוק נפרד, עם או בלי שם המקור בגוף הטקסט?"

→ Stored under `## Citations`. Calibrates the cite-master skill's per-project preference.

### 8. הפתיח
> "תן לי דוגמה לפתיח של פסקה שאתה היית כותב — איזושהי פסקה אופיינית. עדיף משהו אמיתי מהטיוטה הנוכחית, אבל גם משהו ממה שאתה זוכר זה בסדר."

→ Stored under `## Reference paragraphs`. The agent later parses this to compute initial fingerprint metrics for the light path.

### 9. הסיום
> "ואיך פסקה אצלך נסגרת? בעובדה? בשאלה? בדימוי? בציטוט?"

→ Stored under `## Reference paragraphs` (closing-move section).

### 10. הסכנה
> "אם אני 'אתקן' לך משהו ואטעה, מה הוא יהיה? איזו טעות הכי תכאיב לך לראות בטיוטה ערוכה?"

→ Stored under `## What never to touch`. This is the highest-priority guardrail; the linguistic-editor and proofreader read it first.

## After the interview

The voice-miner:
1. Concatenates all 10 answers as draft `AUTHOR_VOICE.md`.
2. Runs the chapter-9 (sample) parser of `extract-voice-fingerprint.py` against the reference paragraphs from Q8 to seed the computational fingerprint with whatever data exists.
3. Writes both `AUTHOR_VOICE.md` and `.book-producer/profile.json`.
4. Reports a 5-line summary back to the author: persona, register, banned-phrase count, preferred-phrase count, next action (run `/lector` once a chapter is drafted).
