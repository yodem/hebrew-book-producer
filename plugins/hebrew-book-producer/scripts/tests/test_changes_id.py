"""Tests for changes_id.compute_change_id — must be stable across calls."""
from __future__ import annotations
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "plugins/hebrew-book-producer/scripts"))
from changes_id import compute_change_id  # noqa: E402


def test_same_inputs_produce_same_id() -> None:
    a = compute_change_id("chapters/ch01.md", 42, "המחשבות")
    b = compute_change_id("chapters/ch01.md", 42, "המחשבות")
    assert a == b


def test_different_before_produces_different_id() -> None:
    a = compute_change_id("chapters/ch01.md", 42, "המחשבות")
    b = compute_change_id("chapters/ch01.md", 42, "מחשבות")
    assert a != b


def test_id_is_12_hex_chars() -> None:
    cid = compute_change_id("chapters/ch01.md", 42, "המחשבות")
    assert len(cid) == 12
    int(cid, 16)


def test_different_file_produces_different_id() -> None:
    a = compute_change_id("chapters/ch01.md", 42, "x")
    b = compute_change_id("chapters/ch02.md", 42, "x")
    assert a != b


def test_handles_unicode() -> None:
    cid = compute_change_id("chapters/ch01.md", 1, "שלום עולם 🌍")
    assert len(cid) == 12
