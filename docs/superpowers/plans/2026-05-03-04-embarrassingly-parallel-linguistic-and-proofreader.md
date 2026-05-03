# Embarrassingly-Parallel Linguistic Editor + Proofreader — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Parallelize the linguistic editor and the proofreader by spawning N independent Sonnet agents — one per chunk — that each emit their own `changes.json`. No synthesizer needed because sentence/register/typo decisions are local; production-manager merges per-chunk outputs by concatenation.

**Architecture:** Reuse the existing `linguistic-editor` and `proofreader` agent definitions; only the orchestrator changes. The orchestrator (commands/edit.md, commands/proof.md) spawns N agents in parallel via the splitter's chunk list, each writes `.book-producer/runs/<run-id>/<agent>/<chunk-id>.changes.json`, and production-manager concatenates them into a single per-agent `changes.json` before invoking the docx renderer.

**Tech Stack:** No new dependencies. Reuses Plan 1's splitter and Plan 2's renderer.

**Spec reference:** `docs/superpowers/specs/2026-05-02-parallel-lector-and-docx-suggestions-design.md` § Component 4 table rows for `linguistic-editor` and `proofreader`.

**Depends on:** Plans 1, 2. Plan 3 is NOT a hard dependency, but in practice the linguistic stage runs after the literary stage so they ship together.

**Plugin root:** `plugins/hebrew-book-producer/`.

---

## File Structure

```
plugins/hebrew-book-producer/
├── agents/
│   ├── linguistic-editor.md        (MODIFIED — accepts CHUNK_ID/CHUNK_PATH inputs; emits change_id)
│   └── proofreader.md              (MODIFIED — same)
├── commands/
│   ├── edit.md                     (MODIFIED — linguistic stage spawns N parallel)
│   └── proof.md                    (MODIFIED — proofreader spawns N parallel)
├── scripts/
│   ├── merge_changes_per_chunk.py  (NEW — concatenates per-chunk changes.json into one)
│   └── tests/
│       └── test_merge_changes_per_chunk.py (NEW)
└── PIPELINE.md                     (MODIFIED — linguistic-editor and proofreader rows note parallel mode)
```

**File responsibilities:**
- `merge_changes_per_chunk.py` — given a directory of `<chunk-id>.changes.json` files, produces one merged `changes.json` with all change objects concatenated. Pure function. Computes `change_id` if missing (backfill).
- `commands/edit.md` linguistic stage and `commands/proof.md` — orchestrate N-way parallel spawn.
- `agents/linguistic-editor.md` and `agents/proofreader.md` — minimal modification: accept `CHUNK_PATH` instead of (or in addition to) the legacy "process the whole chapter" mode; require `change_id` on every emitted change.

---

## Pre-Flight (Task 0)

### Task 0: Verify dependencies

- [ ] **Step 1: Confirm Plans 1 and 2 are merged**

Run: `ls plugins/hebrew-book-producer/scripts/split_manuscript.py plugins/hebrew-book-producer/scripts/changes_id.py plugins/hebrew-book-producer/scripts/render_suggestions_docx.py`
Expected: All three exist.

- [ ] **Step 2: Confirm existing agents exist**

Run: `ls plugins/hebrew-book-producer/agents/linguistic-editor.md plugins/hebrew-book-producer/agents/proofreader.md`
Expected: Both exist.

---

## Task 1: Per-chunk merge script (TDD)

**Files:**
- Create: `plugins/hebrew-book-producer/scripts/merge_changes_per_chunk.py`
- Test: `plugins/hebrew-book-producer/scripts/tests/test_merge_changes_per_chunk.py`

- [ ] **Step 1: Write the failing test**

Create `plugins/hebrew-book-producer/scripts/tests/test_merge_changes_per_chunk.py`:

```python
"""Tests for merge_changes_per_chunk.py."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MERGER = REPO_ROOT / "plugins/hebrew-book-producer/scripts/merge_changes_per_chunk.py"


def _write_chunk_changes(path: Path, chapter: str, before: str, after: str) -> None:
    sys.path.insert(0, str(REPO_ROOT / "plugins/hebrew-book-producer/scripts"))
    from changes_id import compute_change_id
    data = {
        "agent": "linguistic-editor",
        "chapter": chapter,
        "changes": [
            {
                "change_id": compute_change_id(f"chapters/{chapter}.md", 1, before),
                "file": f"chapters/{chapter}.md",
                "line_start": 1,
                "type": "word",
                "before": before,
                "after": after,
                "rationale": "test",
            }
        ],
    }
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_merger_concatenates_changes_from_all_chunks(tmp_path: Path) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    _write_chunk_changes(chunks_dir / "ch01.changes.json", "ch01", "המחשבות", "המחשבה")
    _write_chunk_changes(chunks_dir / "ch02.changes.json", "ch02", "האנשים", "האדם")

    out = tmp_path / "merged.json"
    result = subprocess.run(
        [
            sys.executable,
            str(MERGER),
            "--chunks-dir",
            str(chunks_dir),
            "--out",
            str(out),
            "--agent",
            "linguistic-editor",
            "--run-id",
            "20260503-test",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    merged = json.loads(out.read_text(encoding="utf-8"))
    assert merged["agent"] == "linguistic-editor"
    assert merged["run_id"] == "20260503-test"
    assert merged["chapter"] == "ALL"
    assert len(merged["changes"]) == 2
    chapters = {c["file"] for c in merged["changes"]}
    assert chapters == {"chapters/ch01.md", "chapters/ch02.md"}


def test_merger_backfills_missing_change_id(tmp_path: Path) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    # Write a changes.json WITHOUT change_id
    legacy = {
        "agent": "linguistic-editor",
        "chapter": "ch01",
        "changes": [
            {
                "file": "chapters/ch01.md",
                "line_start": 1,
                "type": "word",
                "before": "א",
                "after": "ב",
                "rationale": "test",
            }
        ],
    }
    (chunks_dir / "ch01.changes.json").write_text(
        json.dumps(legacy, ensure_ascii=False), encoding="utf-8"
    )

    out = tmp_path / "merged.json"
    result = subprocess.run(
        [
            sys.executable,
            str(MERGER),
            "--chunks-dir",
            str(chunks_dir),
            "--out",
            str(out),
            "--agent",
            "linguistic-editor",
            "--run-id",
            "20260503-test",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    merged = json.loads(out.read_text(encoding="utf-8"))
    assert "change_id" in merged["changes"][0]
    assert len(merged["changes"][0]["change_id"]) == 12
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /Users/yotamfromm/dev/hebrew-book-producer && python3 -m pytest plugins/hebrew-book-producer/scripts/tests/test_merge_changes_per_chunk.py -v`
Expected: FAIL — script does not exist.

- [ ] **Step 3: Implement**

Create `plugins/hebrew-book-producer/scripts/merge_changes_per_chunk.py`:

```python
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

    all_changes: list[dict] = []
    next_stage_seen: set[str] = set()

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

    # All chunks should agree on next_stage; if not, log
    if len(next_stage_seen) > 1:
        print(
            f"WARN: divergent next_stage across chunks: {next_stage_seen}",
            file=sys.stderr,
        )
    next_stage = next_stage_seen.pop() if next_stage_seen else None

    merged = {
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
    print(f"merged {len(all_changes)} changes from {len(files)} chunks → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Run: `chmod +x plugins/hebrew-book-producer/scripts/merge_changes_per_chunk.py`

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest plugins/hebrew-book-producer/scripts/tests/test_merge_changes_per_chunk.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/hebrew-book-producer/scripts/merge_changes_per_chunk.py plugins/hebrew-book-producer/scripts/tests/test_merge_changes_per_chunk.py
git commit -m "feat(merge): concatenate per-chunk changes.json with change_id backfill"
```

---

## Task 2: Update `linguistic-editor` agent for chunk-mode

**Files:**
- Modify: `plugins/hebrew-book-producer/agents/linguistic-editor.md`

The existing agent reads `chapters/<id>.md` and edits it in place. We change it to (a) accept a `CHUNK_PATH`, (b) emit changes to a per-chunk `changes.json` file rather than editing the source, and (c) require `change_id` on every change.

- [ ] **Step 1: Read the current agent**

Run: `cat plugins/hebrew-book-producer/agents/linguistic-editor.md`

- [ ] **Step 2: Modify the agent**

Open `plugins/hebrew-book-producer/agents/linguistic-editor.md`. Make these changes:

1. In the frontmatter `tools:` line, add `Write` if not present (we no longer use `Edit` to modify the manuscript directly).
2. In the description, add: "Runs in chunk-mode: one instance per chunk, spawned in parallel by `/edit linguistic`."
3. Replace the "Inputs" / read instructions section with:

```markdown
## Inputs (from spawn prompt)

- `CHUNK_ID` — e.g. `ch03`.
- `CHUNK_PATH` — e.g. `.book-producer/chunks/ch03.md`.
- `RUN_ID` — orchestrator-assigned timestamp.
- `OUT_PATH` — e.g. `.book-producer/runs/<RUN_ID>/linguistic-editor/ch03.changes.json`.

You read your assigned chunk only. You do NOT see other chunks. Cross-chunk concerns are out of your scope (the linguistic edit is local by design).
```

4. Replace the Output section with:

```markdown
## Output

Write **exactly one file**: `$OUT_PATH`.

Schema (per `skills/changes-schema/SKILL.md`):

```json
{
  "agent": "linguistic-editor",
  "chapter": "<CHUNK_ID>",
  "run_id": "<RUN_ID>",
  "changes": [
    {
      "change_id": "<12-char hex; compute via changes_id.py>",
      "file": "chapters/<CHUNK_ID>.md",
      "line_start": <int>,
      "line_end": <int>,
      "type": "word | sentence | register",
      "level": "word | sentence",
      "before": "<verbatim>",
      "after": "<proposed>",
      "rationale": "<short Hebrew>"
    }
  ],
  "state_transition": {"chapter": "<CHUNK_ID>", "next_stage": "proofread-1"},
  "summary": "<5-line Hebrew per PIPELINE.md report.md shape>"
}
```

**The `file` field references `chapters/<CHUNK_ID>.md` (the canonical path), not `.book-producer/chunks/<CHUNK_ID>.md`.** This is so the renderer and applier work against the canonical source after merge.

To compute `change_id`:

```bash
python3 -c "
import sys
sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/scripts')
from changes_id import compute_change_id
print(compute_change_id('chapters/<CHUNK_ID>.md', <line_start>, '<before>'))
"
```
```

5. Replace the "Hard rules" tail with:

```markdown
## Hard rules

- **Read your assigned chunk only.** Do not read other chunks.
- **Do NOT edit the manuscript.** You write `changes.json`; production-manager applies the merged result via the docx round-trip.
- **Every change MUST have `change_id`.** Compute via `changes_id.py`.
- **Voice wins over correctness.**
- **Never silently rewrite a paragraph.** Each change touches the smallest meaningful unit (word, phrase, sentence).
- **Never write to `.book-producer/state.json`.**
```

- [ ] **Step 3: Verify**

Run: `grep -c "CHUNK_PATH" plugins/hebrew-book-producer/agents/linguistic-editor.md`
Expected: `1` or more.

- [ ] **Step 4: Commit**

```bash
git add plugins/hebrew-book-producer/agents/linguistic-editor.md
git commit -m "feat(linguistic-editor): chunk-mode inputs + change_id required + no in-place edit"
```

---

## Task 3: Update `proofreader` agent for chunk-mode

**Files:**
- Modify: `plugins/hebrew-book-producer/agents/proofreader.md`

Same shape as Task 2.

- [ ] **Step 1: Apply equivalent changes to proofreader.md**

Make the same modifications as Task 2 but with these adjustments:
- The agent name in `agent` field of the output JSON is `proofreader`.
- The output path: `.book-producer/runs/<RUN_ID>/proofreader-pass1/<CHUNK_ID>.changes.json` (or `proofreader-pass2/...` for the second pass — the orchestrator passes the directory).
- The state transition `next_stage` depends on which pass: pass 1 → `typeset`; pass 2 → `done`. Pass through whatever the orchestrator instructs.
- Hard rules retain the existing two-passes-non-negotiable, niqqud-only-when-flagged rules.

- [ ] **Step 2: Verify**

Run: `grep -c "CHUNK_PATH" plugins/hebrew-book-producer/agents/proofreader.md`
Expected: `1` or more.

- [ ] **Step 3: Commit**

```bash
git add plugins/hebrew-book-producer/agents/proofreader.md
git commit -m "feat(proofreader): chunk-mode inputs + change_id required + no in-place edit"
```

---

## Task 4: Wire `/edit linguistic` for parallel spawn

**Files:**
- Modify: `plugins/hebrew-book-producer/commands/edit.md`

- [ ] **Step 1: Add the linguistic phase**

Open `plugins/hebrew-book-producer/commands/edit.md`. Find the "Phase: Linguistic + Proofreader" placeholder added in Plan 3 (or the equivalent linguistic section if Plan 3 was not yet implemented). Replace with:

```markdown
## Phase: Linguistic (parallel)

After the literary stage completes (or skipping straight here on `/edit linguistic`):

### 0 — splitter

Ensure `.book-producer/chunks/` exists (created by Plan 1's splitter). If not:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/split-manuscript.sh chapters/
```

### 1 — parallel linguistic-editors

Generate `RUN_ID` (e.g., `$(date -u +%Y%m%d-%H%M%S)`).

Spawn one `linguistic-editor` agent **per chunk in a single message**. For each chunk in `manuscript-index.json` chunks[], pass:

```
You are processing chunk <CHUNK_ID> for the linguistic edit.

Inputs:
  CHUNK_ID = <id>
  CHUNK_PATH = <path>
  RUN_ID = <run-id>
  OUT_PATH = .book-producer/runs/<run-id>/linguistic-editor/<CHUNK_ID>.changes.json

Follow your session-start checklist exactly.
```

Concurrency cap 8 (configurable via `splitter.max_parallel`). Wait for all to return.

### 2 — merge per-chunk outputs

```bash
RUN_ID=<the run-id>
mkdir -p .book-producer/runs/${RUN_ID}/linguistic-editor
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/merge_changes_per_chunk.py \
  --chunks-dir .book-producer/runs/${RUN_ID}/linguistic-editor/ \
  --out .book-producer/runs/${RUN_ID}/linguistic-editor/changes.json \
  --agent linguistic-editor \
  --run-id ${RUN_ID}
```

### 3 — render per-chapter docx

```bash
mkdir -p .book-producer/runs/${RUN_ID}/linguistic-editor/docx
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/render_suggestions_docx.py \
  --changes .book-producer/runs/${RUN_ID}/linguistic-editor/changes.json \
  --source chapters/ \
  --out .book-producer/runs/${RUN_ID}/linguistic-editor/docx/
```

### 4 — Hebrew summary to user

```
שלב לשוני: <N> שינויים מוצעים בכל הספר.
לסקירה ב-Word: chapters/chXX.suggestions.docx
המשך: לאחר שתסקרי, רוצי /apply לכל פרק.
```
```

- [ ] **Step 2: Commit**

```bash
git add plugins/hebrew-book-producer/commands/edit.md
git commit -m "feat(edit): linguistic stage spawns N parallel agents + merges + renders"
```

---

## Task 5: Wire `/proof` for parallel spawn

**Files:**
- Modify: `plugins/hebrew-book-producer/commands/proof.md`

- [ ] **Step 1: Read the existing proof command**

Run: `cat plugins/hebrew-book-producer/commands/proof.md`

- [ ] **Step 2: Replace the proofreader invocation with parallel spawn**

Open `plugins/hebrew-book-producer/commands/proof.md`. Replace the body (preserve frontmatter) with:

```markdown
# /proof — proofread (parallel)

## Pre-flight

1. Verify `book.yaml` and `chapters/` exist.
2. Determine pass: read `.book-producer/state.json`; if any chapter is at stage `typeset`, this is **pass 2**; otherwise **pass 1**.
3. Splitter: ensure `.book-producer/chunks/`. If absent:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/split-manuscript.sh chapters/
```

## Parallel pipeline

Generate `RUN_ID` (e.g., `$(date -u +%Y%m%d-%H%M%S)`).
Determine `PASS_DIR`: `proofreader-pass1` if pass 1, `proofreader-pass2` if pass 2.
Determine `NEXT_STAGE`: pass 1 → `typeset`, pass 2 → `done`.

Spawn one `proofreader` agent **per chunk in a single message**:

```
You are processing chunk <CHUNK_ID> for proofreading pass <PASS>.

Inputs:
  CHUNK_ID = <id>
  CHUNK_PATH = <path>
  RUN_ID = <run-id>
  PASS = <1 or 2>
  NEXT_STAGE = <typeset or done>
  OUT_PATH = .book-producer/runs/<run-id>/<PASS_DIR>/<CHUNK_ID>.changes.json

Follow your session-start checklist exactly. Two-passes are non-negotiable; this is pass <PASS>.
```

Concurrency cap 8. Wait for all to return.

## Merge

```bash
mkdir -p .book-producer/runs/${RUN_ID}/${PASS_DIR}
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/merge_changes_per_chunk.py \
  --chunks-dir .book-producer/runs/${RUN_ID}/${PASS_DIR}/ \
  --out .book-producer/runs/${RUN_ID}/${PASS_DIR}/changes.json \
  --agent proofreader \
  --run-id ${RUN_ID}
```

## Render docx

```bash
mkdir -p .book-producer/runs/${RUN_ID}/${PASS_DIR}/docx
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/render_suggestions_docx.py \
  --changes .book-producer/runs/${RUN_ID}/${PASS_DIR}/changes.json \
  --source chapters/ \
  --out .book-producer/runs/${RUN_ID}/${PASS_DIR}/docx/
```

## Hebrew summary

```
שלב הגהה (פסקה <PASS>): <N> תיקונים מוצעים.
לסקירה: chapters/chXX.suggestions.docx
המשך: /apply לכל פרק.
```

## Hard rules

- **Two passes are non-negotiable.** Pass 1 before typesetting; pass 2 after typesetting (run `/proof` again).
- **Idea-flags are NEVER auto-fixed.** They surface in the rendered docx as comments for human review.
- **Never write to `.book-producer/state.json`** — production-manager owns that file.
```

- [ ] **Step 3: Commit**

```bash
git add plugins/hebrew-book-producer/commands/proof.md
git commit -m "feat(proof): parallel proofreader (per-chunk) with merge + docx render"
```

---

## Task 6: Update PIPELINE.md

**Files:**
- Modify: `plugins/hebrew-book-producer/PIPELINE.md`

- [ ] **Step 1: Annotate the linguistic-editor and proofreader rows**

In `PIPELINE.md`, locate the `### linguistic-editor` and `### proofreader` blocks. In each:

1. Update `tools:` line to include `Write`.
2. In `reads`: change `chapters/<id>.md` to `.book-producer/chunks/<id>.md` (chunk-mode).
3. In `writes`: change "Edits `chapters/<id>.md` in place via `Edit`" to:
   - For linguistic-editor: `.book-producer/runs/<run-id>/linguistic-editor/<chunk-id>.changes.json`
   - For proofreader: `.book-producer/runs/<run-id>/proofreader-pass[1|2]/<chunk-id>.changes.json`
4. Update `hard rules` to add: "Runs in parallel chunk-mode (one instance per chunk); never edits the manuscript directly; every change must include `change_id`."

- [ ] **Step 2: Commit**

```bash
git add plugins/hebrew-book-producer/PIPELINE.md
git commit -m "docs(pipeline): linguistic + proofreader run in parallel chunk-mode"
```

---

## Task 7: End-to-end smoke test

- [ ] **Step 1: Reuse a test project from prior plans**

```bash
cd /tmp/lector-smoke   # or recreate per Plan 1 Task 12
```

Make sure `chapters/`, `book.yaml`, and `.book-producer/chunks/` exist.

- [ ] **Step 2: Run `/edit linguistic`**

Open Claude Code in the test project. Run `/edit linguistic`.

Expected:
- N `linguistic-editor` agents spawn in parallel (one per chunk).
- Each writes `.book-producer/runs/<RUN_ID>/linguistic-editor/chXX.changes.json`.
- After all return, `merge_changes_per_chunk.py` produces a single `changes.json` at `.book-producer/runs/<RUN_ID>/linguistic-editor/changes.json`.
- The renderer produces per-chapter `.suggestions.docx` files.
- Wall-clock: ≤2 minutes for 4 chunks of ≤4000 words each (linguistic is the cheapest stage).

- [ ] **Step 3: Validate merged changes.json**

```bash
RUN_ID=$(ls .book-producer/runs/ | tail -1)
python3 - <<EOF
import json
data = json.load(open('.book-producer/runs/${RUN_ID}/linguistic-editor/changes.json'))
assert data['agent'] == 'linguistic-editor'
assert data['chapter'] == 'ALL'
for c in data['changes']:
    assert 'change_id' in c, f"missing change_id: {c}"
    assert len(c['change_id']) == 12
print(f"validated {len(data['changes'])} linguistic changes")
EOF
```

Expected: A line confirming N validated changes.

- [ ] **Step 4: Run `/proof` (pass 1)**

```bash
# In Claude Code session
/proof
```

Expected:
- N `proofreader` agents spawn in parallel.
- A merged `changes.json` lands at `.book-producer/runs/<RUN_ID>/proofreader-pass1/changes.json`.
- Per-chapter docx files appear under that directory.
- Wall-clock: ≤2 minutes.

- [ ] **Step 5: Update CHANGELOG**

```bash
cd /Users/yotamfromm/dev/hebrew-book-producer
cat >> CHANGELOG.md <<'EOF'

## [Unreleased]

### Added
- Parallel linguistic editor: N Sonnet agents per chunk, no synthesizer (changes are local). Merged via merge_changes_per_chunk.py.
- Parallel proofreader: same shape, both pass 1 and pass 2.
- `merge_changes_per_chunk.py` utility: concatenates per-chunk changes.json files with change_id backfill.

### Changed
- `linguistic-editor` and `proofreader` agents now run in chunk-mode: they read `.book-producer/chunks/<id>.md` and write `.book-producer/runs/<run-id>/<agent>/<chunk-id>.changes.json` instead of editing the manuscript in place.
- `/edit linguistic` and `/proof` commands now spawn N parallel agents.

EOF
git add CHANGELOG.md
git commit -m "docs(changelog): document parallel linguistic + proofreader"
```

---

## Self-Review

**1. Spec coverage:**
- Embarrassingly-parallel linguistic-editor → Task 4 ✅
- Embarrassingly-parallel proofreader → Task 5 ✅
- No synthesizer (per the spec) → confirmed: merge is a deterministic concatenation
- Reuses splitter, change_id, renderer from Plans 1 and 2 → confirmed in tasks
- Per-chunk agents emit `change_id` → Tasks 2, 3 (agent rule), Task 1 (merge backfill safety net)

**2. Placeholder scan:** No "TBD"/"TODO". Where Task 5 says "(or the equivalent linguistic section if Plan 3 was not yet implemented)", that's a contingency phrasing — the implementer reads the actual file and decides. Acceptable.

**3. Type consistency:**
- Per-chunk file naming: `<CHUNK_ID>.changes.json` everywhere (Task 1 test, Task 2 OUT_PATH, Task 4 spawn prompt, Task 5 spawn prompt).
- Merged file naming: `changes.json` (no chunk prefix) — distinct from per-chunk files. Same name across orchestrator (Task 4 step 2), merger output (Task 1 implementation), renderer input (Task 4 step 3).
- `agent` field values: `linguistic-editor` and `proofreader` — match the existing PIPELINE.md and changes-schema enum.
- `next_stage` values: `proofread-1`, `typeset`, `done` — match PIPELINE.md verbatim list.

---

## Acceptance Criteria for Plan 4

- [ ] All 7 tasks completed and committed.
- [ ] `pytest plugins/hebrew-book-producer/scripts/tests/test_merge_changes_per_chunk.py` is green.
- [ ] `/edit linguistic` on a real multi-chapter book spawns N parallel agents and produces a merged `changes.json` with `change_id` on every entry.
- [ ] `/proof` on a real multi-chapter book runs in parallel; produces both pass-1 and pass-2 outputs cleanly.
- [ ] Per-chapter `.suggestions.docx` files render successfully.
- [ ] Round-trip via `/apply` (Plan 2) updates the canonical markdown for each chapter.
- [ ] Wall-clock for a 14-chapter book in linguistic stage ≤ 4 minutes; in proofreader stage ≤ 4 minutes.
- [ ] CHANGELOG entry committed.
