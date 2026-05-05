"""Contract test for voice-interviewer agent (hebrew-book-producer port)."""
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
AGENT = REPO_ROOT / "plugins" / "hebrew-book-producer" / "agents" / "voice-interviewer.md"
QUESTIONS = REPO_ROOT / "plugins" / "hebrew-book-producer" / "skills" / "voice" / "questions-non-fiction.md"


def test_voice_interviewer_exists():
    assert AGENT.is_file()


def test_voice_interviewer_frontmatter():
    text = AGENT.read_text()
    fm_end = text.index("\n---\n", 4)
    fm = yaml.safe_load(text[4:fm_end])
    assert fm["name"] == "voice-interviewer"
    for k in ("description", "tools", "model"):
        assert k in fm


def test_voice_interviewer_references_question_bank():
    text = AGENT.read_text()
    assert "questions-non-fiction.md" in text or "question bank" in text.lower()


def test_voice_interviewer_specifies_session_state():
    text = AGENT.read_text()
    assert ".voice/interview/" in text
    assert "resume" in text.lower()


def test_voice_interviewer_states_per_session_cap():
    text = AGENT.read_text()
    assert "12" in text and "18" in text  # soft floor and hard cap
