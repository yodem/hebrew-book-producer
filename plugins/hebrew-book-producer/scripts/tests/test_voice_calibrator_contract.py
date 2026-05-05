"""Contract test for voice-calibrator agent (hebrew-book-producer port)."""
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
AGENT = REPO_ROOT / "plugins" / "hebrew-book-producer" / "agents" / "voice-calibrator.md"


def test_calibrator_exists():
    assert AGENT.is_file()


def test_calibrator_frontmatter():
    text = AGENT.read_text()
    fm = yaml.safe_load(text.split("---")[1])
    assert fm["name"] == "voice-calibrator"


def test_calibrator_invoked_only_on_3_and_7():
    text = AGENT.read_text()
    assert "session 3" in text.lower() and "session 7" in text.lower()


def test_calibrator_runs_rule_coverage():
    text = AGENT.read_text()
    assert "rule coverage" in text.lower() or "rule-coverage" in text.lower()
    assert ".voice/audit.md" in text


def test_calibrator_three_questions():
    text = AGENT.read_text()
    # Three calibration questions
    assert "sound like you" in text.lower()
    assert "banned" in text.lower()
    assert ("wrong" in text.lower() and "missing" in text.lower())
