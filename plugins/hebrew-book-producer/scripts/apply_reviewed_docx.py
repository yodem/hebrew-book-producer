#!/usr/bin/env python3
"""Round-trip a reviewed manuscript back into the canonical markdown.

Inputs:
  --reviewed-md   : path to a markdown file (typically pandoc's flatten of the
                    reviewed docx with --track-changes=accept).
  --changes       : path to the original changes.json (with change_id on every change).
  --canonical     : path to the canonical chapters/<id>.md to update in-place.
  --decisions-out : path to write the decision log JSON.

Algorithm (per change):
  - "after" appears in reviewed-md, "before" does not  -> accepted
  - "before" appears in reviewed-md, "after" does not  -> rejected
  - neither appears                                    -> modified (author tweaked)
  - both appear                                        -> ambiguous; treat as accepted

For modified changes, the script copies the reviewed-md wholesale into the
canonical file (the author's text is authoritative).

Novel edits are emitted as `[]` in the decision log for v1; v2 will diff
paragraph-by-paragraph against the canonical to detect them.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict


def classify_change(reviewed_text: str, before: str, after: str) -> str:
    has_after = bool(after) and after in reviewed_text
    has_before = bool(before) and before in reviewed_text
    if has_after and not has_before:
        return "accepted"
    if has_before and not has_after:
        return "rejected"
    if not has_after and not has_before:
        return "modified"
    return "accepted"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reviewed-md", required=True)
    p.add_argument("--changes", required=True)
    p.add_argument("--canonical", required=True)
    p.add_argument("--decisions-out", required=True)
    args = p.parse_args()

    reviewed = Path(args.reviewed_md).read_text(encoding="utf-8")
    payload = json.loads(Path(args.changes).read_text(encoding="utf-8"))
    canonical_path = Path(args.canonical)
    canonical = canonical_path.read_text(encoding="utf-8")

    accepted: List[str] = []
    rejected: List[str] = []
    modified: List[Dict] = []

    new_canonical = canonical
    for c in payload.get("changes", []):
        cid = c["change_id"]
        before = c.get("before", "")
        after = c.get("after", "")
        verdict = classify_change(reviewed, before, after)

        if verdict == "accepted":
            if before in new_canonical:
                new_canonical = new_canonical.replace(before, after, 1)
            accepted.append(cid)
        elif verdict == "rejected":
            rejected.append(cid)
        elif verdict == "modified":
            modified.append(
                {
                    "change_id": cid,
                    "original_before": before,
                    "original_after": after,
                }
            )

    if modified:
        new_canonical = reviewed

    canonical_path.write_text(new_canonical, encoding="utf-8")

    decisions = {
        "chapter": payload.get("chapter", canonical_path.stem),
        "run_id": payload.get("run_id"),
        "accepted": accepted,
        "rejected": rejected,
        "modified": modified,
        "novel_edits": [],
    }
    Path(args.decisions_out).write_text(
        json.dumps(decisions, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"applied: accepted={len(accepted)} rejected={len(rejected)} modified={len(modified)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
