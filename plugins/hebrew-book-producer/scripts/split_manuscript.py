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
import subprocess
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
        cumulative_offset += len(text) + 1
        full_md_parts.append(text)

    (out / "manuscript.md").write_text("\n".join(full_md_parts), encoding="utf-8")

    return {
        "$schema_version": SCHEMA_VERSION,
        "source_file": str(src),
        "source_format": "folder",
        "split_strategy": "folder",
        "chunks": chunks,
    }


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
        chunk_start += len(chunk_text) + 2
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

    index = split_md(md_path, out)
    index["source_file"] = str(src)
    index["source_format"] = "docx"
    return index


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
    elif src.suffix.lower() == ".md":
        index = split_md(src, out)
    elif src.suffix.lower() == ".docx":
        index = split_docx(src, out)
    else:
        sys.exit(f"unsupported input: {src} (expected folder, .md, or .docx)")

    (out / "manuscript-index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote {len(index['chunks'])} chunks to {out / 'chunks'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
