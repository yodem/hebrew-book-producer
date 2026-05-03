"""Tests for split_manuscript.py — manuscript splitter."""
from __future__ import annotations
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
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
    # 16 paragraphs × 500 words = 8000 words. Wordcount target is 3000,
    # so we expect ~2-3 chunks with paragraph boundaries respected.
    paragraph = ("מילה " * 500).strip()
    src.write_text("\n\n".join([paragraph] * 16), encoding="utf-8")

    result = run_splitter(str(src), "--out", str(tmp_path / ".book-producer"), cwd=tmp_path)
    assert result.returncode == 0, result.stderr

    idx = json.loads((tmp_path / ".book-producer/manuscript-index.json").read_text(encoding="utf-8"))
    assert idx["split_strategy"] == "wordcount"
    assert 2 <= len(idx["chunks"]) <= 4


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
