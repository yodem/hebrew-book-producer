"""Tests for render_suggestions_docx.py."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
from docx import Document

REPO_ROOT = Path(__file__).resolve().parents[4]
RENDERER = REPO_ROOT / "plugins/hebrew-book-producer/scripts/render_suggestions_docx.py"


def _changes_json(tmp_path: Path) -> Path:
    sys.path.insert(0, str(REPO_ROOT / "plugins/hebrew-book-producer/scripts"))
    from changes_id import compute_change_id

    chapter = "chapters/ch01.md"
    cid = compute_change_id(chapter, 1, "המחשבות")
    payload = {
        "agent": "linguistic-editor",
        "chapter": "ch01",
        "run_id": "20260503-120000",
        "changes": [
            {
                "change_id": cid,
                "file": chapter,
                "line_start": 1,
                "line_end": 1,
                "type": "word",
                "level": "word",
                "before": "המחשבות",
                "after": "המחשבה",
                "rationale": "register: literary-formal — singular fits the chapter",
            }
        ],
        "state_transition": {"chapter": "ch01", "next_stage": "proofread-1"},
        "summary": "תיקון אחד.",
    }
    cj = tmp_path / "changes.json"
    cj.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return cj


def test_renderer_produces_docx_with_tracked_change(tmp_path: Path) -> None:
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir()
    (chapters_dir / "ch01.md").write_text(
        "# פרק 1\n\nהמחשבות שלי על העולם.\n", encoding="utf-8"
    )
    cj = _changes_json(tmp_path)
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    result = subprocess.run(
        [
            sys.executable,
            str(RENDERER),
            "--changes",
            str(cj),
            "--source",
            str(chapters_dir),
            "--out",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    docx_path = out_dir / "ch01.suggestions.docx"
    assert docx_path.is_file()

    doc = Document(docx_path)
    body_xml = doc.element.body.xml
    assert "המחשבות" in body_xml
    assert "המחשבה" in body_xml
    assert "w:del" in body_xml
    assert "w:ins" in body_xml
    sys.path.insert(0, str(REPO_ROOT / "plugins/hebrew-book-producer/scripts"))
    from changes_id import compute_change_id
    cid = compute_change_id("chapters/ch01.md", 1, "המחשבות")
    assert f"chg_{cid}" in body_xml


def test_renderer_skips_unmatched_changes(tmp_path: Path) -> None:
    """If a change's `before` text doesn't appear in the chapter, log and skip."""
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir()
    (chapters_dir / "ch01.md").write_text("# פרק 1\n\nטקסט לא קשור.\n", encoding="utf-8")
    sys.path.insert(0, str(REPO_ROOT / "plugins/hebrew-book-producer/scripts"))
    from changes_id import compute_change_id
    payload = {
        "agent": "linguistic-editor",
        "chapter": "ch01",
        "changes": [
            {
                "change_id": compute_change_id("chapters/ch01.md", 1, "מילה_לא_קיימת"),
                "file": "chapters/ch01.md",
                "line_start": 1,
                "line_end": 1,
                "type": "word",
                "before": "מילה_לא_קיימת",
                "after": "אחרת",
                "rationale": "test",
            }
        ],
    }
    cj = tmp_path / "changes.json"
    cj.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    result = subprocess.run(
        [
            sys.executable,
            str(RENDERER),
            "--changes",
            str(cj),
            "--source",
            str(chapters_dir),
            "--out",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert (out_dir / "ch01.suggestions.docx").is_file()
    assert "skipped" in result.stderr.lower() or "no match" in result.stderr.lower()
