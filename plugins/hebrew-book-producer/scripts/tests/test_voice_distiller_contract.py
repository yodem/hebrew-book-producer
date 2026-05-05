"""Contract test for voice-distiller agent (hebrew-book-producer port)."""
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
AGENT = REPO_ROOT / "plugins" / "hebrew-book-producer" / "agents" / "voice-distiller.md"


def test_distiller_exists():
    assert AGENT.is_file()


def test_distiller_frontmatter():
    text = AGENT.read_text()
    fm = yaml.safe_load(text.split("---")[1])
    assert fm["name"] == "voice-distiller"


def test_distiller_writes_author_voice():
    text = AGENT.read_text()
    assert "AUTHOR_VOICE.md" in text
    assert ".voice/interview" in text
    assert "fingerprint.md" in text


def test_distiller_states_section_structure():
    text = AGENT.read_text()
    for s in ("Core voice", "Terminology", "Academic-specific", "Non-fiction-book-specific"):
        assert s in text


def test_distiller_states_token_budget():
    text = AGENT.read_text()
    assert "2,000" in text or "2000" in text
    assert "5,000" in text or "5000" in text
