"""Tests for merge_changes_per_chunk.py."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
MERGER = REPO_ROOT / "plugins/hebrew-book-producer/scripts/merge_changes_per_chunk.py"


def _write_chunk_changes(path: Path, chapter: str, before: str, after: str) -> None:
    sys.path.insert(0, str(REPO_ROOT / "plugins/hebrew-book-producer/scripts"))
    from changes_id import compute_change_id
    data = {
        "agent": "linguistic-editor",
        "chapter": chapter,
        "changes": [
            {
                "change_id": compute_change_id(f"chapters/{chapter}.md", 1, before),
                "file": f"chapters/{chapter}.md",
                "line_start": 1,
                "type": "word",
                "before": before,
                "after": after,
                "rationale": "test",
            }
        ],
    }
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_merger_concatenates_changes_from_all_chunks(tmp_path: Path) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    _write_chunk_changes(chunks_dir / "ch01.changes.json", "ch01", "המחשבות", "המחשבה")
    _write_chunk_changes(chunks_dir / "ch02.changes.json", "ch02", "האנשים", "האדם")

    out = tmp_path / "merged.json"
    result = subprocess.run(
        [
            sys.executable,
            str(MERGER),
            "--chunks-dir",
            str(chunks_dir),
            "--out",
            str(out),
            "--agent",
            "linguistic-editor",
            "--run-id",
            "20260503-test",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    merged = json.loads(out.read_text(encoding="utf-8"))
    assert merged["agent"] == "linguistic-editor"
    assert merged["run_id"] == "20260503-test"
    assert merged["chapter"] == "ALL"
    assert len(merged["changes"]) == 2
    chapters = {c["file"] for c in merged["changes"]}
    assert chapters == {"chapters/ch01.md", "chapters/ch02.md"}


def test_merger_backfills_missing_change_id(tmp_path: Path) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    legacy = {
        "agent": "linguistic-editor",
        "chapter": "ch01",
        "changes": [
            {
                "file": "chapters/ch01.md",
                "line_start": 1,
                "type": "word",
                "before": "א",
                "after": "ב",
                "rationale": "test",
            }
        ],
    }
    (chunks_dir / "ch01.changes.json").write_text(
        json.dumps(legacy, ensure_ascii=False), encoding="utf-8"
    )

    out = tmp_path / "merged.json"
    result = subprocess.run(
        [
            sys.executable,
            str(MERGER),
            "--chunks-dir",
            str(chunks_dir),
            "--out",
            str(out),
            "--agent",
            "linguistic-editor",
            "--run-id",
            "20260503-test",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    merged = json.loads(out.read_text(encoding="utf-8"))
    assert "change_id" in merged["changes"][0]
    assert len(merged["changes"][0]["change_id"]) == 12
