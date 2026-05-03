# Foundation + Parallel Lector — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single-shot 20-minute `lector` agent with a splitter + N parallel Sonnet readers + 1 Opus synthesizer. Ship the shared manuscript splitter and CandleKeep instruction loader that all later plans depend on.

**Architecture:** A deterministic splitter normalizes any input form (`.docx`, `.md`, folder) into `.book-producer/chunks/chXX.md` plus `manuscript-index.json`. `/lector <file>` calls the splitter, spawns one `lector-reader` Sonnet sub-agent per chunk in parallel (each loads role-specific instructions from CandleKeep on demand), then runs one `lector-synthesizer` Opus sub-agent that reads the readers' note JSONs (never the raw manuscript) and produces `LECTOR_REPORT.md`.

**Tech Stack:** Bash + pandoc (splitter), `ck` CLI (CandleKeep), `yq` (YAML parsing), Claude Code `Agent` tool (sub-agent spawning), Python (split-chunk emission, JSON I/O), `bats` (bash test runner — install via `brew install bats-core` if absent), `pytest` (Python tests).

**Spec reference:** `docs/superpowers/specs/2026-05-02-parallel-lector-and-docx-suggestions-design.md` § Components 1–2.

**Plugin root:** `plugins/hebrew-book-producer/`.

---

## File Structure

```
plugins/hebrew-book-producer/
├── scripts/
│   ├── split-manuscript.sh            (NEW — bash entrypoint, dispatches to python)
│   ├── split_manuscript.py            (NEW — splitting algorithm)
│   ├── load-agent-instructions.sh     (NEW — per-agent CandleKeep loader)
│   └── tests/
│       ├── test_split_manuscript.py   (NEW — pytest)
│       └── test_load_agent_instructions.bats (NEW — bats)
├── agents/
│   ├── lector-reader.md               (NEW — Sonnet, parallel)
│   ├── lector-synthesizer.md          (NEW — Opus, single)
│   └── lector-legacy.md               (RENAMED from agents/lector.md, kept as escape hatch)
├── commands/
│   └── lector.md                      (REWRITTEN — splitter → parallel readers → synthesizer)
└── PIPELINE.md                        (MODIFIED — replace lector contract with three new agents)

docs/superpowers/specs/
└── 2026-05-02-parallel-lector-and-docx-suggestions-design.md   (already exists)

(per-project, written at runtime — NOT committed)
.book-producer/
├── manuscript.md
├── manuscript-index.json
├── chunks/chXX.md
└── chapter-notes/chXX.json
```

**File responsibilities:**
- `split-manuscript.sh` — argument parsing, format detection, calls Python for the actual split.
- `split_manuscript.py` — chunking algorithm, index emission. Pure function: input file → chunks dir + index JSON.
- `load-agent-instructions.sh` — given an agent key, looks up the CandleKeep ID from `book.yaml`, fetches and caches under `.ctx/`. Idempotent; safe under parallel invocation.
- `agents/lector-reader.md` — frontmatter + checklist for one chunk reader. Sonnet model.
- `agents/lector-synthesizer.md` — frontmatter + checklist for the verdict synthesizer. Opus model.
- `commands/lector.md` — orchestration: pre-flight, splitter call, parallel reader spawn, synthesizer spawn, summary to user.

---

## Pre-Flight (Task 0)

### Task 0: Verify environment

**Files:** none (verification only)

- [ ] **Step 1: Verify pandoc is installed**

Run: `pandoc --version | head -1`
Expected: `pandoc 3.x.x` or higher.
If missing: tell the user `brew install pandoc` and stop. Pandoc is required by every later task.

- [ ] **Step 2: Verify yq is installed**

Run: `yq --version`
Expected: `yq (https://github.com/mikefarah/yq/) version v4.x.x` or `mikefarah/yq` (Go-based).
If missing or wrong fork (e.g. Python `yq`): tell the user `brew install yq` (Mike Farah's Go version). The `yq '.foo.bar'` syntax used later assumes the Go version.

- [ ] **Step 3: Verify ck CLI is installed and authenticated**

Run: `ck items list 2>&1 | head -3`
Expected: A table header beginning with `ID` and `Title`.
If missing: tell the user to install ck per CandleKeep docs and run `ck auth login`. Stop until fixed.

- [ ] **Step 4: Verify bats and pytest are available**

Run: `which bats && python3 -c "import pytest; print(pytest.__version__)"`
Expected: Both print versions.
If missing: `brew install bats-core` and `pip3 install pytest`.

- [ ] **Step 5: Confirm working directory**

Run: `pwd && git status`
Expected: `/Users/yotamfromm/dev/hebrew-book-producer` and `On branch main` (or a feature branch).

---

## Task 1: Splitter — folder input mode (TDD)

**Files:**
- Create: `plugins/hebrew-book-producer/scripts/split_manuscript.py`
- Test: `plugins/hebrew-book-producer/scripts/tests/test_split_manuscript.py`

**Why folder mode first:** It's the simplest case (no parsing, no pandoc) — perfect for establishing the index schema and CLI shape.

- [ ] **Step 1: Write the failing test**

Create `plugins/hebrew-book-producer/scripts/tests/test_split_manuscript.py`:

```python
"""Tests for split_manuscript.py — manuscript splitter."""
from __future__ import annotations
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SPLITTER = REPO_ROOT / "plugins/hebrew-book-producer/scripts/split_manuscript.py"


def run_splitter(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SPLITTER), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def test_folder_input_emits_one_chunk_per_file(tmp_path: Path) -> None:
    src = tmp_path / "chapters"
    src.mkdir()
    (src / "ch01.md").write_text("# פרק 1\n\nשלום.\n", encoding="utf-8")
    (src / "ch02.md").write_text("# פרק 2\n\nעולם.\n", encoding="utf-8")
    (src / "ch03.md").write_text("# פרק 3\n\nתחילה.\n", encoding="utf-8")

    result = run_splitter(str(src), "--out", str(tmp_path / ".book-producer"), cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    out = tmp_path / ".book-producer"
    assert (out / "manuscript.md").is_file()
    assert (out / "manuscript-index.json").is_file()
    chunks = sorted((out / "chunks").iterdir())
    assert [c.name for c in chunks] == ["ch01.md", "ch02.md", "ch03.md"]

    idx = json.loads((out / "manuscript-index.json").read_text(encoding="utf-8"))
    assert idx["source_format"] == "folder"
    assert idx["split_strategy"] == "folder"
    assert len(idx["chunks"]) == 3
    assert idx["chunks"][0]["id"] == "ch01"
    assert idx["chunks"][0]["title"] == "פרק 1"
    assert idx["chunks"][0]["word_count"] >= 1
    assert idx["chunks"][0]["path"].endswith("chunks/ch01.md")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /Users/yotamfromm/dev/hebrew-book-producer && python3 -m pytest plugins/hebrew-book-producer/scripts/tests/test_split_manuscript.py -v`
Expected: FAIL with `FileNotFoundError` or `ModuleNotFoundError` (splitter does not yet exist).

- [ ] **Step 3: Write the minimal implementation**

Create `plugins/hebrew-book-producer/scripts/split_manuscript.py`:

```python
#!/usr/bin/env python3
"""Manuscript splitter — produces .book-producer/chunks/ + manuscript-index.json.

Usage:
    split_manuscript.py <input> [--out <dir>]

Where <input> is one of:
    - a folder of .md files (one per chapter, sorted by filename)
    - a .md file (later tasks)
    - a .docx file (later tasks)
"""
from __future__ import annotations
import argparse
import json
import re
import shutil
import sys
from pathlib import Path


SCHEMA_VERSION = "1.0"


def _first_heading_or_filename(md_text: str, fallback: str) -> str:
    for line in md_text.splitlines():
        m = re.match(r"^#+\s+(.*\S)\s*$", line)
        if m:
            return m.group(1).strip()
    return fallback


def _word_count(text: str) -> int:
    return len(text.split())


def split_folder(src: Path, out: Path) -> dict:
    chunks_dir = out / "chunks"
    if chunks_dir.exists():
        shutil.rmtree(chunks_dir)
    chunks_dir.mkdir(parents=True)

    md_files = sorted(p for p in src.iterdir() if p.suffix == ".md")
    if not md_files:
        sys.exit(f"no .md files in {src}")

    chunks: list[dict] = []
    cumulative_offset = 0
    full_md_parts: list[str] = []

    for i, src_path in enumerate(md_files, start=1):
        chunk_id = f"ch{i:02d}"
        text = src_path.read_text(encoding="utf-8")
        title = _first_heading_or_filename(text, src_path.stem)
        chunk_path = chunks_dir / f"{chunk_id}.md"
        chunk_path.write_text(text, encoding="utf-8")

        chunks.append(
            {
                "id": chunk_id,
                "title": title,
                "path": str(chunk_path.relative_to(out.parent)),
                "start_offset": cumulative_offset,
                "end_offset": cumulative_offset + len(text),
                "word_count": _word_count(text),
                "heading_level": 1,
                "source_filename": src_path.name,
            }
        )
        cumulative_offset += len(text) + 1  # +1 for joining newline
        full_md_parts.append(text)

    (out / "manuscript.md").write_text("\n".join(full_md_parts), encoding="utf-8")

    return {
        "$schema_version": SCHEMA_VERSION,
        "source_file": str(src),
        "source_format": "folder",
        "split_strategy": "folder",
        "chunks": chunks,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", help="folder of .md, single .md, or .docx")
    p.add_argument(
        "--out",
        default=".book-producer",
        help="output directory (default: .book-producer)",
    )
    args = p.parse_args()

    src = Path(args.input)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if src.is_dir():
        index = split_folder(src, out)
    else:
        sys.exit("non-folder inputs implemented in later tasks")

    (out / "manuscript-index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote {len(index['chunks'])} chunks to {out / 'chunks'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Run: `chmod +x plugins/hebrew-book-producer/scripts/split_manuscript.py`

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd /Users/yotamfromm/dev/hebrew-book-producer && python3 -m pytest plugins/hebrew-book-producer/scripts/tests/test_split_manuscript.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/yotamfromm/dev/hebrew-book-producer
git add plugins/hebrew-book-producer/scripts/split_manuscript.py plugins/hebrew-book-producer/scripts/tests/test_split_manuscript.py
git commit -m "feat(splitter): folder-input mode with index emission"
```

If the commit-guard hook blocks the commit, run `git status` to see what it asks for, fix, and retry. Do NOT use `--no-verify`.

---

## Task 2: Splitter — single .md with heading detection

**Files:**
- Modify: `plugins/hebrew-book-producer/scripts/split_manuscript.py`
- Modify: `plugins/hebrew-book-producer/scripts/tests/test_split_manuscript.py`

- [ ] **Step 1: Write the failing test**

Append to `test_split_manuscript.py`:

```python
def test_single_md_splits_by_hebrew_chapter_headings(tmp_path: Path) -> None:
    src = tmp_path / "manuscript.md"
    src.write_text(
        "# פרק 1: התחלה\n\nשלום עולם.\n\n"
        "# פרק 2: המשך\n\nכאן ממשיכים.\n\n"
        "# פרק 3: סיום\n\nוסיימנו.\n",
        encoding="utf-8",
    )

    result = run_splitter(str(src), "--out", str(tmp_path / ".book-producer"), cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    out = tmp_path / ".book-producer"
    chunks = sorted((out / "chunks").iterdir())
    assert [c.name for c in chunks] == ["ch01.md", "ch02.md", "ch03.md"]

    idx = json.loads((out / "manuscript-index.json").read_text(encoding="utf-8"))
    assert idx["source_format"] == "md"
    assert idx["split_strategy"] == "headings"
    assert idx["chunks"][0]["title"] == "פרק 1: התחלה"
    assert idx["chunks"][1]["title"] == "פרק 2: המשך"


def test_single_md_falls_back_to_wordcount_when_no_headings(tmp_path: Path) -> None:
    src = tmp_path / "manuscript.md"
    src.write_text("מילה " * 8000, encoding="utf-8")  # 8000 words, no headings

    result = run_splitter(str(src), "--out", str(tmp_path / ".book-producer"), cwd=tmp_path)
    assert result.returncode == 0, result.stderr

    idx = json.loads((tmp_path / ".book-producer/manuscript-index.json").read_text(encoding="utf-8"))
    assert idx["split_strategy"] == "wordcount"
    # 8000 words / ~3000 per chunk → 3 chunks (last may be smaller)
    assert 2 <= len(idx["chunks"]) <= 4
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest plugins/hebrew-book-producer/scripts/tests/test_split_manuscript.py -v`
Expected: The two new tests FAIL with `SystemExit: non-folder inputs implemented in later tasks`. Folder test still passes.

- [ ] **Step 3: Implement single-md splitting**

Replace the `else: sys.exit(...)` branch in `main()` with:

```python
    if src.is_dir():
        index = split_folder(src, out)
    elif src.suffix.lower() == ".md":
        index = split_md(src, out)
    else:
        sys.exit(f"unsupported input: {src} (expected folder or .md)")
```

Add these helpers above `main()`:

```python
HEBREW_HEADING_RE = re.compile(
    r"^(#{1,3}\s+.*|פרק\s+\S+.*|חלק\s+\S+.*|Chapter\s+\S+.*|Part\s+\S+.*)\s*$"
)
WORDCOUNT_TARGET = 3000


def _detect_heading_offsets(text: str) -> list[tuple[int, str]]:
    """Return [(offset, title), ...] for each heading line found."""
    offsets = []
    pos = 0
    for line in text.splitlines(keepends=True):
        stripped = line.rstrip("\n")
        if HEBREW_HEADING_RE.match(stripped):
            title = re.sub(r"^#+\s+", "", stripped).strip()
            offsets.append((pos, title))
        pos += len(line)
    return offsets


def split_md(src: Path, out: Path) -> dict:
    chunks_dir = out / "chunks"
    if chunks_dir.exists():
        shutil.rmtree(chunks_dir)
    chunks_dir.mkdir(parents=True)

    text = src.read_text(encoding="utf-8")
    (out / "manuscript.md").write_text(text, encoding="utf-8")

    headings = _detect_heading_offsets(text)
    if len(headings) >= 2:
        return _split_by_headings(text, headings, src, out, chunks_dir)
    return _split_by_wordcount(text, src, out, chunks_dir)


def _split_by_headings(
    text: str, headings: list[tuple[int, str]], src: Path, out: Path, chunks_dir: Path
) -> dict:
    chunks = []
    for i, (start, title) in enumerate(headings):
        end = headings[i + 1][0] if i + 1 < len(headings) else len(text)
        chunk_id = f"ch{i + 1:02d}"
        chunk_text = text[start:end]
        chunk_path = chunks_dir / f"{chunk_id}.md"
        chunk_path.write_text(chunk_text, encoding="utf-8")
        chunks.append(
            {
                "id": chunk_id,
                "title": title,
                "path": str(chunk_path.relative_to(out.parent)),
                "start_offset": start,
                "end_offset": end,
                "word_count": _word_count(chunk_text),
                "heading_level": 1,
            }
        )
    return {
        "$schema_version": SCHEMA_VERSION,
        "source_file": str(src),
        "source_format": "md",
        "split_strategy": "headings",
        "chunks": chunks,
    }


def _split_by_wordcount(text: str, src: Path, out: Path, chunks_dir: Path) -> dict:
    paragraphs = text.split("\n\n")
    chunks = []
    buf: list[str] = []
    buf_words = 0
    chunk_idx = 1
    pos = 0
    chunk_start = 0

    def _emit_chunk():
        nonlocal chunk_idx, buf, buf_words, chunk_start
        chunk_text = "\n\n".join(buf)
        chunk_id = f"ch{chunk_idx:02d}"
        chunk_path = chunks_dir / f"{chunk_id}.md"
        chunk_path.write_text(chunk_text, encoding="utf-8")
        chunks.append(
            {
                "id": chunk_id,
                "title": f"Chunk {chunk_idx}",
                "path": str(chunk_path.relative_to(out.parent)),
                "start_offset": chunk_start,
                "end_offset": chunk_start + len(chunk_text),
                "word_count": buf_words,
                "heading_level": 0,
            }
        )
        chunk_idx += 1
        chunk_start += len(chunk_text) + 2  # +2 for the joining "\n\n"
        buf = []
        buf_words = 0

    for para in paragraphs:
        words = _word_count(para)
        if buf_words + words > WORDCOUNT_TARGET and buf:
            _emit_chunk()
        buf.append(para)
        buf_words += words

    if buf:
        _emit_chunk()

    return {
        "$schema_version": SCHEMA_VERSION,
        "source_file": str(src),
        "source_format": "md",
        "split_strategy": "wordcount",
        "chunks": chunks,
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest plugins/hebrew-book-producer/scripts/tests/test_split_manuscript.py -v`
Expected: All three tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/hebrew-book-producer/scripts/split_manuscript.py plugins/hebrew-book-producer/scripts/tests/test_split_manuscript.py
git commit -m "feat(splitter): single-md mode with heading + wordcount fallback"
```

---

## Task 3: Splitter — .docx input via pandoc

**Files:**
- Modify: `plugins/hebrew-book-producer/scripts/split_manuscript.py`
- Modify: `plugins/hebrew-book-producer/scripts/tests/test_split_manuscript.py`

- [ ] **Step 1: Write the failing test**

Append to `test_split_manuscript.py`:

```python
def test_docx_input_converts_via_pandoc_then_splits(tmp_path: Path) -> None:
    """Smoke test: produce a .docx from markdown via pandoc, then split it."""
    md_src = tmp_path / "manuscript.md"
    md_src.write_text(
        "# פרק 1: התחלה\n\nשלום.\n\n"
        "# פרק 2: סוף\n\nוסיימנו.\n",
        encoding="utf-8",
    )
    docx_src = tmp_path / "manuscript.docx"
    subprocess.run(
        ["pandoc", "-f", "markdown", "-t", "docx", str(md_src), "-o", str(docx_src)],
        check=True,
    )

    result = run_splitter(str(docx_src), "--out", str(tmp_path / ".book-producer"), cwd=tmp_path)
    assert result.returncode == 0, result.stderr

    idx = json.loads((tmp_path / ".book-producer/manuscript-index.json").read_text(encoding="utf-8"))
    assert idx["source_format"] == "docx"
    assert len(idx["chunks"]) == 2
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest plugins/hebrew-book-producer/scripts/tests/test_split_manuscript.py::test_docx_input_converts_via_pandoc_then_splits -v`
Expected: FAIL with `SystemExit: unsupported input`.

- [ ] **Step 3: Implement docx conversion**

In `split_manuscript.py`, replace the dispatch in `main()`:

```python
    if src.is_dir():
        index = split_folder(src, out)
    elif src.suffix.lower() == ".md":
        index = split_md(src, out)
    elif src.suffix.lower() == ".docx":
        index = split_docx(src, out)
    else:
        sys.exit(f"unsupported input: {src} (expected folder, .md, or .docx)")
```

Add `split_docx` above `main()`:

```python
import subprocess  # add at top of file if not present


def split_docx(src: Path, out: Path) -> dict:
    md_path = out / "manuscript.md"
    proc = subprocess.run(
        [
            "pandoc",
            "-f",
            "docx",
            "-t",
            "markdown",
            "--wrap=none",
            str(src),
            "-o",
            str(md_path),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        sys.exit(f"pandoc conversion failed: {proc.stderr}")

    # Reuse split_md, but force source_format to "docx"
    index = split_md(md_path, out)
    index["source_file"] = str(src)
    index["source_format"] = "docx"
    return index
```

Note: `split_md` rewrites `manuscript.md` from its argument; that's fine because we already wrote pandoc's output there. The path argument and the destination match.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m pytest plugins/hebrew-book-producer/scripts/tests/test_split_manuscript.py -v`
Expected: All four tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/hebrew-book-producer/scripts/split_manuscript.py plugins/hebrew-book-producer/scripts/tests/test_split_manuscript.py
git commit -m "feat(splitter): .docx input via pandoc"
```

---

## Task 4: Splitter — bash wrapper with confirmation prompt

**Files:**
- Create: `plugins/hebrew-book-producer/scripts/split-manuscript.sh`

The bash wrapper exists for two reasons: (a) commands invoke shell scripts more naturally than Python scripts, (b) confirmation UI is easier in bash.

- [ ] **Step 1: Write the wrapper**

Create `plugins/hebrew-book-producer/scripts/split-manuscript.sh`:

```bash
#!/usr/bin/env bash
# split-manuscript.sh — entry point for the manuscript splitter.
# Calls split_manuscript.py and prints a Hebrew confirmation summary.
#
# Usage:
#   split-manuscript.sh <input> [--out <dir>] [--quiet]
#
# Where <input> is a folder, .md, or .docx file.
# --quiet skips the post-split summary (used by orchestrator).

set -euo pipefail

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(dirname "$(dirname "$(realpath "$0")")")}"
SPLITTER_PY="${PLUGIN_ROOT}/scripts/split_manuscript.py"

if [ ! -x "${SPLITTER_PY}" ]; then
  echo "error: ${SPLITTER_PY} not found or not executable" >&2
  exit 2
fi

INPUT=""
OUT_DIR=".book-producer"
QUIET=0

while [ $# -gt 0 ]; do
  case "$1" in
    --out)
      OUT_DIR="$2"
      shift 2
      ;;
    --quiet)
      QUIET=1
      shift
      ;;
    -*)
      echo "unknown flag: $1" >&2
      exit 2
      ;;
    *)
      if [ -z "${INPUT}" ]; then
        INPUT="$1"
      else
        echo "unexpected positional arg: $1" >&2
        exit 2
      fi
      shift
      ;;
  esac
done

if [ -z "${INPUT}" ]; then
  echo "usage: split-manuscript.sh <input> [--out <dir>] [--quiet]" >&2
  exit 2
fi

python3 "${SPLITTER_PY}" "${INPUT}" --out "${OUT_DIR}"

if [ "${QUIET}" -eq 1 ]; then
  exit 0
fi

# Hebrew summary
N_CHUNKS=$(python3 -c "import json,sys; d=json.load(open('${OUT_DIR}/manuscript-index.json')); print(len(d['chunks']))")
STRATEGY=$(python3 -c "import json,sys; d=json.load(open('${OUT_DIR}/manuscript-index.json')); print(d['split_strategy'])")
echo "זיהיתי ${N_CHUNKS} פרקים (split: ${STRATEGY})."
echo "כדי לראות את הרשימה: cat ${OUT_DIR}/manuscript-index.json"
```

Run: `chmod +x plugins/hebrew-book-producer/scripts/split-manuscript.sh`

- [ ] **Step 2: Smoke-test the wrapper end-to-end**

```bash
TMP=$(mktemp -d)
mkdir "${TMP}/chapters"
printf '# פרק 1\n\nשלום.\n' > "${TMP}/chapters/ch01.md"
printf '# פרק 2\n\nעולם.\n' > "${TMP}/chapters/ch02.md"
( cd "${TMP}" && /Users/yotamfromm/dev/hebrew-book-producer/plugins/hebrew-book-producer/scripts/split-manuscript.sh chapters )
ls "${TMP}/.book-producer/chunks/"
rm -rf "${TMP}"
```

Expected output: A Hebrew line `זיהיתי 2 פרקים (split: folder).` and `chunks/` containing `ch01.md` and `ch02.md`.

- [ ] **Step 3: Commit**

```bash
git add plugins/hebrew-book-producer/scripts/split-manuscript.sh
git commit -m "feat(splitter): bash wrapper with Hebrew summary"
```

---

## Task 5: CandleKeep instruction loader (TDD)

**Files:**
- Create: `plugins/hebrew-book-producer/scripts/load-agent-instructions.sh`
- Test: `plugins/hebrew-book-producer/scripts/tests/test_load_agent_instructions.bats`

- [ ] **Step 1: Write the failing test**

Create `plugins/hebrew-book-producer/scripts/tests/test_load_agent_instructions.bats`:

```bash
#!/usr/bin/env bats
# Tests for load-agent-instructions.sh.

setup() {
  TMP="$(mktemp -d)"
  cd "${TMP}"
  REPO="/Users/yotamfromm/dev/hebrew-book-producer"
  LOADER="${REPO}/plugins/hebrew-book-producer/scripts/load-agent-instructions.sh"
  mkdir -p .ctx
}

teardown() {
  rm -rf "${TMP}"
}

@test "no book.yaml: warns and exits 0" {
  run bash "${LOADER}" lector_reader
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"no book.yaml"* ]] || [[ "${output}" == *"skipping"* ]]
}

@test "book.yaml without agent_instructions: warns and exits 0" {
  printf 'genre: philosophy\n' > book.yaml
  run bash "${LOADER}" lector_reader
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"skipping"* ]] || [[ "${output}" == *"no agent_instructions"* ]]
}

@test "cached file present: skips fetch (idempotent)" {
  printf 'agent_instructions:\n  lector_reader: "cmDOESNOTEXIST"\n' > book.yaml
  printf 'cached content\n' > .ctx/lector-reader-instructions.md
  before_mtime=$(stat -f %m .ctx/lector-reader-instructions.md 2>/dev/null || stat -c %Y .ctx/lector-reader-instructions.md)
  run bash "${LOADER}" lector_reader
  [ "${status}" -eq 0 ]
  after_mtime=$(stat -f %m .ctx/lector-reader-instructions.md 2>/dev/null || stat -c %Y .ctx/lector-reader-instructions.md)
  [ "${before_mtime}" -eq "${after_mtime}" ]
}

@test "valid id: fetches from CandleKeep and caches" {
  # Use a real, known-public CandleKeep ID — the writer's guide.
  printf 'agent_instructions:\n  test_role: "cmok9h0m10ahik30zt8yt0lt2"\n' > book.yaml
  run bash "${LOADER}" test_role
  [ "${status}" -eq 0 ]
  [ -s .ctx/test-role-instructions.md ]
  size=$(wc -c < .ctx/test-role-instructions.md)
  [ "${size}" -gt 100 ]
}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `bats plugins/hebrew-book-producer/scripts/tests/test_load_agent_instructions.bats`
Expected: All four tests FAIL (loader does not exist yet).

- [ ] **Step 3: Implement the loader**

Create `plugins/hebrew-book-producer/scripts/load-agent-instructions.sh`:

```bash
#!/usr/bin/env bash
# load-agent-instructions.sh — fetch a per-agent instruction page from CandleKeep.
#
# Usage: load-agent-instructions.sh <agent_key>
#
# Reads book.yaml -> agent_instructions.<agent_key>, fetches the CandleKeep
# page by ID, writes to .ctx/<agent-key-dashed>-instructions.md.
#
# No-op if:
#   - book.yaml is missing
#   - agent_instructions.<agent_key> is missing or null
#   - the cache file already exists (idempotent for parallel sub-agents)
#
# Fail-open: on CandleKeep error, write a stub and exit 0.

set -u

AGENT_KEY="${1:-}"
if [ -z "${AGENT_KEY}" ]; then
  echo "usage: load-agent-instructions.sh <agent_key>" >&2
  exit 2
fi

CACHE_NAME="${AGENT_KEY//_/-}-instructions.md"
CACHE_FILE=".ctx/${CACHE_NAME}"

if [ -f "${CACHE_FILE}" ]; then
  exit 0
fi

if [ ! -f book.yaml ]; then
  echo "WARN: no book.yaml in $(pwd); skipping ${AGENT_KEY}" >&2
  exit 0
fi

if ! command -v yq >/dev/null 2>&1; then
  echo "WARN: yq not installed; cannot read book.yaml" >&2
  exit 0
fi

INSTR_ID=$(yq ".agent_instructions.${AGENT_KEY} // \"\"" book.yaml 2>/dev/null | tr -d '"')

if [ -z "${INSTR_ID}" ] || [ "${INSTR_ID}" = "null" ]; then
  echo "WARN: no agent_instructions.${AGENT_KEY} in book.yaml; skipping" >&2
  exit 0
fi

mkdir -p .ctx

if ! command -v ck >/dev/null 2>&1; then
  echo "WARN: ck CLI not installed; writing stub for ${AGENT_KEY}" >&2
  cat > "${CACHE_FILE}" <<STUB
# ${AGENT_KEY} instructions — UNAVAILABLE

ck CLI is not installed; CandleKeep page \`${INSTR_ID}\` could not be fetched.
[UNVERIFIED — agent should fall back to general session-cached references]
STUB
  exit 0
fi

if ! ck items get "${INSTR_ID}" --no-session > "${CACHE_FILE}" 2>/dev/null; then
  echo "WARN: ck items get ${INSTR_ID} failed; writing stub" >&2
  cat > "${CACHE_FILE}" <<STUB
# ${AGENT_KEY} instructions — UNAVAILABLE

CandleKeep page \`${INSTR_ID}\` could not be fetched.
[UNVERIFIED — agent should fall back to general session-cached references]
STUB
  exit 0
fi

CHARS=$(wc -c < "${CACHE_FILE}" | tr -d ' ')
if [ "${CHARS}" -lt 50 ]; then
  echo "WARN: ${INSTR_ID} returned <50 chars; treating as unavailable" >&2
fi

exit 0
```

Run: `chmod +x plugins/hebrew-book-producer/scripts/load-agent-instructions.sh`

- [ ] **Step 4: Run the tests to verify they pass**

Run: `bats plugins/hebrew-book-producer/scripts/tests/test_load_agent_instructions.bats`
Expected: All four tests PASS. (The fourth requires network + ck auth — if your environment doesn't have it, that test should fail gracefully with the stub and still pass; if it errors, set `CK_OFFLINE=1` env-var support: out of scope for this task.)

If test 4 fails because of ck auth/network, document the prerequisite ("ck must be authenticated") and proceed. The first three tests are the critical correctness ones.

- [ ] **Step 5: Commit**

```bash
git add plugins/hebrew-book-producer/scripts/load-agent-instructions.sh plugins/hebrew-book-producer/scripts/tests/test_load_agent_instructions.bats
git commit -m "feat(loader): per-agent CandleKeep instruction loader"
```

---

## Task 6: Add `agent_instructions` block to `book.yaml` example/template

**Files:**
- Modify: `plugins/hebrew-book-producer/CLAUDE.md` (documentation update)
- Modify: `plugins/hebrew-book-producer/PIPELINE.md` (add reference)

- [ ] **Step 1: Add documentation to CLAUDE.md**

Open `plugins/hebrew-book-producer/CLAUDE.md` and add a new section after the existing "Where to look for what" table. Find the line `| What does Stephen King say about adverbs? | \`.ctx/writers-guide.md\` § Ch. 2 |` and after the entire table, add:

```markdown
## Agent-specific instructions (CandleKeep)

Per-agent operating instructions live in CandleKeep, not in the plugin source. This lets the author iterate on agent behavior without touching the plugin. Configure via `book.yaml`:

```yaml
agent_instructions:
  lector_reader: <candlekeep-page-id>
  lector_synthesizer: <candlekeep-page-id>
  literary_reader: <candlekeep-page-id>
  literary_synthesizer: <candlekeep-page-id>
  linguistic_editor: <candlekeep-page-id>
  proofreader: <candlekeep-page-id>
```

Each sub-agent loads its own page on session start via:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/load-agent-instructions.sh <agent_key>
```

The loader is idempotent — safe under parallel sub-agent invocation. If a key is missing or CandleKeep is unavailable, the loader writes a stub and the agent falls back to the session-cached references (`.ctx/writers-guide.md`, `.ctx/hebrew-linguistic-reference.md`).
```

- [ ] **Step 2: Verify the doc edit**

Run: `grep -n "Agent-specific instructions" plugins/hebrew-book-producer/CLAUDE.md`
Expected: A single line number, e.g. `163:## Agent-specific instructions (CandleKeep)`.

- [ ] **Step 3: Commit**

```bash
git add plugins/hebrew-book-producer/CLAUDE.md
git commit -m "docs(claude.md): document agent_instructions block in book.yaml"
```

---

## Task 7: Rename existing lector to lector-legacy

**Files:**
- Rename: `plugins/hebrew-book-producer/agents/lector.md` → `plugins/hebrew-book-producer/agents/lector-legacy.md`

The existing lector becomes the escape hatch for `/lector --no-split`. We keep it byte-for-byte identical so users can fall back if the new pipeline misbehaves.

- [ ] **Step 1: Rename the file**

```bash
git mv plugins/hebrew-book-producer/agents/lector.md plugins/hebrew-book-producer/agents/lector-legacy.md
```

- [ ] **Step 2: Update the frontmatter `name` and `description`**

Edit `plugins/hebrew-book-producer/agents/lector-legacy.md`. Replace:

```yaml
name: lector
description: One-shot manuscript appraisal (קריאת לקטור). Reads the full manuscript, returns a structured LECTOR_REPORT.md covering market fit, structural soundness, voice signal, and a go/no-go on each chapter. Runs ONCE per project, before any editing.
```

With:

```yaml
name: lector-legacy
description: Legacy single-shot manuscript appraisal. Use ONLY when /lector --no-split is invoked. Reads the entire manuscript in one pass; slow on long books. Prefer lector-reader + lector-synthesizer (parallel pipeline).
```

- [ ] **Step 3: Verify**

Run: `head -3 plugins/hebrew-book-producer/agents/lector-legacy.md`
Expected:
```
---
name: lector-legacy
description: Legacy single-shot manuscript appraisal. Use ONLY when /lector --no-split is invoked. ...
```

- [ ] **Step 4: Commit**

```bash
git add plugins/hebrew-book-producer/agents/lector-legacy.md
git commit -m "refactor(agents): rename lector to lector-legacy (escape hatch)"
```

---

## Task 8: Create `lector-reader` agent

**Files:**
- Create: `plugins/hebrew-book-producer/agents/lector-reader.md`

- [ ] **Step 1: Write the agent file**

Create `plugins/hebrew-book-producer/agents/lector-reader.md`:

```markdown
---
name: lector-reader
description: Reads ONE chunk of the manuscript and produces structured notes per the lector-reader-notes schema. Spawned in parallel by /lector. Does NOT produce a verdict — that is the lector-synthesizer's job. Read-only on the manuscript.
tools: Read, Grep, Glob, Write
model: sonnet
---

# Lector Reader Agent (קורא לקטור)

You read **one chunk** of a manuscript (typically one chapter) and produce a structured note JSON. You do not produce a verdict, and you do not see other chunks. The lector-synthesizer will combine your notes with those of your peers to produce the final `LECTOR_REPORT.md`.

## Mandatory session-start checklist

1. Read `${CLAUDE_PLUGIN_ROOT}/PIPELINE.md` (or `.ctx/PIPELINE.md` if cached).
2. Read globally-cached references (loaded by SessionStart hook):
   - `.ctx/writers-guide.md`
   - `.ctx/hebrew-linguistic-reference.md`
   - `.ctx/author-profile.md`
3. Load role-specific instructions from CandleKeep:
   ```bash
   bash ${CLAUDE_PLUGIN_ROOT}/scripts/load-agent-instructions.sh lector_reader
   ```
   Then `Read .ctx/lector-reader-instructions.md`. If the file is a stub (under 100 chars or contains `[UNVERIFIED`), proceed using only the session-cached references.
4. Read the assigned chunk file (`$CHUNK_PATH` provided in your spawn prompt).
5. Read `.book-producer/manuscript-index.json` to know your chunk's position in the book.

## Inputs (provided in your spawn prompt)

- `CHUNK_ID` — e.g. `ch03`. Used to name your output file.
- `CHUNK_PATH` — path to the chunk markdown, e.g. `.book-producer/chunks/ch03.md`.
- `INDEX_PATH` — path to `manuscript-index.json`.

## Output

Write **exactly one file**: `.book-producer/chapter-notes/<CHUNK_ID>.json`.

Schema:

```json
{
  "chunk_id": "ch03",
  "title": "<from index>",
  "structural_observations": "<1-3 sentences in Hebrew on chapter coherence>",
  "voice_alignment": "<1-2 sentences in Hebrew comparing prose to author-profile>",
  "ai_markers": [
    {"text": "<verbatim sentence>", "reason": "<why it reads as AI>"}
  ],
  "authorial_markers": [
    {"text": "<verbatim sentence>", "reason": "<why it reads authentic>"}
  ],
  "register_notes": "<1 sentence in Hebrew>",
  "specific_quotes": [
    {"offset_or_line": 1234, "text": "<quote>", "type": "ai|authorial|register-drift"}
  ],
  "concerns": ["<short Hebrew bullet>"],
  "strengths": ["<short Hebrew bullet>"]
}
```

Aim for 5–15 entries total across `ai_markers + authorial_markers + specific_quotes` — enough signal for the synthesizer, not so much that the synthesizer drowns.

## Hard rules

- **Read your chunk fully before writing.** No partial reads.
- **Quotes must be verbatim** — copy from the chunk; do not paraphrase. The synthesizer relies on exact strings to cite.
- **Hebrew prose throughout the JSON.** Field names are English; values are Hebrew.
- **One file out, one file only.** Do not write `LECTOR_REPORT.md` — that is the synthesizer's job.
- **Never write to `.book-producer/state.json`.**
- **No verdict.** Do not say "publishable" or "not publishable." Observations only.
```

- [ ] **Step 2: Verify**

Run: `head -8 plugins/hebrew-book-producer/agents/lector-reader.md`
Expected: Frontmatter with `name: lector-reader` and `model: sonnet`.

- [ ] **Step 3: Commit**

```bash
git add plugins/hebrew-book-producer/agents/lector-reader.md
git commit -m "feat(agents): add lector-reader (Sonnet, parallel chunk reader)"
```

---

## Task 9: Create `lector-synthesizer` agent

**Files:**
- Create: `plugins/hebrew-book-producer/agents/lector-synthesizer.md`

- [ ] **Step 1: Write the agent file**

Create `plugins/hebrew-book-producer/agents/lector-synthesizer.md`:

```markdown
---
name: lector-synthesizer
description: Reads chapter notes from the parallel lector-readers and produces the unified LECTOR_REPORT.md verdict. Sees notes only, never the raw manuscript. Single-instance, runs after all readers finish.
tools: Read, Grep, Glob, Write
model: opus
---

# Lector Synthesizer Agent (סנתזט לקטור)

You are the senior lector. You did not read the manuscript directly — your readers did. You read **their structured notes** and produce the final 7-section verdict in Hebrew.

## Mandatory session-start checklist

1. Read `${CLAUDE_PLUGIN_ROOT}/PIPELINE.md` (or `.ctx/PIPELINE.md` if cached).
2. Read globally-cached references:
   - `.ctx/writers-guide.md` — pay particular attention to Ch. 4 (Story First / Theme After), Ch. 8 (Non-Fiction Structure), Ch. 9 (Zinsser).
   - `.ctx/hebrew-linguistic-reference.md` — chapters `hebrew-author-register`, `hebrew-anti-ai-markers`, `hebrew-citation-conventions`.
   - `.ctx/author-profile.md`.
3. Load role-specific instructions from CandleKeep:
   ```bash
   bash ${CLAUDE_PLUGIN_ROOT}/scripts/load-agent-instructions.sh lector_synthesizer
   ```
   Then `Read .ctx/lector-synthesizer-instructions.md`. If stub, proceed using session-cached references and the section template below.
4. Read `.book-producer/manuscript-index.json`.
5. Read **every** file under `.book-producer/chapter-notes/`. If a chunk's note file is missing, surface that in section 7 ("Go / No-Go") as a quality concern but do not fail the run.

## Inputs (provided in your spawn prompt)

- `NOTES_DIR` — e.g. `.book-producer/chapter-notes/`.
- `INDEX_PATH` — e.g. `.book-producer/manuscript-index.json`.
- `OUT_PATH` — e.g. `LECTOR_REPORT.md` (project root).

## Output

Write **exactly one file**: `LECTOR_REPORT.md` at the project root, with these sections, in this order, in Hebrew:

### 1. תקציר (3 sentences max)
What this book is, who it is for, whether it is publishable as-is.

### 2. סוגה ומיצוב שוק
Genre placement (philosophy / autobiography / religious / popular-science). Comparable Israeli titles. Realistic audience size.

### 3. ניתוח מבני
- Does the table of contents tell a coherent story?
- Are chapter promises made and paid?
- Is there a single thesis or driving question?
- Where is the structure weakest?

### 4. ניתוח קולי
- Does the voice match `.ctx/author-profile.md`?
- Does the prose feel AI-generated? Cite specific sentences from the readers' `ai_markers`.
- Is the register (משלב) consistent?

### 5. צמתי כתיבה אנושיים מול AI
List 5–10 sentences from `ai_markers` and 5–10 from `authorial_markers`. **Quote verbatim from the readers' notes** — do not paraphrase.

### 6. המלצה לעריכה
- Stage gates needed: literary? linguistic? both?
- Estimated effort in גיליון דפוס (use word counts from `manuscript-index.json` ÷ 24,000 chars).
- Special concerns: niqqud? religious primary sources? sensitivity reading?

### 7. Go / No-Go
One of:
- **Go** — proceed to literary edit.
- **Go with major revisions** — author rewrites first, lector re-reads.
- **No-go** — fundamental problems; recommend killing the project or restarting from outline.

## Hard rules

- **Notes only.** You may `Read` the index and chapter notes. **Do NOT `Read` the chunks themselves** — the whole point of the parallel pipeline is that the synthesizer trusts the readers' notes.
- **Quote verbatim** when citing AI markers or authorial markers — the readers extracted these for you; do not invent new ones.
- **Be honest, not flattering.** The author hired you to tell them the truth.
- **Be specific.** Cite chunk IDs, page numbers, exact sentences.
- **Never write to `.book-producer/state.json`.**
- **One report per project.** The output path `LECTOR_REPORT.md` is fixed.
```

- [ ] **Step 2: Verify**

Run: `head -8 plugins/hebrew-book-producer/agents/lector-synthesizer.md`
Expected: Frontmatter with `name: lector-synthesizer` and `model: opus`.

- [ ] **Step 3: Commit**

```bash
git add plugins/hebrew-book-producer/agents/lector-synthesizer.md
git commit -m "feat(agents): add lector-synthesizer (Opus, single-instance verdict)"
```

---

## Task 10: Rewrite `/lector` command for parallel pipeline

**Files:**
- Modify: `plugins/hebrew-book-producer/commands/lector.md`

- [ ] **Step 1: Replace the command file**

Open `plugins/hebrew-book-producer/commands/lector.md` and replace its entire contents with:

```markdown
---
description: Run a manuscript appraisal (קריאת לקטור). Splits the manuscript, runs N parallel lector-readers (Sonnet), then a single lector-synthesizer (Opus). Outputs LECTOR_REPORT.md.
argument-hint: <manuscript-file-or-folder> [--no-split] [--resume]
---

# /lector — manuscript appraisal (parallel pipeline)

## Pre-flight

1. Verify `book.yaml` exists. If not — refuse and tell the user to run `/init` first.
2. Verify the argument file or folder exists.
3. The `SessionStart` hook normally caches `.ctx/writers-guide.md` etc. If `.ctx/writers-guide.md` is missing, fall back to `bash ${CLAUDE_PLUGIN_ROOT}/scripts/load-candlekeep-guide.sh`.

## Flag handling

- `--no-split` → invoke the legacy single-shot path: spawn `lector-legacy` agent on the entire manuscript. Skip splitter and synthesizer. Use this only when the parallel path misbehaves.
- `--resume` → if `.book-producer/chunks/` already exists, skip the splitter and reuse existing chunks. Useful for re-runs after fixing chunking.

## Parallel pipeline (default)

### Phase 0 — split

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/split-manuscript.sh "<argument>"
```

If a previous run left `.book-producer/chunks/` and the user did NOT pass `--resume`, the splitter will re-create the chunks (deterministic). If the user passed `--resume`, skip this step.

After splitting, parse `.book-producer/manuscript-index.json` to get the list of chunk IDs.

### Phase 1 — parallel lector-readers

Spawn one `lector-reader` agent **per chunk in a single message** (this is what causes Claude Code to run them concurrently). For each chunk in `manuscript-index.json` chunks[]:

Spawn the `lector-reader` agent with the prompt:

```
You are processing chunk <CHUNK_ID> of a parallel lector run.

Inputs:
  CHUNK_ID = <id>
  CHUNK_PATH = <path>
  INDEX_PATH = .book-producer/manuscript-index.json

Follow your session-start checklist exactly. Write your output to:
  .book-producer/chapter-notes/<CHUNK_ID>.json
```

**Concurrency cap:** if the index has more than 8 chunks, run in waves of 8. Read `splitter.max_parallel` from `book.yaml` if set; default 8.

Wait for all readers to return before proceeding.

### Phase 2 — synthesizer

Spawn **one** `lector-synthesizer` agent with the prompt:

```
You are synthesizing the lector verdict from all chapter notes.

Inputs:
  NOTES_DIR = .book-producer/chapter-notes/
  INDEX_PATH = .book-producer/manuscript-index.json
  OUT_PATH = LECTOR_REPORT.md

Follow your session-start checklist exactly. Read the chapter notes only — do NOT read the chunks themselves. Write your output to LECTOR_REPORT.md.
```

### Phase 3 — summarise to user

Read `LECTOR_REPORT.md`. Print a 5-line Hebrew summary in `.report.md` shape (per `PIPELINE.md`):

```
סוכן: lector-synthesizer
פרק: כל הספר — קריאת לקטור הסתיימה
שינויים: <N עמודי דוח>
שלב הבא: <Go|Go עם תיקונים מהותיים|No-Go>
הערה: <ההערה הראשונה ב-LECTOR_REPORT.md סעיף 7, OR "אין הערות">
```

Then recommend next action based on the verdict:

- If verdict is **Go** → `/edit`
- If verdict is **Go with major revisions** → describe what the author needs to fix first; do NOT auto-proceed.
- If verdict is **No-go** → describe why; offer to discuss before any further work.

## Hard rules

- **Do NOT write prose.** Lector is read-only on the manuscript.
- **Do NOT modify chapters/.** The splitter writes only under `.book-producer/`.
- **Always parallel-spawn readers in a single tool-use message.** Sequential `Agent` calls in separate messages run serially.
- If any reader returns malformed JSON, the synthesizer surfaces it as a quality concern in section 7 — do not fail the whole run.
```

- [ ] **Step 2: Verify the command parses**

Run: `head -5 plugins/hebrew-book-producer/commands/lector.md`
Expected: YAML frontmatter with the new `description` and `argument-hint`.

- [ ] **Step 3: Commit**

```bash
git add plugins/hebrew-book-producer/commands/lector.md
git commit -m "feat(commands): rewrite /lector for parallel splitter→readers→synthesizer pipeline"
```

---

## Task 11: Update PIPELINE.md to reflect new lector contract

**Files:**
- Modify: `plugins/hebrew-book-producer/PIPELINE.md`

- [ ] **Step 1: Replace the lector contract block**

Open `plugins/hebrew-book-producer/PIPELINE.md` and find the `### lector` section (around line 39). Replace the entire `### lector` table block (the 8-line table starting with `| Field | Value |`) with three new contract blocks:

```markdown
### lector-reader

| Field | Value |
|---|---|
| name | `lector-reader` |
| model | sonnet |
| tools | Read, Grep, Glob, Write |
| reads (input artefacts) | `.book-producer/chunks/<id>.md`, `.book-producer/manuscript-index.json`, `.ctx/writers-guide.md`, `.ctx/hebrew-linguistic-reference.md`, `.ctx/author-profile.md`, `.ctx/lector-reader-instructions.md` |
| writes (output artefacts) | `.book-producer/chapter-notes/<id>.json` (one per spawned instance) |
| emits (state transitions) | None — readers feed the synthesizer; no direct state mutation |
| hard rules | Read the assigned chunk fully; quote verbatim; one JSON out per instance; no verdict; never write `.book-producer/state.json` |

---

### lector-synthesizer

| Field | Value |
|---|---|
| name | `lector-synthesizer` |
| model | opus |
| tools | Read, Grep, Glob, Write |
| reads (input artefacts) | `.book-producer/chapter-notes/*.json`, `.book-producer/manuscript-index.json`, `.ctx/writers-guide.md`, `.ctx/hebrew-linguistic-reference.md`, `.ctx/author-profile.md`, `.ctx/lector-synthesizer-instructions.md` |
| writes (output artefacts) | `LECTOR_REPORT.md` (project root, 7 sections in Hebrew) |
| emits (state transitions) | None — lector is a one-shot gate, not a state-advancing agent |
| hard rules | Read notes only — do NOT read raw chunks; quote verbatim from readers' AI/authorial markers; honest not flattering; one report per project |

---

### lector-legacy (escape hatch)

| Field | Value |
|---|---|
| name | `lector-legacy` |
| model | opus |
| tools | Read, Grep, Glob |
| reads (input artefacts) | `chapters/*.md`, `book.yaml`, `.ctx/*` |
| writes (output artefacts) | `LECTOR_REPORT.md` |
| emits (state transitions) | None |
| hard rules | Use only via `/lector --no-split`. Slow on long manuscripts. |
```

- [ ] **Step 2: Verify**

Run: `grep -c "^### lector" plugins/hebrew-book-producer/PIPELINE.md`
Expected: `3` (one each for `lector-reader`, `lector-synthesizer`, `lector-legacy`).

- [ ] **Step 3: Commit**

```bash
git add plugins/hebrew-book-producer/PIPELINE.md
git commit -m "docs(pipeline): replace lector contract with reader+synthesizer+legacy"
```

---

## Task 12: End-to-end smoke test on a real book

**Files:** none (verification only)

This is a manual integration test. The author should run it before declaring Plan 1 done.

- [ ] **Step 1: Prepare a test manuscript**

Use a real book the author has. Create a small test manuscript if needed:

```bash
mkdir -p /tmp/lector-smoke/chapters
for i in $(seq 1 6); do
  cat > /tmp/lector-smoke/chapters/ch0${i}.md <<EOF
# פרק ${i}: כותרת לדוגמה

זהו פרק לדוגמה. המטרה היא לבדוק שהלקטור הופעל על מספר פרקים במקביל.
EOF
done
cd /tmp/lector-smoke
cat > book.yaml <<EOF
genre: philosophy
title: "ספר בדיקה"
agent_instructions:
  lector_reader: "<paste-page-id-or-leave-empty>"
  lector_synthesizer: "<paste-page-id-or-leave-empty>"
EOF
```

- [ ] **Step 2: Run the splitter standalone**

```bash
cd /tmp/lector-smoke
/Users/yotamfromm/dev/hebrew-book-producer/plugins/hebrew-book-producer/scripts/split-manuscript.sh chapters
ls .book-producer/chunks/
cat .book-producer/manuscript-index.json | python3 -m json.tool
```

Expected: 6 chunk files, well-formed JSON index with `source_format: "folder"`.

- [ ] **Step 3: Run `/lector chapters` from a Claude Code session**

Open Claude Code in `/tmp/lector-smoke`. Run `/lector chapters`.

Expected:
- One Hebrew confirmation line about N chapters detected.
- 6 lector-readers spawn in parallel (visible in the agent panel).
- Wall-clock from spawn to verdict: under 90 seconds for this trivial manuscript.
- A `LECTOR_REPORT.md` file appears in the project root with the 7 Hebrew sections.

- [ ] **Step 4: Run `/lector chapters --no-split` and confirm legacy path still works**

Same project, run with the flag. Expected: `lector-legacy` agent runs, single sequential pass, produces `LECTOR_REPORT.md`. Slower but functional.

- [ ] **Step 5: Run on a real long book and time it**

Pick the author's largest manuscript (the one that previously timed out at 20+ minutes). Run `/lector <file>`. Record wall-clock time.

Acceptance criterion: under 5 minutes wall-clock for any book up to ~14 chapters of ≤4000 words each. (The spec target is 3 min; 5 min is the must-pass threshold.)

If wall-clock exceeds 5 min, investigate:
- Are readers actually spawning in parallel? Check the Claude Code agent panel for concurrent activity.
- Is the synthesizer reading raw chunks instead of notes? Inspect its trace.
- Is one chunk so large it dominates? Lower `splitter.max_parallel` may help, or split that chunk further.

- [ ] **Step 6: Mark Plan 1 done in the project README or CHANGELOG**

```bash
cd /Users/yotamfromm/dev/hebrew-book-producer
# Append a CHANGELOG entry
cat >> CHANGELOG.md <<EOF

## [Unreleased]

### Added
- Parallel lector pipeline: splitter + N Sonnet readers + 1 Opus synthesizer.
- Manuscript splitter (\`scripts/split-manuscript.sh\`) supporting .docx, .md, and folder inputs.
- Per-agent CandleKeep instruction loader (\`scripts/load-agent-instructions.sh\`).
- \`agent_instructions\` block in \`book.yaml\` for per-role CandleKeep page IDs.

### Changed
- \`/lector\` now uses the parallel pipeline by default. Pass \`--no-split\` to force the legacy single-shot path.

### Renamed
- \`agents/lector.md\` → \`agents/lector-legacy.md\` (escape hatch).
EOF
git add CHANGELOG.md
git commit -m "docs(changelog): document parallel lector + foundation"
```

---

## Self-Review (run by the implementer before declaring Plan 1 done)

**1. Spec coverage:** Confirm each item in Components 1–2 of the spec has a task:

- Splitter — folder mode → Task 1 ✅
- Splitter — md mode + heading detection + wordcount fallback → Task 2 ✅
- Splitter — docx via pandoc → Task 3 ✅
- Splitter — bash wrapper + Hebrew confirmation → Task 4 ✅
- CandleKeep instruction loader → Task 5 ✅
- `agent_instructions` documentation → Task 6 ✅
- `lector-reader` agent → Task 8 ✅
- `lector-synthesizer` agent → Task 9 ✅
- `/lector` command rewrite → Task 10 ✅
- `lector-legacy` escape hatch → Task 7 ✅
- PIPELINE.md update → Task 11 ✅
- Smoke test → Task 12 ✅

**2. Placeholder scan:** No "TBD", "TODO", "implement later" anywhere. Every step has the actual command or code.

**3. Type consistency:**
- Schema field names match across `lector-reader.md` (output schema), `lector-synthesizer.md` (input from notes), and `split_manuscript.py` (`manuscript-index.json` shape). Specifically: `chunk_id`, `id`, `title`, `path`, `word_count`, `start_offset`, `end_offset` are spelled identically everywhere.
- Cache file naming: `lector_reader` (agent_key) → `lector-reader-instructions.md` (cache file). Confirm in Task 5 (loader uses `${AGENT_KEY//_/-}`) and Tasks 8/9 (agents read `.ctx/lector-reader-instructions.md` and `.ctx/lector-synthesizer-instructions.md`).

If any inconsistency surfaces during execution, fix it inline and update both the source and any test that depended on the old name.

---

## Acceptance Criteria for Plan 1

- [ ] All 12 tasks completed and committed.
- [ ] `pytest plugins/hebrew-book-producer/scripts/tests/` is green.
- [ ] `bats plugins/hebrew-book-producer/scripts/tests/` is green.
- [ ] `/lector` on a real 14-chapter manuscript completes in ≤5 minutes wall-clock.
- [ ] `/lector --no-split` on the same manuscript still produces a valid `LECTOR_REPORT.md` (slower).
- [ ] No agent except `production-manager` writes to `.book-producer/state.json` (verify by `grep`).
- [ ] CHANGELOG entry committed.
