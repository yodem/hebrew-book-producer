# Hebrew Book Fonts — Reference

## Default body font: Frank Ruhl Libre

**Frank Ruhl Libre** is the open-source descendant of the Frank-Ruehl Hebrew type, originally designed by Raphael Frank in 1908 for the German publisher C.F. Ruhl. It has been the de-facto Hebrew book typeface for over a century. The Libre version (released 2017 by Yanek Iontef and others under the SIL Open Font License) is the modern digital cut suitable for both screen and print.

| Weight | Use for |
|---|---|
| Frank Ruhl Libre Book | Body text — non-fiction, philosophy, autobiography. Default. |
| Frank Ruhl Libre Medium | Chapter titles, running headers. |
| Frank Ruhl Libre Bold | Section headers, emphasis (sparingly). |
| Frank Ruhl Libre Black | Cover only. |

## Sizing rules

| Use | Size | Leading |
|---|---|---|
| Body — non-fiction | 11 pt | 16 pt |
| Body — non-fiction (long book, 100k+ words) | 10.5 pt | 15 pt |
| Body — religious / poetry (with niqqud) | 12 pt | 18 pt |
| Footnotes | 9 pt | 12 pt |
| Chapter title | 24 pt | natural |
| Chapter number ("פרק") | 14 pt | natural |
| Running header | 9 pt | natural |
| Folio (page number) | 9 pt | natural |
| Block quote (indented) | 10.5 pt | 14 pt |

## Latin-script fallback (for foreign-language quotations)

When Hebrew text contains a Latin-script passage (a quote from German philosophy, an English citation, a Greek term), use a Latin font of matching x-height:

| Hebrew body font | Recommended Latin pairing |
|---|---|
| Frank Ruhl Libre Book | EB Garamond Regular |
| Frank Ruhl Libre Medium | EB Garamond Medium |

Set the Latin font to the same point size as the body. The x-heights will align, and the page texture stays even.

## Why NOT these fonts (common mistakes)

| Font | Why not |
|---|---|
| **Arial** | Screen font. Looks like a school worksheet in print. |
| **David (Microsoft)** | Office-document font. Lacks the rhythm needed for sustained reading. |
| **Times New Roman + Hebrew fallback** | The Hebrew fallback is usually David — see above. |
| **Open Sans Hebrew** | Web font. Too thin for book paper. |
| **Narkisim** | Cool for headlines, exhausting for body. |
| **Hadassah Friedlaender** | Beautiful, but proprietary; do not use unless licensed. |

## Open-source alternatives to Frank Ruhl Libre

If Frank Ruhl Libre is not appropriate (e.g. very modernist book design):

| Font | Use case |
|---|---|
| **Heebo** | Modernist, geometric, sans-serif. Memoir or popular-non-fiction with a contemporary feel. |
| **Assistant** | Clean modern sans. Good for self-help, business non-fiction. |
| **Rubik** | Slightly playful sans. Avoid for academic work. |
| **Suez One** | Display only — never body. |

## Niqqud-compatible fonts

If `book.yaml` has `niqqud: true`, the font must render diacritics correctly. Verified niqqud-compatible:

- Frank Ruhl Libre (all weights). ✅ Default for niqqud.
- Heebo. ✅
- David Libre. ✅
- Avoid: Open Sans Hebrew (niqqud collides with letterforms), Rubik (same).

## Procurement

Frank Ruhl Libre, Heebo, Assistant, Rubik, David Libre, EB Garamond — all available free at fonts.google.com under OFL.
