---
name: hazal-citation
description: Citation conventions for Hebrew religious primary sources — Tanakh, Talmud Bavli, Talmud Yerushalmi, Midrash, Rambam, Rashi, Tosafot, and other classical literature. Specialised sub-skill of cite-master. Used by linguistic-editor and proofreader when religious primary sources appear in the manuscript.
user-invocable: false
---

# hazal-citation — Hebrew religious-source citations

## When to invoke

When the cite-master skill detects a religious primary source. Common patterns:

- "(בבלי…", "(ירושלמי…"
- "(בראשית…", "(שמות…", "(תהלים…", any Tanakh book
- "(מדרש רבה…", "(תנחומא…", "(מכילתא…"
- "(רמב"ם, הלכות…", "(שולחן ערוך…"
- "רש"י על…", "תוס' על…", "רא"ש על…"

## Citation formats by source

### Tanakh

Format: `(<ספר> <פרק>:<פסוק>)` or `(<ספר> <פרק> <פסוק>)`.

| Style | Example |
|---|---|
| Modern Hebrew academic | (בראשית א, א) |
| Traditional | (בראשית פרק א פסוק א) |
| Compact | (בר' א, א) — only with a list of abbreviations in front matter |

For a range: `(תהלים קיט, א-יח)`.

For a chapter alone: `(איוב כח)`.

**Always**:
- Hebrew letters for chapter and verse (gimatria), not Arabic numerals.
- Comma between chapter and verse.
- Book name in full unless an abbreviations table exists.

### Talmud Bavli

Format: `(בבלי <מסכת> <דף>, <עמוד>)` where עמוד is "ע"א" or "ע"ב".

| Example | Meaning |
|---|---|
| (בבלי ברכות י, ע"א) | Berakhot 10a |
| (בבלי שבת קיט, ע"ב) | Shabbat 119b |
| (בבלי בבא מציעא נט, ע"ב) | Bava Metzia 59b |

For a range: `(בבלי ברכות י, ע"א – יא, ע"ב)`.

### Talmud Yerushalmi

Format: `(ירושלמי <מסכת> <פרק>:<הלכה>)`.

| Example | Meaning |
|---|---|
| (ירושלמי ברכות א:א) | Yerushalmi Berakhot ch. 1 hal. 1 |
| (ירושלמי פאה ה:ב) | Yerushalmi Pe'ah ch. 5 hal. 2 |

Some editions cite by page-and-column (Vilna): `(ירושלמי ברכות ב, ע"ג)`. Project must declare which convention in `book.yaml`:

```yaml
yerushalmi_citation: chapter-halacha  # | vilna-page
```

### Midrash

Format depends on midrash:

| Midrash | Format | Example |
|---|---|---|
| Midrash Rabba | (<ספר> רבה <פרשה>:<סימן>) | (בראשית רבה ב:ה) |
| Tanchuma | (תנחומא <פרשה>, <סימן>) | (תנחומא בראשית, ז) |
| Mekhilta | (מכילתא דרבי ישמעאל, <מסכתא>, <פרק>) | (מכילתא דרבי ישמעאל, מסכתא דבחדש, פרק ה) |
| Sifra / Sifrei | (ספרא, <פרשה>, <פרק>) | (ספרא, ויקרא, פרק ב) |

### Rambam (Mishneh Torah)

Format: `(רמב"ם, הלכות <נושא> <פרק>:<הלכה>)`.

Examples:
- (רמב"ם, הלכות תשובה ג, ב)
- (רמב"ם, הלכות מלכים יא, ד)

For Moreh Nevuchim: `(רמב"ם, מורה נבוכים, חלק <חלק>, פרק <פרק>)` — e.g. `(רמב"ם, מורה נבוכים, חלק א, פרק נא)`.

### Shulchan Arukh

Format: `(שולחן ערוך, <חלק>, <סימן>:<סעיף>)`.

Examples:
- (שולחן ערוך, אורח חיים, צ:א)
- (שולחן ערוך, יורה דעה, רמו:ד)

### Commentaries on the spot (Rashi, Tosafot, Ramban, etc.)

Format: `<מפרש> <על המקור>` — usually inline, no parentheses.

| Example | Meaning |
|---|---|
| רש"י על בראשית א, א | Rashi on Genesis 1:1 |
| תוס' על שבת לא, ע"א, ד"ה <Hebrew word> | Tosafot ad loc., starting "..." |
| רמב"ן על שמות ג, ב | Ramban on Exodus 3:2 |

### Modern poskim and responsa

Format: `(<מחבר>, <שם הספר>, <חלק>:<סימן>)`.

Examples:
- (אגרות משה, אורח חיים א, סימן ד)
- (יביע אומר, חלק ה, יורה דעה, סימן ב)
- (מנחת יצחק, חלק ז, סימן ל"ב)

## Validation rules

For each detected hazal citation:

1. **Source name spelling.** Verify against canonical list (Tanakh books, masechet names, midrash names). Common typos: "בבא מציאע" should be "בבא מציעא".
2. **Chapter / verse format.** Must use Hebrew letters (gimatria). Reject any pure-Arabic-numeral hazal citation.
3. **Page-side notation.** Must be "ע"א" or "ע"ב" (with quotes), not "א" or "ב" alone, not "a" / "b".
4. **Range punctuation.** En-dash with spaces around: `י, ע"א – יא, ע"ב`.
5. **Quotation accuracy.** When a hazal source is quoted (not just cited), the Hebrew must match the canonical edition character-for-character. Any deviation gets `[...]`.

## Sefaria validation (preferred — when available)

The skill now validates every detected citation against [Sefaria](https://www.sefaria.org), which is the canonical online corpus.

### Method 1 — Sefaria MCP tool (preferred, when running inside Claude Code with the MCP server enabled)

If the agent has access to `mcp__claude_ai_Sefaria__get_text` (or any of the other Sefaria MCP tools), call it directly with the English Sefaria reference form:

| Hebrew citation in manuscript | Sefaria reference to query |
|---|---|
| `(בבלי ברכות י, ע"א)` | `Berakhot 10a` |
| `(ירושלמי ברכות א:א)` | `Jerusalem Talmud Berakhot 1:1` |
| `(בראשית רבה ב:ה)` | `Genesis Rabbah 2:5` |
| `(רמב"ם, הלכות תשובה ג:ב)` | `Mishneh Torah, Repentance 3:2` |
| `(שולחן ערוך, אורח חיים צ:א)` | `Shulchan Arukh, Orach Chayim 90:1` |
| `(בראשית א:א)` | `Genesis 1:1` |
| `(תהלים קיט:א-יח)` | `Psalms 119:1-18` |

Mapping rules:
- Hebrew gematria → Arabic numeral.
- Tractate / book name → English Sefaria title (use `mcp__claude_ai_Sefaria__clarify_name_argument` if uncertain).
- Page-side `ע"א` → `a`; `ע"ב` → `b`.

If MCP returns text → **VERIFIED**.
If MCP returns an error or empty → **NOT-FOUND** (mark in manuscript as `[הציטוט לא נמצא בספריא — לבדוק במהדורה מודפסת]`).

### Method 2 — Bundled fallback script (when MCP is unavailable)

Run `bash ${CLAUDE_PLUGIN_ROOT}/scripts/verify-citation.sh "<English Sefaria reference>"`.

The script tries the `sefaria` CLI first, then falls back to the public Sefaria API via curl.

Output:
- Line 1: `VERIFIED` | `NOT-FOUND` | `UNVERIFIED`
- Line 2: canonical reference (or original on miss)

If line 1 is `UNVERIFIED` (no network / no tool), mark the citation in the manuscript with `[UNVERIFIED]` so a human can validate later.

### Caveat — Sefaria normalisation

Sefaria is forgiving about edge inputs. A made-up reference like `Bava Metzia 999a` may silently normalise to `Bava Metzia 2a` (the first valid page). Always compare the **canonical ref returned by Sefaria** against the **original ref**. If they differ in chapter/page numbers, treat as `NOT-FOUND` and flag.

## Marking unverified citations in the manuscript

For citations that cannot be validated (no network, no MCP, source not in Sefaria, or Sefaria returned a different canonical ref):

```
(בבלי ברכות י, ע"א) [UNVERIFIED — Sefaria unreachable this session, please verify against printed edition]
```

The square-bracket flag is a deliberate, agent-friendly marker. The proofreader sweeps for `[UNVERIFIED]` flags during pass 2 and reports them as a list. **Never strip `[UNVERIFIED]` markers without reverifying.**

## Output

Embedded in `CITATION_REPORT.md` (the cite-master skill's main report) as a separate "Hazal Citations" section. Schema:

```
## Hazal Citations

| # | Citation in manuscript | Sefaria ref | Status | Notes |
|---|---|---|---|---|
| 1 | (בבלי ברכות י, ע"א) | Berakhot 10a | ✓ VERIFIED | exact match |
| 2 | (בבלי ברכות י, ע"ב) | Berakhot 10b | ✓ VERIFIED | |
| 3 | (בבלי ברכות תקעב, ע"א) | — | ✗ NOT-FOUND | page does not exist |
| 4 | (ירושלמי ברכות א:א) | Jerusalem Talmud Berakhot 1:1 | [UNVERIFIED] | Sefaria unreachable |
```

For NOT-FOUND citations: append `[INVALID — no such reference]` to the manuscript and explain in PROOF_NOTES.md.
For UNVERIFIED citations: append `[UNVERIFIED]` and require human verification before publication.

## Hard rules

- **Quote accurately.** Religious primary sources are not paraphrased — quoted with brackets for any change.
- **Use the canonical name.** "מכילתא" without "דרבי ישמעאל" is ambiguous (could be d'Rashbi). Always specify.
- **Hebrew gimatria, not Arabic numerals.** Even in academic books that otherwise use Arabic numerals.
- **Source must exist.** A citation pointing to "ירושלמי ברכות לב, ה" is impossible — Yerushalmi Berakhot has 9 chapters. Validate against a chapter/halacha map.
