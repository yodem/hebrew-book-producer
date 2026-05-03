"""Tests for apply_reviewed_docx.py — round-trip reviewed docx into markdown."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
APPLIER = REPO_ROOT / "plugins/hebrew-book-producer/scripts/apply_reviewed_docx.py"


def _make_reviewed_md(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "reviewed.md"
    p.write_text(content, encoding="utf-8")
    return p


def test_accepted_change_applied_to_canonical(tmp_path: Path) -> None:
    sys.path.insert(0, str(REPO_ROOT / "plugins/hebrew-book-producer/scripts"))
    from changes_id import compute_change_id

    canonical = tmp_path / "chapters" / "ch01.md"
    canonical.parent.mkdir()
    canonical.write_text("המחשבות שלי על העולם.", encoding="utf-8")

    cid = compute_change_id("chapters/ch01.md", 1, "המחשבות")
    payload = {
        "agent": "linguistic-editor",
        "chapter": "ch01",
        "run_id": "20260503-120000",
        "changes": [
            {
                "change_id": cid,
                "file": "chapters/ch01.md",
                "line_start": 1,
                "type": "word",
                "before": "המחשבות",
                "after": "המחשבה",
                "rationale": "register",
            }
        ],
    }
    cj = tmp_path / "changes.json"
    cj.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    reviewed = _make_reviewed_md(tmp_path, "המחשבה שלי על העולם.")

    result = subprocess.run(
        [
            sys.executable,
            str(APPLIER),
            "--reviewed-md",
            str(reviewed),
            "--changes",
            str(cj),
            "--canonical",
            str(canonical),
            "--decisions-out",
            str(tmp_path / "decisions.json"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert canonical.read_text(encoding="utf-8") == "המחשבה שלי על העולם."

    decisions = json.loads((tmp_path / "decisions.json").read_text(encoding="utf-8"))
    assert decisions["accepted"] == [cid]
    assert decisions["rejected"] == []
    assert decisions["modified"] == []


def test_rejected_change_keeps_original(tmp_path: Path) -> None:
    sys.path.insert(0, str(REPO_ROOT / "plugins/hebrew-book-producer/scripts"))
    from changes_id import compute_change_id

    canonical = tmp_path / "chapters" / "ch01.md"
    canonical.parent.mkdir()
    canonical.write_text("המחשבות שלי.", encoding="utf-8")

    cid = compute_change_id("chapters/ch01.md", 1, "המחשבות")
    payload = {
        "changes": [
            {
                "change_id": cid,
                "file": "chapters/ch01.md",
                "line_start": 1,
                "type": "word",
                "before": "המחשבות",
                "after": "המחשבה",
                "rationale": "register",
            }
        ]
    }
    cj = tmp_path / "changes.json"
    cj.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    reviewed = _make_reviewed_md(tmp_path, "המחשבות שלי.")

    result = subprocess.run(
        [
            sys.executable,
            str(APPLIER),
            "--reviewed-md",
            str(reviewed),
            "--changes",
            str(cj),
            "--canonical",
            str(canonical),
            "--decisions-out",
            str(tmp_path / "decisions.json"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert canonical.read_text(encoding="utf-8") == "המחשבות שלי."

    decisions = json.loads((tmp_path / "decisions.json").read_text(encoding="utf-8"))
    assert decisions["rejected"] == [cid]
    assert decisions["accepted"] == []


def test_modified_change_uses_authors_text(tmp_path: Path) -> None:
    sys.path.insert(0, str(REPO_ROOT / "plugins/hebrew-book-producer/scripts"))
    from changes_id import compute_change_id

    canonical = tmp_path / "chapters" / "ch01.md"
    canonical.parent.mkdir()
    canonical.write_text("המחשבות שלי.", encoding="utf-8")

    cid = compute_change_id("chapters/ch01.md", 1, "המחשבות")
    payload = {
        "changes": [
            {
                "change_id": cid,
                "file": "chapters/ch01.md",
                "line_start": 1,
                "type": "word",
                "before": "המחשבות",
                "after": "המחשבה",
                "rationale": "register",
            }
        ]
    }
    cj = tmp_path / "changes.json"
    cj.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    reviewed = _make_reviewed_md(tmp_path, "הרעיונות שלי.")

    result = subprocess.run(
        [
            sys.executable,
            str(APPLIER),
            "--reviewed-md",
            str(reviewed),
            "--changes",
            str(cj),
            "--canonical",
            str(canonical),
            "--decisions-out",
            str(tmp_path / "decisions.json"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert canonical.read_text(encoding="utf-8") == "הרעיונות שלי."

    decisions = json.loads((tmp_path / "decisions.json").read_text(encoding="utf-8"))
    assert len(decisions["modified"]) == 1
    assert decisions["modified"][0]["change_id"] == cid
