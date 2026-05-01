#!/usr/bin/env python3
"""
extract-voice-fingerprint.py — compute a Hebrew style fingerprint over one or
more text/markdown/PDF/DOCX files and emit JSON with the schema documented in
the CandleKeep "Hebrew Linguistic Reference" book, chapter `hebrew-style-fingerprint-baseline`.

Used by /init-voice in two paths:
  * heavy — input is `past-books/` (≥1 file).
  * light — input is a sample of the current manuscript (3 chapters).

The output JSON's field names are binary-compatible with the schema documented
in academic-writer's style-miner agent — both plugins consume the same shape.

Usage:
  ./extract-voice-fingerprint.py --input <path-or-dir> --output <file.json> [--baseline <ck-cached-md>]

Optional --baseline: a path to .ctx/hebrew-linguistic-reference.md (cached
from the CandleKeep book). The script extracts the baseline JSON code block
from the `hebrew-style-fingerprint-baseline` chapter and emits a contrastive
section with deviations from baseline. If the baseline isn't readable,
contrastive is skipped (not fatal).
"""

from __future__ import annotations
import argparse, json, math, re, sys
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone

# Optional deps — used when input is PDF/DOCX. The script degrades gracefully.
try:
    import pdfplumber  # type: ignore
except Exception:
    pdfplumber = None

try:
    import docx  # python-docx  # type: ignore
except Exception:
    docx = None


HEBREW_RANGE = re.compile(r"[֐-׿]")
HE_TOKEN = re.compile(r"[֐-׿'׳״]+|[A-Za-z]+")
SENT_END = re.compile(r"[.!?׃]+(?:\s|$)|\n{2,}")
PARA_SPLIT = re.compile(r"\n\s*\n")

# Heuristic Hebrew passive: niphal/pual/hofal — pattern-matched on word forms.
# Pragmatic, not linguistically perfect.
PASSIVE_PREFIX = re.compile(r"^(?:נ|מו?[פב]ע?|הו?[פב]ע?)")
FIRST_PERSON_TOKENS = {"אני", "אנחנו", "אנו", "לי", "לנו", "שלי", "שלנו", "אצלי", "אצלנו"}


def load_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt"}:
        return path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".pdf" and pdfplumber is not None:
        out = []
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                out.append(t)
        return "\n".join(out)
    if suffix == ".docx" and docx is not None:
        d = docx.Document(str(path))
        return "\n".join(p.text for p in d.paragraphs)
    return path.read_text(encoding="utf-8", errors="replace")


def collect_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    out = []
    for ext in ("*.md", "*.txt", "*.pdf", "*.docx"):
        out.extend(sorted(input_path.rglob(ext)))
    return out


def split_sentences(text: str) -> list[str]:
    parts = SENT_END.split(text)
    return [p.strip() for p in parts if p.strip()]


def split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in PARA_SPLIT.split(text) if p.strip()]


def tokenize(text: str) -> list[str]:
    return HE_TOKEN.findall(text)


def hebrew_ratio(text: str) -> float:
    he = len(HEBREW_RANGE.findall(text))
    return he / max(len(text), 1)


def stdev(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    mean = sum(xs) / len(xs)
    var = sum((x - mean) ** 2 for x in xs) / (len(xs) - 1)
    return math.sqrt(var)


def length_distribution(lengths: list[int]) -> dict:
    n = max(len(lengths), 1)
    buckets = {"under_10": 0, "10_20": 0, "20_30": 0, "30_40": 0, "over_40": 0}
    for L in lengths:
        if L < 10: buckets["under_10"] += 1
        elif L < 20: buckets["10_20"] += 1
        elif L < 30: buckets["20_30"] += 1
        elif L < 40: buckets["30_40"] += 1
        else: buckets["over_40"] += 1
    return {k: round(v / n, 4) for k, v in buckets.items()}


def compute_metrics(texts: list[str]) -> dict:
    full = "\n\n".join(texts)
    sents = []
    for t in texts:
        sents.extend(split_sentences(t))
    paras = []
    for t in texts:
        paras.extend(split_paragraphs(t))

    sent_word_counts = []
    first_words = []
    openers = []
    passive_hits = 0
    fp_hits = 0
    total_words = 0
    all_words: list[str] = []

    for s in sents:
        toks = tokenize(s)
        if not toks:
            continue
        sent_word_counts.append(len(toks))
        first_words.append(toks[0])
        opener = " ".join(toks[:3])
        openers.append(opener)
        for w in toks:
            all_words.append(w)
            if PASSIVE_PREFIX.match(w):
                passive_hits += 1
            if w in FIRST_PERSON_TOKENS:
                fp_hits += 1
            total_words += 1

    para_word_counts: list[int] = []
    sentences_per_para: list[int] = []
    for p in paras:
        ptoks = tokenize(p)
        para_word_counts.append(len(ptoks))
        sentences_per_para.append(len(split_sentences(p)))

    if not sent_word_counts:
        return {"error": "no sentences detected — empty or non-Hebrew input"}

    mean_sent = sum(sent_word_counts) / len(sent_word_counts)
    sent_sd = stdev([float(x) for x in sent_word_counts])
    burstiness = round(sent_sd / mean_sent, 3) if mean_sent else 0.0

    word_lengths = [len(w) for w in all_words]
    type_token_ratio = round(len(set(all_words)) / max(len(all_words), 1), 4)
    avg_word_len = round(sum(word_lengths) / max(len(word_lengths), 1), 2)

    first_word_counter = Counter(first_words).most_common(15)
    opener_counter = Counter(openers).most_common(15)
    content_words = [w for w in all_words if len(w) >= 3]
    top_content = Counter(content_words).most_common(20)

    return {
        "version": "0.3.0",
        "extractedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputCharCount": len(full),
        "hebrewRatio": round(hebrew_ratio(full), 3),
        "sentenceLevel": {
            "length": {
                "mean": round(mean_sent, 2),
                "stdev": round(sent_sd, 2),
                "min": min(sent_word_counts),
                "max": max(sent_word_counts),
            },
            "distribution": length_distribution(sent_word_counts),
            "passiveVoiceFrequency": round(passive_hits / max(total_words, 1), 4),
            "firstPersonFrequency": round(fp_hits / max(total_words, 1), 4),
            "topFirstWords": [{"word": w, "count": c} for w, c in first_word_counter],
            "topOpeners": [{"opener": o, "count": c} for o, c in opener_counter],
            "burstiness_score": burstiness,
        },
        "vocabulary": {
            "typeTokenRatio": type_token_ratio,
            "avgWordLength": avg_word_len,
            "topContentWords": [{"word": w, "count": c} for w, c in top_content],
            "totalTokens": total_words,
            "uniqueTokens": len(set(all_words)),
        },
        "paragraphStructure": {
            "length": {
                "mean": round(sum(para_word_counts) / max(len(para_word_counts), 1), 1),
                "stdev": round(stdev([float(x) for x in para_word_counts]), 1),
            },
            "sentencesPerParagraph": round(
                sum(sentences_per_para) / max(len(sentences_per_para), 1), 2
            ),
        },
        "chapterShape": {
            "wordCountMean": None,
            "wordCountStdev": None,
            "sceneToExpositionRatio": None,
            "narratorIntrusionFrequency": None,
        },
    }


def extract_baseline(baseline_md: Path) -> dict | None:
    """Pull the JSON code block from the `hebrew-style-fingerprint-baseline` chapter."""
    if not baseline_md.exists():
        return None
    text = baseline_md.read_text(encoding="utf-8", errors="replace")
    # Find the chapter section. The CandleKeep book wraps each chapter in
    # a comment marker `<!-- chapter: hebrew-style-fingerprint-baseline -->`.
    marker = "<!-- chapter: 08-style-fingerprint-baseline -->"
    if marker not in text:
        return None
    after = text.split(marker, 1)[1]
    m = re.search(r"```json\s*(\{.*?\})\s*```", after, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def contrastive(metrics: dict, baseline: dict) -> dict:
    """Produce a deviation report relative to baseline. Conservative — only emit fields that exist in both."""
    out: dict = {}
    sl = metrics.get("sentenceLevel", {})
    bsl = baseline.get("sentenceLevel", {}) or {}

    def deviation(actual: float | None, mean: float | None, sd: float | None) -> dict | None:
        if actual is None or mean is None or sd in (None, 0):
            return None
        z = (actual - mean) / sd
        if abs(z) < 0.5:
            cls = "typical"
        elif abs(z) < 1.5:
            cls = "above" if z > 0 else "below"
        else:
            cls = "well_above" if z > 0 else "well_below"
        return {"deviation": round(z, 2), "classification": cls}

    bl = bsl.get("length", {})
    out["sentenceLength"] = deviation(
        sl.get("length", {}).get("mean"),
        bl.get("mean"),
        bl.get("stdev"),
    )
    return {k: v for k, v in out.items() if v is not None}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="Path to a file or a directory of text/md/pdf/docx files.")
    p.add_argument("--output", required=True, help="Path to write the JSON fingerprint.")
    p.add_argument("--baseline", help="Path to .ctx/hebrew-linguistic-reference.md for contrastive analysis.")
    args = p.parse_args()

    in_path = Path(args.input).expanduser()
    if not in_path.exists():
        print(f"ERROR: input path not found: {in_path}", file=sys.stderr)
        sys.exit(1)

    files = collect_files(in_path)
    if not files:
        print(f"ERROR: no readable files at {in_path}", file=sys.stderr)
        sys.exit(1)

    texts = []
    for f in files:
        try:
            t = load_text(f)
            if t.strip():
                texts.append(t)
        except Exception as e:
            print(f"WARN: skipping {f}: {e}", file=sys.stderr)

    if not texts:
        print("ERROR: no text content extracted.", file=sys.stderr)
        sys.exit(1)

    fingerprint = compute_metrics(texts)
    fingerprint["filesAnalyzed"] = [str(f) for f in files]

    if args.baseline:
        bl = extract_baseline(Path(args.baseline).expanduser())
        if bl:
            fingerprint["contrastive"] = contrastive(fingerprint, bl)
            fingerprint["baselineVersion"] = bl.get("version")

    out_path = Path(args.output).expanduser()
    out_path.write_text(json.dumps(fingerprint, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_path} ({fingerprint.get('vocabulary',{}).get('totalTokens', 0)} tokens analysed across {len(files)} files).")


if __name__ == "__main__":
    main()
