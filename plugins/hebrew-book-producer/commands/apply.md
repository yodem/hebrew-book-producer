---
description: Round-trip a reviewed .docx (with tracked-change accept/reject decisions) back into the canonical chapter markdown. Pass a chapter ID, or no argument to apply all chapters with reviewed docx files.
argument-hint: [chapter-id] [--accept-all]
---

# /apply — round-trip reviewed docx into canonical markdown

## Pre-flight

1. Verify `book.yaml` exists.
2. Verify `chapters/` directory exists.
3. Determine the latest run-id: `ls -1 .book-producer/runs/ | sort | tail -1`. Save as `RUN_ID`.

## Argument handling

- No argument → apply every chapter that has a reviewed docx (`chapters/<id>.reviewed.docx`).
- `<chapter-id>` (e.g. `ch03`) → apply only that chapter.
- `--accept-all` (with chapter-id) → bypass docx round-trip; accept every change in the chapter's `changes.json` directly.

## For each target chapter

### Step A — locate the reviewed docx

Look for `chapters/<chapter>.reviewed.docx`. If absent, look for `chapters/<chapter>.suggestions.docx` whose mtime is newer than the file production-manager originally wrote (= the author saved over it). If neither found:
- Print Hebrew error: "לא נמצא קובץ סקירה עבור פרק <chapter>. צרי קובץ <chapter>.reviewed.docx ב-chapters/ ונסי שוב."
- Skip this chapter and continue with the next.

### Step B — flatten via pandoc

```bash
mkdir -p .book-producer/round-trip
pandoc --track-changes=accept "chapters/<chapter>.reviewed.docx" \
  -o ".book-producer/round-trip/<chapter>.reviewed.md"
```

### Step C — locate the original changes.json

```bash
CHANGES_JSON=$(ls -1 .book-producer/runs/${RUN_ID}/*/changes.json | head -1)
```

If multiple agents touched this chapter (literary + linguistic + proofreader), there are multiple changes.json files. Apply them in stage order: literary → linguistic → proofreader. Re-run Steps D and E for each.

### Step D — run the applier

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/apply_reviewed_docx.py \
  --reviewed-md ".book-producer/round-trip/<chapter>.reviewed.md" \
  --changes "${CHANGES_JSON}" \
  --canonical "chapters/<chapter>.md" \
  --decisions-out ".book-producer/runs/${RUN_ID}/<agent>/apply-decisions.<chapter>.json"
```

### Step E — print Hebrew summary

Read the decisions JSON. Print a 5-line Hebrew summary:

```
פרק: <chapter>
שינויים מוצעים: <total>
אישרת: <accepted count>
דחית: <rejected count>
שינית: <modified count>
```

Then add a one-line follow-up:

> "הקובץ הסופי: chapters/<chapter>.md. רוצה לראות diff מול הגרסה הקודמת? (git diff HEAD~1 chapters/<chapter>.md)"

## --accept-all path

If invoked as `/apply <chapter> --accept-all`:

```bash
python3 -c "
import json, sys
sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/scripts')
data = json.load(open('${CHANGES_JSON}'))
text = open('chapters/<chapter>.md').read()
accepted = []
for c in data['changes']:
    if c.get('before') and c['before'] in text:
        text = text.replace(c['before'], c.get('after', ''), 1)
        accepted.append(c['change_id'])
open('chapters/<chapter>.md', 'w').write(text)
print(f'accepted-all: {len(accepted)} changes')
"
```

Then write a decisions log with all change_ids in `accepted`. Print Hebrew summary as above.

## Hard rules

- **Markdown is canonical.** `chapters/<chapter>.md` is the source of truth. Docx is a review surface only.
- **Never modify changes.json.** It records what the agent proposed; the apply step records what the author decided in a separate decisions file.
- **Never write to `.book-producer/state.json`** — that's production-manager's job. After apply, the user should run `/edit` (or whichever next stage) to advance state.
- If pandoc errors on the reviewed docx, surface the error and stop. Do NOT touch the canonical markdown.
