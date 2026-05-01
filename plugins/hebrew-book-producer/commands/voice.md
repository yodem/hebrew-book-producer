---
description: Update the author voice profile in CandleKeep interactively from recent corrections in .book-producer/memory.md. Compacts the rolling log into stable voice rules.
---

# /voice — update author voice fingerprint

Refresh the author voice profile in CandleKeep from accumulated feedback.

## Pre-flight

- `author_profile` IDs must exist in `book.yaml` (created by `/voice init`).
- `.book-producer/memory.md` should have content; if not — nothing to do, exit.

## What happens

1. Read the last 200 lines of `.book-producer/memory.md`.
2. Identify recurring patterns:
   - Phrases the author has rejected more than 3 times → candidate for "banned phrases" in the author profile.
   - Replacements the author has accepted more than 3 times → candidate for "preferred phrases."
   - Sentence-rhythm patterns (Burstiness, length distribution) of accepted prose → update reference paragraphs.
   - Register shifts the author has consistently rejected → tighten the register declaration.
3. Present each candidate change to the user one at a time. Format:

   ```
   PROPOSAL: add "בעולם המשתנה של היום" to BANNED PHRASES (rejected 5 times)
   Approve? [y/n/edit]
   ```

4. After each approval, push the change to CandleKeep immediately (see Output section). Never silently rewrite — the profile is sacred.
5. After all decisions: archive the processed lines from `.book-producer/memory.md` to `.book-producer/memory-archive.md` and truncate the active log.

## Output

1. Read the `author_profile.overview` ID from `book.yaml`.
2. For each approved change:
   - Update `.ctx/author-profile.md` locally (the in-session working copy).
   - Determine which CandleKeep page the change belongs to:
     - Banned phrase addition/removal → `author_profile.banned_phrases` ID
     - Preferred phrase addition/removal → `author_profile.preferred_phrases` ID
     - Register, rhythm, or persona update → `author_profile.overview` ID
   - Download the relevant CandleKeep item to a temp file:
     ```bash
     PAGE_ID=$(grep -A 10 '^author_profile:' book.yaml | grep '<page-key>:' \
       | sed -E 's/.*<page-key>:[[:space:]]*"?//; s/"?$//' | tr -d ' ')
     ck items get "${PAGE_ID}" --no-session > /tmp/profile-<page>.md
     ```
   - Apply the approved change to the temp file.
   - Push back immediately:
     ```bash
     ck items put "${PAGE_ID}" --file /tmp/profile-<page>.md --no-session
     ```
3. Always push `overview` last (it is the summary page and should reflect all changes).
4. Archive processed lines from `.book-producer/memory.md` to `.book-producer/memory-archive.md` and truncate the active log.
5. Tell the author in Hebrew: "עדכנתי X כללים בפרופיל הקולי ב-CandleKeep."

## Hard rules

- **Push to CandleKeep before reporting success.** If the push fails, report the failure and leave the change pending in `.book-producer/memory.md`.
- **Never bulk-add.** Author approval per item (unchanged from current behaviour).
- **Never delete an existing rule** without explicit author approval.
- **If `author_profile` IDs are missing** from `book.yaml` (profile was never created), tell the author: "לא נמצא פרופיל קולי ב-CandleKeep. הרץ /voice init כדי ליצור פרופיל." — do not create local files as fallback.
