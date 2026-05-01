# CandleKeep Author Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store the author's voice profile as a collection of CandleKeep items (one per "page"), pulled into `.ctx/` at session start, and auto-synced on every `/voice` correction — making the profile portable across all book projects.

**Architecture:** CandleKeep is the source of truth. `book.yaml` holds IDs for each profile page. The `SessionStart` hook pulls `overview` into `.ctx/author-profile.md`. Agents load deeper pages on demand. `voice-miner` creates/updates CandleKeep items and writes IDs back to `book.yaml`. `/voice` auto-pushes corrections immediately.

**Tech Stack:** Bash (hooks + scripts), `ck` CLI (CandleKeep), YAML (`book.yaml`), Markdown (agent prompt files)

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `plugins/hebrew-book-producer/scripts/load-candlekeep-guide.sh` | Modify | Add author profile overview pull |
| `plugins/hebrew-book-producer/hooks/session-start.sh` | No change | Already calls load-candlekeep-guide.sh |
| `plugins/hebrew-book-producer/commands/init.md` | Modify | Check for existing profile; skip skeleton if found; copy IDs to new book.yaml |
| `plugins/hebrew-book-producer/agents/voice-miner.md` | Modify | Create/update CandleKeep items; write IDs to book.yaml |
| `plugins/hebrew-book-producer/commands/voice.md` | Modify | Push updated overview + changed deep pages to CandleKeep after local update |
| `plugins/hebrew-book-producer/CLAUDE.md` | Modify | Rule #2: read `.ctx/author-profile.md` instead of `AUTHOR_VOICE.md` |
| `plugins/hebrew-book-producer/agents/book-writer.md` | Modify | Load `reference_paragraphs`, `preferred_phrases`, `chapter_patterns` from CandleKeep on demand |
| `plugins/hebrew-book-producer/agents/linguistic-editor.md` | Modify | Load `banned_phrases` from CandleKeep on demand |
| `plugins/hebrew-book-producer/agents/proofreader.md` | Modify | Load `banned_phrases` from CandleKeep on demand |
| `plugins/hebrew-book-producer/agents/lector.md` | Modify | Load `reference_paragraphs` from CandleKeep on demand |
| `plugins/hebrew-book-producer/agents/voice-miner.md` | Modify | Load `source_style` for cite-master integration |

---

## Task 1: Define the `author_profile` schema in book.yaml

**Files:**
- Modify: `plugins/hebrew-book-producer/commands/init.md`

- [ ] **Step 1: Read the current init.md**

```bash
cat plugins/hebrew-book-producer/commands/init.md
```

- [ ] **Step 2: Update step 3 in init.md** — add `author_profile` block to the `book.yaml` template shown in the file. Replace the existing `book.yaml` template block with:

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

- [ ] **Step 3: Verify the edit looks correct**

```bash
grep -A 12 "author_profile" plugins/hebrew-book-producer/commands/init.md
```

Expected: the block above appears in the template section.

- [ ] **Step 4: Commit**

```bash
git add plugins/hebrew-book-producer/commands/init.md
git commit -m "feat: add author_profile schema to book.yaml template"
```

---

## Task 2: Pull author profile overview in load-candlekeep-guide.sh

**Files:**
- Modify: `plugins/hebrew-book-producer/scripts/load-candlekeep-guide.sh`

- [ ] **Step 1: Read the current script**

```bash
cat plugins/hebrew-book-producer/scripts/load-candlekeep-guide.sh
```

- [ ] **Step 2: Add author profile section** — append the following block before the final `echo "Done..."` lines. Find the line `echo` just before `echo "Done. Cached references in: ${CTX_DIR}/"` and insert above it:

```bash
# ── Author voice profile (optional, per-project) ────────────
# Reads author_profile.overview from book.yaml and caches to .ctx/author-profile.md
if [ -f "${PROJECT_ROOT}/book.yaml" ]; then
  profile_overview_id=$(grep -A 10 '^author_profile:' "${PROJECT_ROOT}/book.yaml" \
    | grep -E '^\s+overview:' | head -1 \
    | sed -E 's/.*overview:[[:space:]]*//; s/[[:space:]]*#.*$//; s/^"//; s/"$//' | tr -d ' ')
  if [ -n "${profile_overview_id}" ] && [ "${profile_overview_id}" != '""' ]; then
    fetch_guide "${profile_overview_id}" "author-profile.md" "Author voice profile — overview"
  fi
fi
```

- [ ] **Step 3: Verify the function `fetch_guide` handles the new call correctly**

The function already handles missing IDs gracefully (writes a STUB). Confirm the new block appears correctly:

```bash
grep -A 8 "Author voice profile" plugins/hebrew-book-producer/scripts/load-candlekeep-guide.sh
```

- [ ] **Step 4: Manual smoke test** — create a temporary book.yaml with a known CandleKeep item ID and run the script:

```bash
# In a temp directory
mkdir /tmp/profile-test && cd /tmp/profile-test
cat > book.yaml <<'EOF'
title: "Test"
author_profile:
  overview: "PASTE_A_REAL_CK_ITEM_ID_HERE"
EOF
CLAUDE_PROJECT_DIR=/tmp/profile-test bash /PATH/TO/plugins/hebrew-book-producer/scripts/load-candlekeep-guide.sh
cat .ctx/author-profile.md | head -5
```

Expected: `.ctx/author-profile.md` contains the CandleKeep item content (or STUB if ID is invalid).

- [ ] **Step 5: Commit**

```bash
git add plugins/hebrew-book-producer/scripts/load-candlekeep-guide.sh
git commit -m "feat: pull author profile overview into .ctx/author-profile.md at session start"
```

---

## Task 3: Update /init to handle existing vs. new author profiles

**Files:**
- Modify: `plugins/hebrew-book-producer/commands/init.md`

- [ ] **Step 1: Read the current init.md step 4** (the AUTHOR_VOICE.md skeleton step)

```bash
grep -n "AUTHOR_VOICE" plugins/hebrew-book-producer/commands/init.md
```

- [ ] **Step 2: Replace step 4** — change "Create AUTHOR_VOICE.md skeleton" to a conditional block. Find and replace the relevant section with:

```markdown
4. **Resolve author profile — existing or new:**

   a. Check if `book.yaml` already has a non-empty `author_profile.overview` ID:
      - If yes: fetch it with `ck items get <id> --no-session > .ctx/author-profile.md`. Skip the skeleton and skip the voice interview. Tell the author (in Hebrew): "מצאתי פרופיל קולי קיים — נטענתי ממנו. אין צורך למלא AUTHOR_VOICE.md."
      - If no: create a blank `author_profile` block in `book.yaml` (all values empty string). Tell the author: "לא מצאתי פרופיל קולי קיים. לאחר הגדרת הפרויקט, הרץ /voice כדי לבנות את הפרופיל מהספרים שלך."

   b. **Never create a blank AUTHOR_VOICE.md skeleton.** The profile lives in CandleKeep, not in a local file.
```

- [ ] **Step 3: Add guidance for "same author, new project" workflow** — add a note after step 8 (the final report step):

```markdown
**Note — porting a profile to a new project:** If the author has an existing profile from another project, copy the `author_profile` block from the old `book.yaml` into the new one. The `SessionStart` hook will load it automatically next session.
```

- [ ] **Step 4: Verify**

```bash
grep -n "author_profile\|AUTHOR_VOICE\|profile" plugins/hebrew-book-producer/commands/init.md
```

Expected: no references to creating a blank AUTHOR_VOICE.md skeleton; `author_profile` conditional logic present.

- [ ] **Step 5: Commit**

```bash
git add plugins/hebrew-book-producer/commands/init.md
git commit -m "feat: /init checks CandleKeep author profile before creating skeleton"
```

---

## Task 4: Update voice-miner to write output to CandleKeep

**Files:**
- Modify: `plugins/hebrew-book-producer/agents/voice-miner.md`

- [ ] **Step 1: Read the current voice-miner output section**

```bash
grep -n "Save\|Write\|output\|AUTHOR_VOICE\|profile.json" plugins/hebrew-book-producer/agents/voice-miner.md
```

- [ ] **Step 2: Replace the output section in both heavy and light paths.** Find "Save the JSON and the markdown" and every reference to writing local files. Replace with this CandleKeep output procedure (add as a new section titled `## CandleKeep output procedure` before `## Reporting back to the author`):

```markdown
## CandleKeep output procedure

Run after either path completes. Always use `--no-session` on all `ck` commands.

### New author (no existing profile IDs in book.yaml)

Create one CandleKeep item per page:

```bash
# overview (required)
OVERVIEW_ID=$(ck items create "Author Profile — Overview — <Author Name>" \
  --description "Voice fingerprint overview: register, stance, banned/preferred phrases" \
  --no-session | grep -oE '[a-z0-9]{20,}' | tail -1)

BANNED_ID=$(ck items create "Author Profile — Banned Phrases — <Author Name>" \
  --description "Full banned phrase list with context and wrong/right examples" \
  --no-session | grep -oE '[a-z0-9]{20,}' | tail -1)

PREFERRED_ID=$(ck items create "Author Profile — Preferred Phrases — <Author Name>" \
  --description "Preferred collocations with example sentences" \
  --no-session | grep -oE '[a-z0-9]{20,}' | tail -1)

REFS_ID=$(ck items create "Author Profile — Reference Paragraphs — <Author Name>" \
  --description "20-30 verbatim representative passages" \
  --no-session | grep -oE '[a-z0-9]{20,}' | tail -1)

FP_ID=$(ck items create "Author Profile — Voice Fingerprint — <Author Name>" \
  --description "Statistical fingerprint: sentence length, burstiness, vocabulary richness" \
  --no-session | grep -oE '[a-z0-9]{20,}' | tail -1)

CH_ID=$(ck items create "Author Profile — Chapter Patterns — <Author Name>" \
  --description "How author opens/closes chapters and transitions between ideas" \
  --no-session | grep -oE '[a-z0-9]{20,}' | tail -1)

SRC_ID=$(ck items create "Author Profile — Source Style — <Author Name>" \
  --description "How author integrates Hazal citations, block quotes, inline references" \
  --no-session | grep -oE '[a-z0-9]{20,}' | tail -1)

REG_ID=$(ck items create "Author Profile — Register Examples — <Author Name>" \
  --description "Concrete examples of register shifts" \
  --no-session | grep -oE '[a-z0-9]{20,}' | tail -1)
```

Write content to temp files, then upload each:

```bash
# Write content to temp files (use the AUTHOR_VOICE.md schema for overview)
# Then upload:
ck items put "${OVERVIEW_ID}"   --file /tmp/profile-overview.md   --no-session
ck items put "${BANNED_ID}"     --file /tmp/profile-banned.md     --no-session
ck items put "${PREFERRED_ID}"  --file /tmp/profile-preferred.md  --no-session
ck items put "${REFS_ID}"       --file /tmp/profile-refs.md       --no-session
ck items put "${FP_ID}"         --file /tmp/profile-fp.md         --no-session
ck items put "${CH_ID}"         --file /tmp/profile-chapters.md   --no-session
ck items put "${SRC_ID}"        --file /tmp/profile-source.md     --no-session
ck items put "${REG_ID}"        --file /tmp/profile-register.md   --no-session
```

Write all IDs back to `book.yaml` under `author_profile`. Use `sed` or rewrite the block:

```bash
# Read current book.yaml, update the author_profile block
python3 - <<PYEOF
import re, sys
with open("book.yaml", "r") as f:
    content = f.read()
new_block = f"""author_profile:
  overview: "{OVERVIEW_ID}"
  banned_phrases: "{BANNED_ID}"
  preferred_phrases: "{PREFERRED_ID}"
  reference_paragraphs: "{REFS_ID}"
  voice_fingerprint: "{FP_ID}"
  chapter_patterns: "{CH_ID}"
  source_style: "{SRC_ID}"
  register_examples: "{REG_ID}"
"""
# Replace existing author_profile block (multi-line) or append
content = re.sub(r'author_profile:.*?(?=\n\w|\Z)', new_block.rstrip(), content, flags=re.DOTALL)
if 'author_profile:' not in content:
    content += "\n" + new_block
with open("book.yaml", "w") as f:
    f.write(content)
PYEOF
```

Also cache overview locally:
```bash
cp /tmp/profile-overview.md .ctx/author-profile.md
```

### Existing author (profile IDs already in book.yaml)

Read existing IDs from `book.yaml`, then upload updated content directly (no `create` needed):

```bash
OVERVIEW_ID=$(grep -A 2 '^author_profile:' book.yaml | grep 'overview:' | sed -E 's/.*overview:[[:space:]]*"?//; s/"$//')
# ... repeat for each page ID

ck items put "${OVERVIEW_ID}" --file /tmp/profile-overview.md --no-session
# ... repeat for each page
cp /tmp/profile-overview.md .ctx/author-profile.md
```

### Hard rules

- **Never write `AUTHOR_VOICE.md` or `.book-producer/profile.json` locally.** CandleKeep is the only output.
- **Always update `.ctx/author-profile.md`** after writing to CandleKeep so the session stays in sync.
- **If a `ck` command fails**, log the error, write a local fallback to `.ctx/author-profile.md` with the generated content, and tell the author in Hebrew: "לא הצלחתי לשמור ב-CandleKeep. שמרתי זמנית ב-.ctx/author-profile.md — הרץ /voice כדי לנסות שוב."
```

- [ ] **Step 3: Remove the old "Save the JSON and the markdown" step** from both heavy and light path sections, and any mention of writing `AUTHOR_VOICE.md` or `AUTHOR_VOICE.draft.md` locally.

- [ ] **Step 4: Verify no local file output remains**

```bash
grep -n "AUTHOR_VOICE\|profile\.json\|Write.*md\b" plugins/hebrew-book-producer/agents/voice-miner.md
```

Expected: zero matches (or only in the hard-rules "Never write..." line).

- [ ] **Step 5: Commit**

```bash
git add plugins/hebrew-book-producer/agents/voice-miner.md
git commit -m "feat: voice-miner writes profile to CandleKeep items instead of local files"
```

---

## Task 5: Update /voice to auto-push corrections to CandleKeep

**Files:**
- Modify: `plugins/hebrew-book-producer/commands/voice.md`

- [ ] **Step 1: Read the current voice.md**

```bash
cat plugins/hebrew-book-producer/commands/voice.md
```

- [ ] **Step 2: Add CandleKeep push step** — find the "Output" section and add a new step between "AUTHOR_VOICE.md updated" and "memory.md truncated". Replace the Output section with:

```markdown
## Output

1. Read the `author_profile.overview` ID from `book.yaml`.
2. For each approved change:
   - Update `.ctx/author-profile.md` locally (the in-session working copy).
   - Determine which CandleKeep page the change belongs to:
     - Banned phrase → `author_profile.banned_phrases` ID
     - Preferred phrase → `author_profile.preferred_phrases` ID
     - Register / rhythm / persona → `author_profile.overview` ID
   - Download the relevant CandleKeep item to `/tmp/profile-<page>.md`:
     ```bash
     ck items get <page-id> --no-session > /tmp/profile-<page>.md
     ```
   - Apply the change to the local temp file.
   - Push back immediately:
     ```bash
     ck items put <page-id> --file /tmp/profile-<page>.md --no-session
     ```
3. Always push `overview` last (it's the summary page and should reflect all changes).
4. Archive processed lines from `.book-producer/memory.md` to `.book-producer/memory-archive.md` and truncate the active log.
5. Tell the author in Hebrew: "עדכנתי X כללים בפרופיל הקולי ב-CandleKeep."

## Hard rules

- **Push to CandleKeep before reporting success.** If the push fails, report the failure and leave the change pending in `.book-producer/memory.md`.
- **Never bulk-add.** Author approval per item (unchanged).
- **Never delete an existing rule** without explicit approval (unchanged).
- **If `author_profile` IDs are missing** from `book.yaml` (profile was never created), tell the author: "לא נמצא פרופיל קולי ב-CandleKeep. הרץ /voice init כדי ליצור פרופיל." — do not create local files as fallback.
```

- [ ] **Step 3: Verify**

```bash
grep -n "CandleKeep\|ck items\|author_profile" plugins/hebrew-book-producer/commands/voice.md
```

Expected: CandleKeep push logic appears in output section.

- [ ] **Step 4: Commit**

```bash
git add plugins/hebrew-book-producer/commands/voice.md
git commit -m "feat: /voice auto-pushes corrections to CandleKeep immediately"
```

---

## Task 6: Update CLAUDE.md default behaviour rule #2

**Files:**
- Modify: `plugins/hebrew-book-producer/CLAUDE.md`

- [ ] **Step 1: Find rule #2**

```bash
grep -n "AUTHOR_VOICE\|author.voice\|Voice preservation" plugins/hebrew-book-producer/CLAUDE.md
```

- [ ] **Step 2: Replace the read instruction** — change:

```
read `AUTHOR_VOICE.md` and `.book-producer/memory.md` if they exist
```

to:

```
read `.ctx/author-profile.md` (the session-cached author voice overview, loaded by the SessionStart hook from CandleKeep) and `.book-producer/memory.md` if they exist. If `.ctx/author-profile.md` is missing or empty, check `book.yaml` for `author_profile.overview` and fetch it with `ck items get <id> --no-session > .ctx/author-profile.md` before proceeding.
```

- [ ] **Step 3: Verify**

```bash
grep -n "author-profile\|AUTHOR_VOICE" plugins/hebrew-book-producer/CLAUDE.md
```

Expected: `AUTHOR_VOICE.md` removed; `.ctx/author-profile.md` in its place.

- [ ] **Step 4: Commit**

```bash
git add plugins/hebrew-book-producer/CLAUDE.md
git commit -m "fix: default behaviour reads .ctx/author-profile.md not AUTHOR_VOICE.md"
```

---

## Task 7: Add on-demand deep page loading to agents

**Files:**
- Modify: `plugins/hebrew-book-producer/agents/book-writer.md`
- Modify: `plugins/hebrew-book-producer/agents/linguistic-editor.md`
- Modify: `plugins/hebrew-book-producer/agents/proofreader.md`
- Modify: `plugins/hebrew-book-producer/agents/lector.md`

**Pattern for every agent:** Add a `## Deep profile pages` section to the agent's mandatory session-start checklist. The section is the same structure for all agents — only the pages differ.

- [ ] **Step 1: Read each agent's current checklist**

```bash
grep -n "checklist\|session.start\|AUTHOR_VOICE\|author.profile" \
  plugins/hebrew-book-producer/agents/book-writer.md \
  plugins/hebrew-book-producer/agents/linguistic-editor.md \
  plugins/hebrew-book-producer/agents/proofreader.md \
  plugins/hebrew-book-producer/agents/lector.md
```

- [ ] **Step 2: Add deep-page loading to book-writer.md**

In the mandatory session-start checklist, after the step that reads `.ctx/author-profile.md`, add:

```markdown
- **Deep profile pages (load on demand):** Before drafting or expanding any section, load additional profile pages from CandleKeep:
  ```bash
  # Read IDs from book.yaml
  REFS_ID=$(grep -A 10 '^author_profile:' book.yaml | grep 'reference_paragraphs:' | sed -E 's/.*reference_paragraphs:[[:space:]]*"?//; s/"$//')
  PREF_ID=$(grep -A 10 '^author_profile:' book.yaml | grep 'preferred_phrases:' | sed -E 's/.*preferred_phrases:[[:space:]]*"?//; s/"$//')
  CH_ID=$(grep -A 10 '^author_profile:' book.yaml | grep 'chapter_patterns:' | sed -E 's/.*chapter_patterns:[[:space:]]*"?//; s/"$//')

  [ -n "$REFS_ID" ] && ck items get "$REFS_ID" --no-session > .ctx/profile-reference-paragraphs.md
  [ -n "$PREF_ID" ] && ck items get "$PREF_ID" --no-session > .ctx/profile-preferred-phrases.md
  [ -n "$CH_ID"   ] && ck items get "$CH_ID"   --no-session > .ctx/profile-chapter-patterns.md
  ```
  Read all three cached files before writing any prose.
```

- [ ] **Step 3: Add deep-page loading to linguistic-editor.md and proofreader.md**

Same pattern, but only `banned_phrases`:

```markdown
- **Deep profile pages (load on demand):** Before editing, load the full banned-phrases page:
  ```bash
  BANNED_ID=$(grep -A 10 '^author_profile:' book.yaml | grep 'banned_phrases:' | sed -E 's/.*banned_phrases:[[:space:]]*"?//; s/"$//')
  [ -n "$BANNED_ID" ] && ck items get "$BANNED_ID" --no-session > .ctx/profile-banned-phrases.md
  ```
  Read `.ctx/profile-banned-phrases.md` before any substitution pass.
```

- [ ] **Step 4: Add deep-page loading to lector.md**

Same pattern, only `reference_paragraphs`:

```markdown
- **Deep profile pages (load on demand):** Before appraising, load representative passages to calibrate voice expectations:
  ```bash
  REFS_ID=$(grep -A 10 '^author_profile:' book.yaml | grep 'reference_paragraphs:' | sed -E 's/.*reference_paragraphs:[[:space:]]*"?//; s/"$//')
  [ -n "$REFS_ID" ] && ck items get "$REFS_ID" --no-session > .ctx/profile-reference-paragraphs.md
  ```
  Read `.ctx/profile-reference-paragraphs.md` before writing the appraisal.
```

- [ ] **Step 5: Verify all four agents have the deep-page section**

```bash
grep -l "Deep profile pages" \
  plugins/hebrew-book-producer/agents/book-writer.md \
  plugins/hebrew-book-producer/agents/linguistic-editor.md \
  plugins/hebrew-book-producer/agents/proofreader.md \
  plugins/hebrew-book-producer/agents/lector.md
```

Expected: all four filenames printed.

- [ ] **Step 6: Commit**

```bash
git add \
  plugins/hebrew-book-producer/agents/book-writer.md \
  plugins/hebrew-book-producer/agents/linguistic-editor.md \
  plugins/hebrew-book-producer/agents/proofreader.md \
  plugins/hebrew-book-producer/agents/lector.md
git commit -m "feat: agents load deep CandleKeep profile pages on demand"
```

---

## Task 8: End-to-end smoke test

No code changes — verification only.

- [ ] **Step 1: Create a test project directory**

```bash
mkdir /tmp/ck-profile-test && cd /tmp/ck-profile-test
```

- [ ] **Step 2: Run /init flow manually (simulate)**

```bash
# Simulate what /init produces for a new author
cat > book.yaml <<'EOF'
title: "Test Book"
author: "Test Author"
genre: mixed
target_words: 30000
citation_style: chicago-author-date
niqqud: false
deadline: 2026-12-31
created: 2026-05-01
author_profile:
  overview: ""
  banned_phrases: ""
  preferred_phrases: ""
  reference_paragraphs: ""
  voice_fingerprint: ""
  chapter_patterns: ""
  source_style: ""
  register_examples: ""
EOF
```

- [ ] **Step 3: Confirm session-start hook produces no author-profile.md (empty ID)**

```bash
mkdir -p .ctx
CLAUDE_PROJECT_DIR=/tmp/ck-profile-test \
  bash /PATH/TO/plugins/hebrew-book-producer/scripts/load-candlekeep-guide.sh 2>&1 | grep -i "profile"
ls .ctx/author-profile.md 2>/dev/null && echo "EXISTS (unexpected)" || echo "ABSENT (expected — no ID set)"
```

Expected: `ABSENT (expected — no ID set)`

- [ ] **Step 4: Simulate voice-miner creating a CandleKeep item**

```bash
# Create a real CandleKeep item for the overview
OVERVIEW_ID=$(ck items create "Author Profile — Overview — Test Author" \
  --description "Test profile" --no-session | grep -oE '[a-z0-9]{20,}' | tail -1)
echo "Created: $OVERVIEW_ID"

# Write minimal content
cat > /tmp/test-overview.md <<'EOF'
# Author Voice — Overview
## Register
- Default: mixed
## Banned phrases
- בעולם המשתנה של היום
EOF
ck items put "$OVERVIEW_ID" --file /tmp/test-overview.md --no-session

# Inject ID into book.yaml
sed -i '' "s/overview: \"\"/overview: \"$OVERVIEW_ID\"/" book.yaml
```

- [ ] **Step 5: Confirm session-start now pulls the profile**

```bash
CLAUDE_PROJECT_DIR=/tmp/ck-profile-test \
  bash /PATH/TO/plugins/hebrew-book-producer/scripts/load-candlekeep-guide.sh 2>&1
cat .ctx/author-profile.md
```

Expected: the content from step 4 appears in `.ctx/author-profile.md`.

- [ ] **Step 6: Clean up test item**

```bash
# Optional — delete the test CandleKeep item
ck items list --no-session | grep "Test Author"
# Note the ID and delete if the CLI supports it, or leave as an orphan
```

- [ ] **Step 7: Final commit if any fixes were made during smoke test**

```bash
git add -p  # review any fixups
git commit -m "fix: smoke test corrections to CandleKeep author profile"
```
