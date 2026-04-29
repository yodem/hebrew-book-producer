---
name: cite-master
description: Format citations consistently per the project's citation style (Chicago Author-Date / APA / Hazal). Reads book.yaml's citation_style field. Validates that every footnote and bibliography entry follows the chosen format. Hands off to hazal-citation skill when religious primary sources appear.
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
| `hazal` | Hebrew religious texts (delegated to `hazal-citation` skill) |
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

## Hazal — delegated

For tractate references, midrash, scripture: hand off to the `hazal-citation` skill. This skill recognises the pattern and delegates:

- "(בבלי ברכות י, ע"ב)" → hazal-citation
- "(מדרש רבה, בראשית פרשה ב, ה)" → hazal-citation
- "(רמב"ם, הלכות תשובה ג, ב)" → hazal-citation

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
Hazal delegations: 23
```

Followed by a numbered list of violations with page references.

## Hard rules

- **Never silently rewrite.** Always flag and let the human approve.
- **Mixed styles are fine within `mixed` mode** — a philosophy book with religious primary sources should use Chicago for academic refs and Hazal for primary religious refs in the same footnote.
- **Author spelling consistency.** Compare every author surname across in-text + bibliography. Even one-character drift gets flagged.
