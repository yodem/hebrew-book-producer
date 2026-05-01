---
name: review-style
description: Detect AI-flat Hebrew prose and prescribe fixes. Measures Burstiness (sentence-length variance), flags banned AI-marker phrases ("בעולם המשתנה של היום", "חשוב לזכור ש"...), and suggests rhythm injections. Use whenever the linguistic-editor or proofreader is about to commit edits — and whenever the user reports that the prose "sounds AI."
user-invocable: false
---

# review-style — giving Hebrew prose its human pulse

## When to invoke

- Linguistic-editor reaches the end of a chapter and is about to hand off to proofreader.
- User says "this sounds like ChatGPT wrote it" / "זה נשמע כמו AI".
- Production-manager runs a sanity gate before declaring a chapter complete.

## What this skill checks

### 1. Burstiness (גיוון אורך משפטים)

AI-generated Hebrew tends to cluster around medium-length sentences. Healthy human prose alternates short, medium, and long.

**Algorithm:**
1. Split the chapter into sentences (split on `. `, `! `, `? `, `: ` outside of quotes).
2. Compute character-length per sentence.
3. Compute the **standard deviation / mean** ratio. Below `0.45` is suspicious (AI-flat).
4. Find the longest run of consecutive sentences within ±15% of the mean. A run of 6+ such sentences is a "flat zone" — flag for fixing.

**Fix:** in flat zones, recommend converting one sentence into a fragment (3–5 words). Or split a long sentence into two short, punchy ones.

### 2. Banned openers (פתיחים אסורים)

These phrases are AI-marker tells. **Replace, never delete and pretend it was nothing** — the underlying content needs to actually exist.

| Banned | Why | Replace with |
|---|---|---|
| בעולם המשתנה של היום | empty | concrete year, concrete event, concrete person |
| במאמר זה ננסה ל… | meta-narration | the actual claim |
| חשוב לזכור ש… | hedging | the thing itself |
| כפי שראינו | self-referential bloat | nothing — cut |
| לסיכום, ניתן לומר ש… | summary stock phrase | the summary itself, no preamble |
| ראוי לציין כי… | apologetic hedge | nothing — cut |
| ככלל, ניתן לומר ש… | softens an assertion you should make | the assertion |

### 3. Empty hedges

Across the whole chapter, count occurrences of: כביכול, במידה מסוימת, בצורה זו או אחרת, מעין, איזושהי. Flag any chapter with more than 3 instances per 1,000 words. These are usually deletable.

### 4. Concept-noun overload (Zinsser §3 in the writers-guide)

Hebrew AI prose loves abstract nouns where verbs would be clearer. Flag patterns like:

- "ביצוע של בדיקה" → "לבדוק"
- "קיום של דיון" → "לדון"
- "במסגרת התייחסות אל…" → "ביחס ל…"

### 5. Adverb density

Count adverbs ending in -ית (סופית, בסופו של דבר, בעיקרו של דבר, בסופו של יום). Flag chapters with > 5 per 1,000 words. Then check each instance — most are deletable.

## Output format

Return a JSON-ish report:

```
{
  "chapter": "ch04",
  "burstiness_ratio": 0.38,
  "flat_zones": [{"start": "p.41", "end": "p.43", "sentence_count": 9}],
  "banned_openers_found": [{"phrase": "בעולם המשתנה של היום", "page": 41}],
  "empty_hedges_per_1000_words": 5.2,
  "concept_nouns_to_replace": [{"original": "ביצוע של בדיקה", "page": 47, "suggested": "לבדוק"}],
  "verdict": "needs revision"
}
```

## Hard rules

- **Suggest, do not auto-fix.** Voice is the author's. The skill produces flags; the linguistic-editor decides.
- **Don't flag style as a marker.** Some authors genuinely write long, complex sentences. The Burstiness check fails when applied to a deliberate stylistic choice. Always cross-reference `AUTHOR_VOICE.md` first.

## Knowledge source

The full curated banned-opener corpus (~30+ entries with reasons + Hebrew alternatives), the 5-dimension scoring rubric (directness / rhythm / trust / authenticity / density), and the structural-tells list live in the **CandleKeep book "Hebrew Linguistic Reference"**, chapter `hebrew-anti-ai-markers`. Read at activation:

```bash
ck items read <hebrew-linguistic-reference-id> --chapter hebrew-anti-ai-markers
```

Also read chapter `hebrew-author-register` from the same book for register-flatness diagnosis. Local table above (sections "Banned openers" / "Empty hedges") is a quick-reference summary; the CandleKeep chapter is authoritative. Source on GitHub: [yodem/hebrew-linguistics-data](https://github.com/yodem/hebrew-linguistics-data).

## References

- Writers-guide Ch. 9 (Zinsser principles) at `.ctx/writers-guide.md`.
- `AUTHOR_VOICE.md` for author-specific overrides.
