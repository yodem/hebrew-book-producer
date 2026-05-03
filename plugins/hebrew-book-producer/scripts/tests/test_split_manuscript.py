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
