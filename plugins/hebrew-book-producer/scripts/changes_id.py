"""Stable change_id hashing.

A change_id is a short hex hash of (file, line_start, before-text). It is stable
across re-runs: the same proposed edit produces the same ID. This is what lets
the docx renderer and the round-trip applier agree on which change is which,
without storing IDs in the docx as visible text.
"""
from __future__ import annotations
import hashlib


def compute_change_id(file: str, line_start: int, before: str) -> str:
    """Return a 12-char hex hash uniquely identifying a change."""
    raw = f"{file}\x1f{line_start}\x1f{before}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:12]
