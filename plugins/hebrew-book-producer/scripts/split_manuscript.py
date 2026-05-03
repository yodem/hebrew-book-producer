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
