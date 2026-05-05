"""Structural tests for the voice subsystem (hebrew-book-producer port)."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_author_voice_at_root_exists():
    assert (REPO_ROOT / "AUTHOR_VOICE.md").is_file()


def test_voice_dir_exists():
    assert (REPO_ROOT / ".voice").is_dir()
    assert (REPO_ROOT / ".voice" / ".gitkeep").is_file()


def test_voice_artifacts_gitignored():
    gi = (REPO_ROOT / ".gitignore").read_text()
    assert ".voice/*" in gi
    assert "!.voice/.gitkeep" in gi
