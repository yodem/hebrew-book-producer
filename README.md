# hebrew-book-producer

A Claude Code plugin that turns a Hebrew manuscript into a print-ready book through a fully orchestrated pipeline of specialist sub-agents — modelled on how an Israeli publishing house actually produces a book.

> ספרי עיון, אוטוביוגרפיה, פילוסופיה, וטקסטים דתיים. בעברית. מההערכה הראשונית של כתב היד עד הקובץ המוכן לדפוס.

## What it does

| Stage | Hebrew name | Agent | What it produces |
|---|---|---|---|
| Manuscript appraisal | קריאת לקטור | `lector` | `LECTOR_REPORT.md` |
| Literary editing | עריכה ספרותית | `literary-editor` | Track-changes draft + structural notes |
| Linguistic editing | עריכה לשונית | `linguistic-editor` | Sentence-level Hebrew edits |
| Proofreading | הגהה | `proofreader` | Two passes — pre-typesetting and post-typesetting |
| Typesetting brief | עימוד | `typesetting-agent` | InDesign / LaTeX hand-off brief (Frank Ruhl Libre, RTL) |
| Pipeline orchestration | ניהול הפקה | `production-manager` | Schedules sub-agents, tracks word count in גיליון דפוס (24,000 chars) |

## Runtime dependencies

This plugin **does not bundle** any of the following — they must be installed separately:

1. **CandleKeep** (`ck` CLI) — *the author's curated knowledge layer*. The plugin reads the user's writing-craft library at session start (Writer's Guide + Agent-Team guide + optional per-project thesis notebook + any `craft_extras` the author lists in `book.yaml`). Falls back gracefully if missing.
   **CandleKeep is not used for canonical religious texts** — those queries go to Sefaria.
2. **Sefaria** (MCP tool `mcp__claude_ai_Sefaria__get_text`) — *the canonical-text validator*. Every Hazal citation in the manuscript is verified against Sefaria via the MCP tool. Unverifiable citations are flagged `[UNVERIFIED]` in the manuscript.
3. **Superpowers** — provides `$plan-review-gate`, `$design-review-gate`, and the `writing-skills/anthropic-best-practices` reference used by the senior agents.
4. **Metaswarm** — provides `$start`, `$orchestrated-execution`, and the multi-agent spawn conventions used by `production-manager`.

If any are missing, the plugin still works in degraded single-agent mode.

## Install — per-project (recommended)

The plugin is **not** auto-loaded by Claude Code, and you usually don't want it loaded globally — it only makes sense inside a book-project directory. Enable it just in the folders where you actually have a manuscript.

### Option A — install from GitHub, enable per-project

In **any** Claude Code session (it doesn't matter which folder), add the GitHub marketplace once:

```bash
/plugin marketplace add yodem/hebrew-book-producer
/plugin install hebrew-book-producer@yodem/hebrew-book-producer
```

This makes the plugin **available** but doesn't enable it anywhere yet.

Then, in the **specific folder** where you have a manuscript:

```bash
cd /path/to/your/book-project
mkdir -p .claude
cat > .claude/settings.json <<'EOF'
{
  "enabledPlugins": {
    "hebrew-book-producer@yodem/hebrew-book-producer": true
  }
}
EOF
```

Now `hebrew-book-producer` is **only** active when Claude Code is launched from that directory. Other projects are untouched.

Restart Claude Code from inside the project. Verify with `/help` — you should see `/start`, `/proof`, `/draft`, etc.

### Option B — install locally for development, enable per-project

Clone the repo somewhere outside the book project:

```bash
git clone https://github.com/yodem/hebrew-book-producer.git ~/dev/hebrew-book-producer
```

Then in your book-project folder:

```bash
cd /path/to/your/book-project
mkdir -p .claude
cat > .claude/settings.json <<'EOF'
{
  "enabledPlugins": {
    "hebrew-book-producer@local": true
  },
  "extraKnownMarketplaces": {
    "local": {
      "source": { "source": "local", "path": "/Users/YOU/dev" }
    }
  }
}
EOF
```

Replace `/Users/YOU/dev` with the actual parent directory of the cloned repo. Restart Claude Code from inside the project.

### Don't forget to gitignore the settings file (if your manuscript is in a git repo)

`.claude/settings.json` is project-scoped configuration — you typically don't want it in version control:

```bash
echo ".claude/" >> .gitignore
```

### Optional but strongly recommended runtime dependencies

Install these once on your machine; the plugin uses them when present and degrades gracefully otherwise:

```bash
# CandleKeep CLI — for the shared writing-craft + Hebrew Linguistic Reference layer
curl -fsSL https://candlekeep.dev/install.sh | sh
ck auth login

# Python deps for the voice fingerprint extractor (only needed for /init-voice heavy path)
pip install pdfplumber python-docx
```

Sefaria MCP comes with claude.ai's default tools — just authenticate when prompted.

## Quick start — the one-sentence flow

```bash
cd /path/to/your/manuscript      # manuscript.md (or chapters/) already here
```

Then in Claude Code, type any of these in plain Hebrew or English:

| What you type | What happens |
|---|---|
| **תוכל להגיה את הספר שלי?** | auto-detects the manuscript, scaffolds the project, asks 3 quick voice questions, runs the proofreader, returns a fix report |
| תוכל לערוך / edit my book | literary + linguistic edit |
| תקרא ותגיד לי מה אתה חושב / appraise | manuscript appraisal (lector report) |
| תעמיד / typeset | typesetting brief |
| תכתוב לי פרק 3 / draft chapter 3 | book-writer drafts a chapter from a brief |
| ספר חדש / new book | scaffold-only — sets up an empty project |

Total inputs to proofread an existing book: **1 sentence + 1 confirmation + 3 voice answers**. No YAML editing.

### Advanced — the underlying slash commands

Power users can skip the natural-language layer:

```bash
/start proofread                # the auto-bootstrap entry-point
/start write ch3                # draft chapter 3 via book-writer
/init                           # interactive project setup (long form)
/init-voice                     # full 10-question voice fingerprint
/lector manuscript.md           # manuscript appraisal
/edit                           # literary + linguistic edit
/proof                          # proofreading
/typeset                        # typesetting brief
/draft ch3                      # book-writer directly
/ship                           # full pipeline end-to-end
```

## Memory architecture

The plugin uses three layers of memory, each with a different lifecycle and purpose.

### Local (per-project)

| File | Purpose | Versioned in git? |
|---|---|---|
| `book.yaml` | Project metadata: title, author, genre, citation style, word target, niqqud on/off, optional `thesis_notebook:` (CandleKeep ID) and `craft_extras:` (list of CandleKeep IDs) | yes |
| `AUTHOR_VOICE.md` | Voice fingerprint: example paragraphs, preferred/banned phrases, register, persona | yes |
| `.book-producer/state.json` | Pipeline state per chapter | no |
| `.book-producer/memory.md` | Rolling log of user corrections (what the AI got wrong) | no |
| `.book-producer/runs/<id>/` | Per-run sub-agent outputs (changes.json, notes.md, log.txt) — auditable, resumable | no |
| `.book-producer/snapshots/` | Pre-edit file snapshots (rollback safety) | no |

### CandleKeep (cross-project, author knowledge layer)

| File (cached under `.ctx/`) | Source | Purpose |
|---|---|---|
| `writers-guide.md` | `cmok9h0m10ahik30zt8yt0lt2` | Writer's Guide (King/Zinsser/Penn/Shapiro) |
| `agent-team-guide.md` | `cmnudfue5003rmy0zlxt7ioa1` | Building Your Agent Team (multi-agent design) |
| `thesis-notebook.md` | `book.yaml: thesis_notebook` | Author's running notes for THIS book (managed via `/thesis`) |
| `craft-extras/<id>.md` | `book.yaml: craft_extras: [...]` | Additional craft references the author has curated |

### External (canonical-text validator)

| Source | Used for |
|---|---|
| Sefaria MCP | Validating every Hazal citation in the manuscript (Tanakh, Bavli, Yerushalmi, Midrash, Rambam, Shulchan Arukh, responsa) |

## Hebrew architecture document

The full Hebrew design document is at [`README.he.md`](./README.he.md).

## Status

`v0.4.0` — Natural-language entry-point + book-writer agent. One freeform sentence (Hebrew or English) auto-bootstraps the project and runs the requested action. New `book-writer` agent drafts chapters from briefs, with per-genre conventions for biography / philosophy / religious / popular non-fiction. See `CHANGELOG.md` for the full v0.3.0 → v0.4.0 history and `CLAUDE.md` for current behaviour.

## License

MIT.
