"""Contract test for voice SKILL.md (hebrew-book-producer port)."""
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / "plugins" / "hebrew-book-producer" / "skills" / "voice" / "SKILL.md"


def test_skill_exists():
    assert SKILL.is_file()


def test_skill_frontmatter_complete():
    text = SKILL.read_text()
    fm = yaml.safe_load(text.split("---")[1])
    assert fm["name"] == "voice"
    assert fm["user-invocable"] is True
    for k in ("description", "allowedTools"):
        assert k in fm


def test_skill_lists_subactions():
    text = SKILL.read_text()
    for sub in ("init", "continue", "recompress", "audit", "quick", "sync", "status"):
        assert f":voice {sub}" in text or f"`{sub}`" in text


def test_skill_invokes_correct_agents():
    text = SKILL.read_text()
    assert "voice-interviewer" in text
    assert "voice-distiller" in text
    assert "voice-calibrator" in text
    # Calibrator only on sessions 3 and 7
    assert "session 3" in text.lower() and "session 7" in text.lower()
