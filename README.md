# hebrew-book-producer

A Claude Code plugin that takes a Hebrew manuscript through the full Israeli book-production pipeline — lectorship, literary editing, linguistic editing, proofreading, and a typesetting brief.

> ספרי עיון, אוטוביוגרפיה, פילוסופיה וטקסטים דתיים. בעברית. מהערכת כתב היד עד הקובץ המוכן לדפוס.

## What it does

| Stage | Hebrew name | Agent | Output |
|---|---|---|---|
| Manuscript appraisal | קריאת לקטור | `lector` | `LECTOR_REPORT.md` |
| Literary editing | עריכה ספרותית | `literary-editor` | Tracked-changes draft + structural notes |
| Linguistic editing | עריכה לשונית | `linguistic-editor` | Sentence-level Hebrew edits |
| Proofreading | הגהה | `proofreader` | Two passes — pre- and post-typesetting |
| Typesetting brief | עימוד | `typesetting-agent` | InDesign / LaTeX brief (Frank Ruhl Libre, RTL) |
| Pipeline orchestration | ניהול הפקה | `production-manager` | Schedules sub-agents, tracks word count in גיליון דפוס (24,000 chars) |

## Runtime dependencies

The plugin **does not bundle** these — they are optional. Without them the plugin still runs in degraded single-agent mode.

1. **CandleKeep** (`ck` CLI) — *the author's curated knowledge layer.* Loaded at session start: the Writer's Guide, the Hebrew Linguistic Reference, an optional per-project thesis notebook, and any `craft_extras` listed in `book.yaml`. Not used for canonical religious texts.
2. **Sefaria MCP** (`mcp__claude_ai_Sefaria__get_text`) — *canonical-text validator.* Every Hazal citation is verified against Sefaria. Unverifiable citations are flagged `[UNVERIFIED]` in the manuscript.

## Install — per-project (recommended)

The plugin is **not** auto-loaded by Claude Code, and you usually don't want it loaded globally — it only makes sense inside a book-project directory.

### Option A — install from GitHub, enable per-project

In any Claude Code session:

```bash
/plugin marketplace add yodem/hebrew-book-producer
/plugin install hebrew-book-producer@hebrew-book-producer
```

Then in your **manuscript folder**:

```bash
cd /path/to/your/book-project
mkdir -p .claude
cat > .claude/settings.json <<'EOF'
{
  "enabledPlugins": {
    "hebrew-book-producer@hebrew-book-producer": true
  }
}
EOF
```

The plugin is now active **only** when Claude Code starts from that directory. Restart Claude Code from inside the project, then run `/help` to verify.

### Option B — local development install

```bash
git clone https://github.com/yodem/hebrew-book-producer.git ~/dev/hebrew-book-producer
```

In your book project:

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

Replace `/Users/YOU/dev` with the parent directory of the cloned repo.

### gitignore the settings file

```bash
echo ".claude/" >> .gitignore
```

### Optional setup

```bash
# CandleKeep CLI — for the shared writing-craft + Hebrew Linguistic Reference layer
curl -fsSL https://candlekeep.dev/install.sh | sh
ck auth login

# Python deps for the heavy /init-voice path
pip install pdfplumber python-docx
```

Sefaria MCP ships with claude.ai's default tools — just authenticate when prompted.

## Quick start — one sentence

```bash
cd /path/to/your/manuscript      # manuscript.md (or chapters/) already here
```

In Claude Code, type any of these in plain Hebrew or English:

| You type | What happens |
|---|---|
| **תוכל להגיה את הספר שלי?** | auto-detects the manuscript, scaffolds the project, asks 3 quick voice questions, runs the proofreader |
| תוכל לערוך / edit my book | literary + linguistic edit |
| תקרא ותגיד לי מה אתה חושב / appraise | manuscript appraisal (lector report) |
| תעמיד / typeset | typesetting brief |
| תכתוב לי פרק 3 / draft chapter 3 | book-writer drafts a chapter from a brief |
| ספר חדש / new book | scaffold an empty project |

Total inputs to proofread an existing book: **1 sentence + 1 confirmation + 3 voice answers**. No YAML editing.

### Underlying slash commands (advanced)

```
/start <action> [chapter]     # natural-language entry point
/init / /init-voice           # full project / voice setup
/lector manuscript.md         # manuscript appraisal
/edit                         # literary + linguistic edit
/proof                        # proofreading
/typeset                      # typesetting brief
/draft ch3                    # book-writer
/ship                         # full pipeline end-to-end
```

## Memory architecture

### Local (per-project)

| File | Purpose | In git? |
|---|---|---|
| `book.yaml` | Project metadata: title, author, genre, citation style, word target, niqqud, optional `thesis_notebook` and `craft_extras` (CandleKeep IDs) | yes |
| `AUTHOR_VOICE.md` | Voice fingerprint — example paragraphs, preferred/banned phrases, register | yes |
| `.book-producer/state.json` | Pipeline state per chapter | no |
| `.book-producer/memory.md` | Rolling log of user corrections | no |
| `.book-producer/runs/<id>/` | Per-run sub-agent outputs (changes.json, notes.md, log.txt) | no |
| `.book-producer/snapshots/` | Pre-edit file snapshots (rollback safety) | no |

### CandleKeep (cross-project, cached under `.ctx/`)

| File | Source | Purpose |
|---|---|---|
| `writers-guide.md` | `cmok9h0m10ahik30zt8yt0lt2` | Writer's Guide (King/Zinsser/Penn/Shapiro) |
| `agent-team-guide.md` | `cmnudfue5003rmy0zlxt7ioa1` | Building Your Agent Team |
| `thesis-notebook.md` | `book.yaml: thesis_notebook` | Author's running notes for this book |
| `craft-extras/<id>.md` | `book.yaml: craft_extras` | Additional craft references |

### External

| Source | Used for |
|---|---|
| Sefaria MCP | Validating every Hazal citation (Tanakh, Bavli, Yerushalmi, Midrash, Rambam, Shulchan Arukh, responsa) |

## Hebrew architecture document

[`README.he.md`](./README.he.md).

## License

MIT.
