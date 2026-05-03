#!/usr/bin/env python3
"""Merge per-chunk changes.json files into a single agent-level changes.json.

Usage:
    merge_changes_per_chunk.py \
        --chunks-dir <dir-of-chXX.changes.json> \
        --out <merged.json> \
        --agent <linguistic-editor|proofreader> \
        --run-id <run-id>

Concatenates the `changes` arrays from every <chunk>.changes.json under
<chunks-dir>. Backfills `change_id` on any change object that lacks one.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Set

sys.path.insert(0, str(Path(__file__).resolve().parent))
from changes_id import compute_change_id  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--chunks-dir", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--agent", required=True)
    p.add_argument("--run-id", required=True)
    args = p.parse_args()

    chunks_dir = Path(args.chunks_dir)
    files = sorted(chunks_dir.glob("*.changes.json"))
    if not files:
        sys.exit(f"no .changes.json files in {chunks_dir}")

    all_changes: List[Dict] = []
    next_stage_seen: Set[str] = set()

    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        for c in data.get("changes", []):
            if "change_id" not in c:
                c["change_id"] = compute_change_id(
                    c.get("file", ""),
                    c.get("line_start", 0),
                    c.get("before", ""),
                )
            all_changes.append(c)
        st = data.get("state_transition", {}).get("next_stage")
        if st:
            next_stage_seen.add(st)

    if len(next_stage_seen) > 1:
        print(
            f"WARN: divergent next_stage across chunks: {next_stage_seen}",
            file=sys.stderr,
        )
    next_stage = next_stage_seen.pop() if next_stage_seen else None

    merged: Dict = {
        "agent": args.agent,
        "chapter": "ALL",
        "run_id": args.run_id,
        "changes": all_changes,
        "summary": f"merged from {len(files)} chunks; {len(all_changes)} changes",
    }
    if next_stage:
        merged["state_transition"] = {"chapter": "ALL", "next_stage": next_stage}

    Path(args.out).write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"merged {len(all_changes)} changes from {len(files)} chunks -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
