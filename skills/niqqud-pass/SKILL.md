---
name: niqqud-pass
description: Optional Hebrew niqqud-only proofreading pass for poetry, religious texts, or any project with `niqqud: true` in book.yaml. NEVER applied to modern non-fiction — niqqud rules conflict with standard modern Hebrew conventions and will damage prose. Run as a separate sweep after the main proofread.
user-invocable: false
---

# niqqud-pass — vowel-pointing proofreading

## Knowledge source

The full Academy ruleset for niqqud (כללי הניקוד 1996 + updates), shwa-na'/shwa-nach rules, dagesh kal/chazak rules, and the common-mistakes table live in the **CandleKeep book "Hebrew Linguistic Reference"**, chapter `hebrew-niqqud-rules`. Read at activation:

```bash
ck items read <hebrew-linguistic-reference-id> --chapter hebrew-niqqud-rules
```

Source on GitHub: [yodem/hebrew-linguistics-data](https://github.com/yodem/hebrew-linguistics-data).

## When to invoke

ONLY when `book.yaml` has:

```yaml
niqqud: true
```

Use cases:

- Poetry collections (שירה).
- Religious primary-source quotations (תנ"ך, שירה דתית, פיוטים).
- Children's books (where ניקוד aids reading).
- Hebrew language textbooks.

## When NEVER to invoke

- Modern Hebrew prose (academic, popular non-fiction, autobiography).
- Mixed-mode books where only block quotes have niqqud — the main flow doesn't get this pass.
- Drafts that haven't yet been proofread by `proofreader` for normal typos.

## Method

1. **Pre-flight:** verify `book.yaml` has `niqqud: true`. If not, abort and warn.
2. **Scope:** identify which passages have niqqud. Some books mix — only quotations have niqqud, body does not. The pass operates only on niqqudded passages.
3. **Verify** every niqqudded letter has the correct vowel based on:
   - Source comparison (for primary-text quotations: compare to authoritative edition).
   - Standard Hebrew niqqud rules for original prose.
4. **Specific checks:**
   - שווא נע vs שווא נח: standard rules of Tiberian niqqud.
   - דגש קל / דגש חזק: present where required (after שווא נח, after closed syllable, etc.).
   - מפיק in final ה: present when the ה is consonantal.
   - חולם vs חולם חסר: consistent decision per word.
   - קמץ קטן vs קמץ גדול: most modern editions don't distinguish; follow project convention.
   - שורוק vs קובוץ: must match standard rules of the form.
5. **Production:** annotate each error with page reference. Do NOT auto-fix — niqqud is a specialised craft and the author must approve each correction.

## Source comparison for primary texts

For Tanakh, Bavli, Yerushalmi, Midrash quotations:

- Default reference: Mikraot Gedolot for Tanakh, standard Vilna for Bavli.
- If the project has `book.yaml` field `primary_source_edition`, use that.
- Quote must match the source character-for-character INCLUDING niqqud, OR the deviation must be marked with `[...]` and a footnote.

## Output

`NIQQUD_REPORT.md`:

```
Total niqqudded passages: 47
Total niqqudded letters: 8,231
Discrepancies vs source: 12
Standard-rule violations: 5
Inconsistencies (same word niqqudded differently): 8
```

Followed by a numbered list with page references.

## Hard rules

- **Never auto-correct.** Niqqud is too specialised for autonomous correction.
- **Never apply to non-niqqudded modern Hebrew.** This will damage the prose.
- **Compare to source, not to memory.** For primary-text quotations, always pull the source.
- **The proofreader's normal pass runs FIRST.** This pass runs only after typos are clean.
