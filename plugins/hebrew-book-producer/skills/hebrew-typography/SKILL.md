---
name: hebrew-typography
description: Hebrew book typography reference. Frank Ruhl Libre as the default body font, RTL margin rules, even-page chapter starts, גיליון דפוס math (24,000 characters per printing sheet). Used by typesetting-agent to produce the typesetting brief.
user-invocable: false
---

# hebrew-typography — Hebrew book layout standards

## When to invoke

- Typesetting-agent is producing `TYPESETTING_BRIEF.md`.
- A user asks "what font should this book use?"
- Production-manager is calculating word count in printing sheets.

## Reference files (load these)

- [`references/fonts.md`](./references/fonts.md) — fonts and sizing (typesetting-machine-specific, plugin-local).
- [`references/layout-rules.md`](./references/layout-rules.md) — margins, headers, chapter breaks, גיליון דפוס math (typesetting-machine-specific, plugin-local).

## Knowledge source — Hebrew character & punctuation conventions

For everything character-level (`״` vs `"`, `׳` vs `'`, en-dash vs מקף עברי, RTL/LTR controls, numerals, quotation rules), read the **CandleKeep book "Hebrew Linguistic Reference"**, chapter `hebrew-typography-conventions`:

```bash
ck items read <hebrew-linguistic-reference-id> --chapter hebrew-typography-conventions
```

The chapter has the full Unicode-codepoint table, abbreviation rules (גרש vs גרשיים), and the bidi pitfalls in mixed-language passages. Source on GitHub: [yodem/hebrew-linguistics-data](https://github.com/yodem/hebrew-linguistics-data). The local `references/` folder stays for typesetting-machine specifics that are not shared cross-plugin.

## גיליון דפוס (printing sheet) math

Israeli book production prices and schedules in **printing sheets**:

```
1 גיליון דפוס = 24,000 characters (including spaces, excluding YAML / markdown headings / footnote markup)
```

A typical Israeli non-fiction book:

| Genre | Typical sheet count |
|---|---|
| Philosophy | 8–14 sheets (192k–336k chars) |
| Autobiography | 6–10 sheets (144k–240k chars) |
| Popular non-fiction | 5–8 sheets (120k–192k chars) |
| Religious essay collection | 6–12 sheets |

Use `bash $CLAUDE_PLUGIN_ROOT/scripts/count-printing-sheets.sh <file>` to compute this.

## Default specifications (lifted from `layout-rules.md`)

| Element | Default |
|---|---|
| Body font | Frank Ruhl Libre Book |
| Body size | 11 pt |
| Body leading | 16 pt |
| Trim size | 14 × 21 cm |
| Inner margin | 22 mm |
| Outer margin | 18 mm |
| Top margin | 20 mm |
| Bottom margin | 22 mm |
| Chapter starts | Even (left) page only |
| Even-page header | Chapter title, right-aligned |
| Odd-page header | Book title, left-aligned |
| Folio | Bottom outer corner, 9 pt |

## Hard rules

- **Frank Ruhl Libre is the default.** Override only with explicit author instruction.
- **Never propose Arial, David, or Times New Roman for body.** Those are screen / institutional fonts, not book fonts.
- **Even-page chapter starts.** Always.
- **RTL-correct quotation marks** (״ ... ״), never Latin double quotes.
- **The typesetting-agent produces a brief, not a PDF.**
