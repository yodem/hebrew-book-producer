---
description: Bootstrap a new Hebrew book project — create book.yaml, AUTHOR_VOICE.md skeleton, .book-producer/ directory.
---

# /init — bootstrap project

Create a new book project in the current directory.

## What this command does

1. **Check for existing files.** If `book.yaml`, `AUTHOR_VOICE.md`, or `.book-producer/` already exist — ask the user before overwriting.
2. **Ask the author** these questions, one at a time:
   - שם הספר?
   - שם המחבר?
   - סוגה: philosophy / autobiography / religious / popular-science / mixed?
   - יעד באורך — כמה מילים? (alt: כמה גיליונות דפוס? `1 גיליון = ~4,000 מילים`)
   - סגנון ציטוט: chicago-author-date / apa / mixed?
   - ניקוד? (true for poetry/religious, false otherwise)
   - דד-ליין?
3. **Create `book.yaml`:**

   ```yaml
   title: "..."
   author: "..."
   genre: philosophy        # philosophy | autobiography | religious | popular-science | mixed
   target_words: 60000
   citation_style: chicago-author-date
   niqqud: false
   deadline: 2026-12-31
   created: 2026-04-29
   author_profile:          # CandleKeep item IDs — populated by voice-miner; empty = no profile yet
     overview: ""
     banned_phrases: ""
     preferred_phrases: ""
     reference_paragraphs: ""
     voice_fingerprint: ""
     chapter_patterns: ""
     source_style: ""
     register_examples: ""
   ```

4. **Create `AUTHOR_VOICE.md` skeleton** — see template in `skills/voice-preserver/SKILL.md`. Pre-fill the headings; the author fills in the content.

5. **Create `.book-producer/` directory** with:
   - `state.json` — empty `{ "chapters": [], "last_update": "<now>" }`
   - `memory.md` — empty file with header `# Memory — author corrections`
   - `snapshots/` — empty directory

6. **Create `.gitignore` entries** if not present:
   ```
   .book-producer/snapshots/
   .book-producer/memory.md
   .book-producer/state.json
   .ctx/
   ```

7. **Verify CandleKeep references are cached.** The plugin's `SessionStart` hook should already have populated `.ctx/`. If not, fall back to `bash ${CLAUDE_PLUGIN_ROOT}/scripts/load-candlekeep-guide.sh`.

8. **Final report** — summary of files created, next-action recommendation (`run /lector <manuscript-file>` once the author has draft text).
