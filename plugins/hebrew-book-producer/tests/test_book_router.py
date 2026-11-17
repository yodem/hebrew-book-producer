"""The `book` skill is a stage router; its rules 2 and 3 must be disjoint and ordered."""
import re
from pathlib import Path

ROUTER = Path(__file__).resolve().parent.parent / "skills" / "book" / "SKILL.md"


def _steps():
    text = ROUTER.read_text(encoding="utf-8")
    body = text.split("\n---\n", 1)[1]
    return {int(m.group(1)): m.group(2) for m in re.finditer(r"^(\d)\. (.*)$", body, re.M)}


def test_rules_exist_and_are_disjoint():
    s = _steps()
    r2, r3 = s[2], s[3]
    assert "more than one bare word" in r2 and "infer the stage" in r2 and "ask the author" in r2
    assert "single bare word" in r3 and "not in the table" in r3 and "print the table and stop" in r3
    assert "Never apply this rule to a sentence" in r3
    assert "print the table" not in r2
    assert "infer" not in r3
    assert "in this order" in r2.lower()


def test_router_size_and_table_position():
    lines = ROUTER.read_text(encoding="utf-8").splitlines()
    assert len(lines) < 150
    assert next(i for i, l in enumerate(lines, 1) if l.strip() == "## Phases") <= 60
