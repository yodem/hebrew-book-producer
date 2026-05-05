"""Contract test for voice-miner agent definition (hebrew-book-producer port)."""
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
AGENT = REPO_ROOT / "plugins" / "hebrew-book-producer" / "agents" / "voice-miner.md"


def test_voice_miner_agent_exists():
    assert AGENT.is_file()


def test_voice_miner_frontmatter_complete():
    text = AGENT.read_text()
    assert text.startswith("---\n")
    fm_end = text.index("\n---\n", 4)
    fm = yaml.safe_load(text[4:fm_end])
    for k in ("name", "description", "tools", "model"):
        assert k in fm, f"missing frontmatter key: {k}"
    assert fm["name"] == "voice-miner"


def test_voice_miner_specifies_io_contract():
    text = AGENT.read_text()
    assert "past-articles/" in text or "corpus" in text.lower()
    assert ".voice/fingerprint.md" in text
    assert "## Inputs" in text or "**Inputs**" in text
    assert "## Outputs" in text or "**Outputs**" in text
