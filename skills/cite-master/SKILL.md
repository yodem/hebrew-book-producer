---
name: cite-master
description: Format citations consistently per the project's citation style (Chicago Author-Date / APA / Hazal-style). Reads book.yaml's citation_style field. Validates that every footnote and bibliography entry follows the chosen format. Includes an inline routine for religious primary sources that verifies each reference against Sefaria via the MCP tool.
user-invocable: false
---

# cite-master — citations, consistently

## When to invoke

- Linguistic-editor finishes a chapter that contains citations.
- Proofreader is doing pass 1 and finds an unfamiliar citation format.
- User runs `/proof` on a chapter with footnotes.

## Supported citation styles

The skill reads `book.yaml`:

```yaml
citation_style: chicago-author-date  # | apa | hazal | mixed
```

| Style | Use for |
|---|---|
| `chicago-author-date` | Hebrew academic philosophy, history, social science. Default. |
| `apa` | Hebrew popular psychology, applied science. |
| `hazal` | Hebrew religious primary sources — formatted inline by this skill, with each reference verified against Sefaria. |
| `mixed` | Books that span multiple registers. Author specifies a per-chapter override. |

## Chicago Author-Date — Hebrew conventions

In-text: `(שמיר 2018, 47)` or `(Levinas 1961, 197)` for foreign-language sources.

Bibliography:

```
שמיר, אילן. 2018. *הסדר החדש*. ירושלים: מאגנס.
Levinas, Emmanuel. 1961. *Totalité et infini*. La Haye: Nijhoff.
```

Hebrew rules:
- Author name in **first-name-then-family-name** order in the in-text citation, but **family-name-comma-first-name** in the bibliography (Hebrew convention follows English Chicago here).
- Italics use `*...*` in the source markdown — the typesetting agent converts to true italics later.
- Hebrew dates are NOT converted to Hebrew calendar in citations. Use Gregorian.
- Foreign-language titles stay in their original alphabet, italicised.

## APA — Hebrew conventions

In-text: `(שמיר, 2018, ע' 47)`.

Bibliography:

```
שמיר, א' (2018). *הסדר החדש*. הוצאת מאגנס.
```

## Hazal — inline routine

For tractate references, midrash, scripture, Rambam, Shulchan Arukh, responsa: this skill formats and verifies them directly. No external skill is invoked.

### Recognised patterns
- `(בבלי ברכות י, ע"ב)`
- `(ירושלמי שבת ב, ג)`
- `(מדרש רבה, בראשית פרשה ב, ה)`
- `(רמב"ם, הלכות תשובה ג, ב)`
- `(שולחן ערוך, אורח חיים סימן א)`
- Tanakh: `(בראשית א, א)` / `(תהילים קיט, יח)`

### Format rules
- Always Hebrew, traditional reference order: source → tractate/sefer → chapter → page or halacha.
- Use `ע"א` / `ע"ב` for Babylonian Talmud daf-side, with quotation marks (not straight ASCII apostrophe).
- Use a space-comma between chapter and verse: `בראשית א, א`.
- Italicise nothing — Hazal references are by convention plain.

### Verification — Sefaria MCP

For every Hazal-style reference detected, call `mcp__claude_ai_Sefaria__get_text` with the reference string normalised to Sefaria's API form (e.g., "Berakhot 10b", "Genesis 1:1"). Three outcomes:

1. Sefaria returns the text → reference is valid; leave alone.
2. Sefaria returns 404 / no result → tag the in-text reference with `[UNVERIFIED]` so the author can fix it manually.
3. Sefaria returns text but the manuscript's quoted Hebrew differs significantly → flag in `CITATION_REPORT.md` under "primary-source quote drift".

Do **not** auto-correct primary-source quotes. The author may have intentionally bracketed an emendation. The skill's job is to flag, not to rewrite.

## What this skill validates

For each citation in the manuscript:

1. Does it follow the declared style?
2. Are all required fields present?
3. Does the bibliography contain a matching entry?
4. Are author names spelled identically across in-text and bibliography?
5. Are dates consistent?
6. Are page ranges formatted with the right separator (Chicago: `45–67`, APA: `45-67`)?

## Output

A `CITATION_REPORT.md`:

```
Total citations: 142
Bibliography entries: 138
Orphans (cited but not in bib): 4
Unused (in bib but not cited): 0
Style violations: 7 (see below)
Hazal references verified via Sefaria: 23 (1 [UNVERIFIED])
```

Followed by a numbered list of violations with page references.

## Hard rules

- **Never silently rewrite.** Always flag and let the human approve.
- **Mixed styles are fine within `mixed` mode** — a philosophy book with religious primary sources should use Chicago for academic refs and Hazal for primary religious refs in the same footnote.
- **Author spelling consistency.** Compare every author surname across in-text + bibliography. Even one-character drift gets flagged.
