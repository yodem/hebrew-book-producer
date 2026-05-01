# Changelog

All notable changes to `hebrew-book-producer` are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] — 2026-05-01

### Removed
- **`skills/hazal-citation/`** removed entirely. Hazal-style references are now handled inline by `cite-master` via a Sefaria-MCP routine — one path, not two.
- **`scripts/verify-citation.sh`** removed. The Sefaria MCP tool (`mcp__claude_ai_Sefaria__get_text`) is the **sole** validator for canonical religious texts.

### Changed
- **CLAUDE.md / READMEs** updated to reflect single Sefaria path; genre table no longer references `hazal-citation`.
- **`agents/proofreader.md`, `agents/lector.md`** — replaced the `hazal-citation` conditional-skill block with a direct Sefaria-MCP verification routine.
- **`commands/proof.md`, `commands/init.md`, `commands/help.md`** — removed `hazal-citation` references; citation-style choices are now `chicago` / `apa` / `mixed`.
- **`skills/cite-master/SKILL.md`** — folds the Hazal path back in as an inline routine (no external delegation).
- **`workflows/full-pipeline.md`, `scripts/load-candlekeep-guide.sh`** — drop residual `hazal-citation` references.

### Added (Stream 3)
- **Shared Hebrew Linguistic Reference book**, synced from the public GitHub repo `yodem/hebrew-linguistics-data`. Eight curated chapters: academy-decisions, connectives-modern-usage, niqqud-rules, anti-ai-markers, citation-conventions, typography-conventions, author-register, style-fingerprint-baseline. Now loaded at session start via the candlekeep-writers-guide loader; consumed by every linguistics-touching skill.
- All affected skills (`connectives`, `review-style`, `cite-master`, `niqqud-pass`, `voice-preserver`, `hebrew-typography`, `candlekeep-writers-guide`) gained a "Knowledge source" section pointing at the right chapter ID. No new local `references/` folders.

### Added (Stream 2)
- **`/init-voice` command + voice-miner agent** with hybrid auto-detect: heavy path (computational fingerprint over `past-books/`) or light path (3-chapter manuscript sample + 10-question Hebrew interview). Produces `.book-producer/profile.json` and `AUTHOR_VOICE.md` (or `AUTHOR_VOICE.draft.md` if one already exists).
- **`scripts/extract-voice-fingerprint.py`** — Hebrew text-statistics extractor. Output schema is binary-compatible with academic-writer's documented `style-miner` schema, so the same baseline JSON works for both plugins. Supports `.md`, `.txt`, `.pdf` (via pdfplumber), `.docx` (via python-docx).
- **`scripts/voice-interview.md`** — 10-question Hebrew interview used by the light path.

### Planned (Stream 4)
- Per-agent enrichment (CandleKeep chapter pinning in agent frontmatter).
- Cross-plugin: extend `academic-helper`'s session-start loader to also read the shared book; refactor its baseline loading to fetch from CandleKeep.
- End-to-end verification + tag `v0.3.0`.

## [0.2.0] — 2026-04-29

### Added
- **Sefaria-backed citation validation.** `hazal-citation` skill now validates every Hazal reference against the Sefaria MCP tool (when running inside Claude Code) or the bundled `scripts/verify-citation.sh` (offline fallback against the public Sefaria API). Unverifiable citations are flagged `[UNVERIFIED]` in the manuscript for human review. All 5 sample citation patterns in the skill verified live against Sefaria.
- **Author thesis notebook in CandleKeep.** New `/thesis` command (`append` / `show` / `refresh`) lets the author maintain a per-project running notebook of ideas, observations, voice notes, and design decisions, persisted in CandleKeep. Configured via `book.yaml: thesis_notebook: <ck-id>`.
- **Curated craft extras.** `book.yaml: craft_extras: [<id1>, <id2>, ...]` lets the author pull additional CandleKeep-curated craft references into `.ctx/craft-extras/`.
- **Sub-agent merge protocol.** `production-manager` now writes structured outputs under `.book-producer/runs/<run-id>/` with `changes.json` per sub-agent, making runs auditable and resumable. Merge order, conflict resolution, and atomicity rules documented.
- **Non-technical user guide** (`AGENTS.md`) — Hebrew step-by-step walk-through for authors with no coding background.
- **CHANGELOG.md** (this file).

### Changed (architectural)
- **Separation of concerns: CandleKeep ≠ canonical-text store.** CandleKeep is now used exclusively for the author's curated knowledge layer (craft books, thesis notebook, voice fingerprints). Canonical religious primary texts (Tanakh / Bavli / Yerushalmi / Midrash / Rambam / Shulchan Arukh) are NOT cached in CandleKeep — every citation is validated live against Sefaria. This change replaces the v0.2 prototype's per-genre CandleKeep bundle (Bavli, Mishneh Torah, Malbim, Torah Temimah) which was redundant with Sefaria's superior coverage.
- **`load-candlekeep-guide.sh` rewritten** around the knowledge-layer model. Always loads Writer's Guide + Agent-Team guide. Optionally loads `thesis_notebook` and `craft_extras` from `book.yaml`. No more `genre`-conditional Sefaria-redundant fetches.

### Changed
- **`settings.json`** rewritten to the standard Claude Code plugin schema (`$schema`, `respectGitignore`, `permissions.allow`).
- **Hooks** moved from `settings.json` to dedicated `hooks/hooks.json` with `version: 1` envelope, matching the dvar-torah-plugin convention.
- **State directory** renamed `.claude/` → `.book-producer/` to avoid collision with Claude Code's own state directory. Affected: 18 files.
- **`${CLAUDE_PLUGIN_ROOT}`** standardised everywhere (always with curly braces, required for hook command resolution).
- **Skill frontmatter** — all 8 skills now have `user-invocable: false` so internal helper skills don't pollute the user's slash-command list.
- **Hook scripts** now require `jq` (no regex JSON parsing). Skip silently if `jq` is missing — a more robust failure mode than the previous regex fallback that broke on escaped quotes.
- **`linguistic-editor.md`** — added a "hard rule" clarifying that the 10% formula is NOT a linguistic-editor responsibility; it belongs to the literary-editor's structural cut.
- **`proofreader.md`** — unified the niqqud-pass ordering rule: it always runs as a SEPARATE sweep AFTER the main proofread, never inside the main loop.

### Added (administrative)
- `LICENSE` — MIT.
- `.gitignore` — at plugin root.

## [0.1.0] — 2026-04-29 (initial scaffold)

### Added
- Plugin skeleton: 6 specialist agents, 8 skills, 8 slash commands, 2 hooks, 2 helper scripts, 2 workflow docs.
- Pre-populated Hebrew reference data: 5-relation connectives table, Frank Ruhl Libre typography rules, Israeli book layout standards.
- Bilingual READMEs (`README.md`, `README.he.md`) and `CLAUDE.md` plugin instructions.
- Architectural plan in `~/.claude/plans/shiny-baking-abelson.md`.

[0.1.0]: https://github.com/yodem/hebrew-book-producer/commit/3155aad
