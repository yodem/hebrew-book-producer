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

## Output

Embedded in `CITATION_REPORT.md` (the cite-master skill's main report) as a separate "Hazal Citations" section.

## Hard rules

- **Quote accurately.** Religious primary sources are not paraphrased — quoted with brackets for any change.
- **Use the canonical name.** "מכילתא" without "דרבי ישמעאל" is ambiguous (could be d'Rashbi). Always specify.
- **Hebrew gimatria, not Arabic numerals.** Even in academic books that otherwise use Arabic numerals.
- **Source must exist.** A citation pointing to "ירושלמי ברכות לב, ה" is impossible — Yerushalmi Berakhot has 9 chapters. Validate against a chapter/halacha map.
