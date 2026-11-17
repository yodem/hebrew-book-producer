"""The `book` skill is a stage router; its "How to run" steps are ordered and rule 1 wins."""
import re
from pathlib import Path

ROUTER = Path(__file__).resolve().parent.parent / "skills" / "book" / "SKILL.md"


def _steps():
    text = ROUTER.read_text(encoding="utf-8")
    body = text.split("\n---\n", 1)[1].split("## How to run", 1)[1].split("\n## ", 1)[0]
    return {int(m.group(1)): m.group(2) for m in re.finditer(r"^(\d)\. (.*)$", body, re.M)}


def test_steps_in_order_and_rule_one_wins():
    s = _steps()
    assert sorted(s) == [1, 2, 3, 4, 5]
    assert "stage in the table" in s[1] and "wins over every rule below" in s[1]
    assert "No arguments at all" in s[2] and "`help`" in s[2]
    assert "single bare word" in s[3] and "print the table and stop" in s[3]
    assert "first word is not a stage" in s[4] and "infer the stage" in s[4] and "ask the author" in s[4]
    assert "Read exactly one file" in s[5]
    assert "print the table" not in s[4] and "infer" not in s[3]


def test_router_size_and_table_position():
    lines = ROUTER.read_text(encoding="utf-8").splitlines()
    assert len(lines) < 150
    assert next(i for i, l in enumerate(lines, 1) if l.strip() == "## Phases") <= 60
