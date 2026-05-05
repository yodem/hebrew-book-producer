"""voice-migrate.sh end-to-end test (hebrew-book-producer port)."""
import subprocess
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT = REPO_ROOT / "plugins" / "hebrew-book-producer" / "skills" / "voice" / "voice-migrate.sh"
FIXTURE = REPO_ROOT / "plugins" / "hebrew-book-producer" / "scripts" / "tests" / "fixtures" / "voice" / "legacy-profile.json"


def test_migrate_via_academic_writer_profile(tmp_path):
    """Migration from a legacy .academic-writer/profile.json (Academic Helper layout)."""
    aw_dir = tmp_path / ".academic-writer"
    aw_dir.mkdir()
    (aw_dir / "profile.json").write_text(FIXTURE.read_text())
    r = subprocess.run([str(SCRIPT)], cwd=str(tmp_path), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    new = json.loads((aw_dir / "profile.json").read_text())
    # voice and style_fingerprint should be replaced with pointer comments
    assert isinstance(new.get("voice"), str) and "AUTHOR_VOICE.md" in new["voice"]
    assert "style_fingerprint" not in new or "AUTHOR_VOICE.md" in str(new["style_fingerprint"])
    assert new["writer_name"] == "Test Writer"
    # AUTHOR_VOICE.md should be at root and contain seeded content
    avo = (tmp_path / "AUTHOR_VOICE.md").read_text()
    assert "Test Writer" in avo
    assert "מבחינה זו" in avo
    # Legacy archive intact
    legacy = tmp_path / ".voice" / "legacy" / "profile.json"
    assert legacy.is_file()
    assert json.loads(legacy.read_text()) == json.loads(FIXTURE.read_text())
    # Idempotent
    r2 = subprocess.run([str(SCRIPT)], cwd=str(tmp_path), capture_output=True, text=True)
    assert r2.returncode == 0
    assert "already migrated" in (r2.stdout + r2.stderr).lower()


def test_migrate_hebrew_book_producer_legacy_author_voice(tmp_path):
    """Migration of a legacy AUTHOR_VOICE.md that lacks the four-section structure."""
    legacy_avo = tmp_path / "AUTHOR_VOICE.md"
    legacy_avo.write_text(
        "# Voice Profile — Test Author\n\nSome legacy content.\n"
    )
    r = subprocess.run([str(SCRIPT)], cwd=str(tmp_path), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    migrated = (tmp_path / "AUTHOR_VOICE.md").read_text()
    # Should now have the four-section structure
    assert "## Core voice" in migrated
    assert "## Terminology" in migrated
    assert "## Academic-specific" in migrated
    assert "## Non-fiction-book-specific" in migrated
    # Legacy archive should exist
    assert (tmp_path / ".voice" / "legacy" / "AUTHOR_VOICE.md").is_file()
    # Idempotent
    r2 = subprocess.run([str(SCRIPT)], cwd=str(tmp_path), capture_output=True, text=True)
    assert r2.returncode == 0
    assert "already migrated" in (r2.stdout + r2.stderr).lower()


def test_migrate_no_legacy_records_marker(tmp_path):
    """When there are no legacy artifacts, migrate exits 0 and records the marker."""
    r = subprocess.run([str(SCRIPT)], cwd=str(tmp_path), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    marker = tmp_path / ".voice" / ".migrated"
    assert marker.is_file()
    # Idempotent
    r2 = subprocess.run([str(SCRIPT)], cwd=str(tmp_path), capture_output=True, text=True)
    assert r2.returncode == 0
    assert "already migrated" in (r2.stdout + r2.stderr).lower()
