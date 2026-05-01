---
name: voice-preserver
description: Read AUTHOR_VOICE.md at session start and enforce the author's idiolect. Checks proposed edits against banned-phrase, preferred-phrase, register, and persona rules. Used by linguistic-editor and proofreader before committing any change. Voice ALWAYS wins over a "more correct" rephrasing.
user-invocable: false
---

# voice-preserver — never lose the author

## Knowledge source

The five-register taxonomy (high / academic / journalistic / everyday / colloquial), the per-register vocabulary lists, and the register-mismatch tells live in the **CandleKeep book "Hebrew Linguistic Reference"**, chapter `hebrew-author-register`. Read at activation:

```bash
ck items read <hebrew-linguistic-reference-id> --chapter hebrew-author-register
```

Source on GitHub: [yodem/hebrew-linguistics-data](https://github.com/yodem/hebrew-linguistics-data). Use the chapter to classify the chapter's actual register before deciding whether a proposed edit shifts register; do not classify by intuition alone.

## When to invoke

- Linguistic-editor is about to apply an `Edit` call.
- Proofreader is about to apply an `Edit` call.
- Production-manager is about to merge a sub-agent's output.
- Before any chapter-level rewrite.

## The contract

The author hired this plugin to clean their Hebrew, not to make it generic. **Voice always wins.** A grammatically-perfect sentence that does not sound like the author is wrong.

## AUTHOR_VOICE.md schema

The file is created by `/init` with skeleton; the author fills it in. Sections:

```markdown
# AUTHOR_VOICE.md

## Persona (פרסונה)
One paragraph: who is the narrator? what is their tone? what do they refuse to be?

## Register (משלב)
- Default: literary-modern / academic / colloquial-modern / classical
- Switches: when do you switch register? (e.g., "academic for arguments, conversational for personal anecdotes")

## Preferred phrases (ביטויים מועדפים)
- ...
- ...

## Banned phrases (ביטויים אסורים)
- ...
- ...

## Sentence rhythm
- I write in: long, layered sentences / short and punchy / mixed
- I am suspicious of: ...

## Reference paragraphs
Five paragraphs from my prior work that I want to be measured against. The plugin never deviates from this rhythm without flagging me first.

### Paragraph 1
[paste]

### Paragraph 2
[paste]

(...up to 5 or 10)
```

## What the skill does

1. **Load** `AUTHOR_VOICE.md` at session start.
2. **Index** the banned and preferred phrases.
3. **Before each Edit:** check the proposed new text:
   - Does it use a banned phrase? → BLOCK the edit; ask for a different phrasing.
   - Does it remove a preferred phrase? → WARN; ask for confirmation.
   - Does it shift register more than ±1 step from the chapter's declared register? → WARN.
4. **Sentence-rhythm fingerprint:** compute Burstiness ratio of `AUTHOR_VOICE.md` reference paragraphs. The chapter being edited should land within ±20% of this ratio.

## How to use this skill from another agent

Inside `linguistic-editor` or `proofreader`, before the first `Edit`:

```
Read AUTHOR_VOICE.md (if exists).
For every Edit you are about to make:
  - Check the new_string against the banned-phrases list.
  - Check the new_string against the preferred-phrases list (don't drop them).
  - Compute the rhythm delta against the reference paragraphs.
If any check fails: do not apply the Edit. Report the conflict. Ask the user.
```

## What this skill does NOT do

- It does NOT generate a voice fingerprint from scratch. The author writes `AUTHOR_VOICE.md`; the skill reads it.
- It does NOT auto-correct edits. It blocks or warns; humans decide.
- It does NOT learn from `.book-producer/memory.md` directly — that is a separate periodic process triggered by `/voice` command.

## When AUTHOR_VOICE.md is missing

If the file does not exist, do not block any edit. Instead, log a single warning: *"`AUTHOR_VOICE.md` not found. Voice protection disabled. Run `/voice` to bootstrap."* Continue with edits.

## Hard rules

- Voice trumps correctness.
- The skill is reactive, not generative.
- Never modify `AUTHOR_VOICE.md` from this skill — only the `/voice` command can.
