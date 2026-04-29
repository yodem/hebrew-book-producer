# Hebrew Book Layout Rules — Reference

## Trim sizes

| Size | cm | Use for |
|---|---|---|
| Standard non-fiction | 14 × 21 | Default for philosophy, autobiography, popular non-fiction. |
| Compact / paperback | 13 × 19.5 | Mass-market non-fiction, religious paperbacks. |
| Large format | 16 × 23 | Academic monographs with figures, illustrated books. |
| Square | 22 × 22 | Coffee-table only. Not for prose. |

## Margins (for 14 × 21 default)

```
        ┌──────────────────────────┐
        │                          │  ← Top: 20 mm (excludes header)
        │   Running header (9 pt)  │
        │                          │
        │ ┌──────────────────────┐ │
        │ │                      │ │
        │ │                      │ │
        │ │                      │ │
        │ │      BODY TEXT       │ │
        │ │                      │ │
        │ │                      │ │
        │ │                      │ │
        │ └──────────────────────┘ │
        │                          │  ← Outer: 18 mm
        │           Folio (9 pt)   │
        │                          │  ← Bottom: 22 mm (excludes folio)
        └──────────────────────────┘
                                    ↑
                              Inner: 22 mm (gutter, RTL binding)
```

| Margin | mm | Reason |
|---|---|---|
| Inner (gutter) | 22 | Hebrew RTL bindings need extra inner space; reader's thumb must not cover text. |
| Outer | 18 | Standard reader thumbprint. |
| Top | 20 | Excludes running header. |
| Bottom | 22 | Excludes folio. |

## Running headers

| Page | Content | Alignment |
|---|---|---|
| Even (left) | Chapter title | Right-aligned (toward outer margin) |
| Odd (right) | Book title | Left-aligned (toward outer margin) |
| Chapter-opening page | NO HEADER | n/a |

In a multi-author or multi-essay book: even = chapter title; odd = author of current essay.

## Chapter breaks

1. Every chapter starts on a **left-hand page** (even page). If the previous chapter ends on an even page, insert a blank page.
2. Chapter opens at **1/3 down the page** with chapter number ("פרק <numeral or gimatria>") at 14 pt, centred.
3. Chapter title two lines below the number, 24 pt, centred, Frank Ruhl Libre Medium.
4. Three blank lines, then the first paragraph.
5. **First paragraph: no indent.** All subsequent paragraphs: 4 mm indent (RTL — text shifts to the left edge of the column).

## Block quotations

- Indent 8 mm RTL (text starts further from right edge).
- Body 0.5 pt smaller than main body (so 10.5 pt if body is 11 pt).
- Leading 14 pt.
- One blank line above and below.
- No quotation marks around the block quote — the indent does the work.

## Inline quotations

- Use Hebrew-correct quotation marks: ״...״ (right and left geresh-double).
- Latin double quotes "..." are wrong in Hebrew typesetting. Always.
- Nested quotes use single ׳...׳.

## Paragraphs

- 4 mm indent for all paragraphs except the first of a chapter / section.
- No blank line between paragraphs (blank lines suggest scene change in autobiography).
- Widow / orphan control: no fewer than 2 lines of a paragraph at the top or bottom of a page.

## Footnotes

- 9 pt Frank Ruhl Libre Book.
- Separator rule: 30 mm horizontal line, 0.5 pt, flush right.
- Numbered consecutively per chapter (restart at 1 each chapter).
- Numbers in body: superscript, 7 pt, 0.5 pt above baseline.
- Footnote text: hanging indent matching superscript width.

## Tables

- Hebrew tables read RTL: column 1 is the **rightmost** column.
- Header row in Frank Ruhl Libre Medium.
- Body in Frank Ruhl Libre Book at 10 pt.
- Row separators: 0.25 pt rules.
- No double-rules.

## Front matter (in order)

1. Half-title (book title only)
2. Title page (full title + author + publisher)
3. Copyright
4. Dedication (optional)
5. Epigraph (optional)
6. Table of contents
7. Foreword / introduction

## Back matter (in order)

1. Appendices
2. Endnotes (if footnotes were collected)
3. Bibliography
4. Index
5. About the author
6. Colophon

## Page numbering

- Front matter: lowercase Hebrew gimatria (i, ii, iii…) — but most contemporary Israeli publishers use **no numbering for front matter**.
- Body: Arabic numerals starting from page 1 = first body page.
- No folio on chapter-opening pages.
- No folio on blank versos.

## גיליון דפוס math (printing sheet calculation)

```
1 גיליון דפוס = 24,000 characters
              = 16 print pages of body text (at 14 × 21, body 11/16, default margins)
              = 1 standard 16-page signature
```

Industry pricing in Israel uses sheets, not words.

## Hebrew-specific typography pitfalls

- **Letter spacing inside a word:** never. Hebrew justification stretches *between* words, not inside them. Disable letter-spacing-on-justify in InDesign / similar.
- **Kashida elongation (Arabic-style stretching):** never in Hebrew.
- **Shins and sins:** if niqqud is on, the dot above shin/sin must render. Verify on print proof.
- **Final letters:** מ ם, נ ן, פ ף, צ ץ, כ ך — these are typeset automatically by font, not by manual swap. Verify the font does this correctly.

## Even-page chapter rule — why

Hebrew reads RTL. The reader opens the book on the right. The "first" page they see when turning to a new chapter is a **left** page. A chapter opening on a right page (odd) makes the reader's first impression of the new chapter be a single isolated page rather than a full spread. The convention: chapters open left so the reader sees a full spread (left-side title page + right-side first body page) when the chapter begins.

This is non-negotiable in serious Hebrew non-fiction.
