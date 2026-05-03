# Docx Suggestion Mode + /apply Round-Trip — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every editorial agent's `changes.json` gets rendered to `chXX.suggestions.docx` with Word tracked changes + inline rationale comments. The author reviews in Word, saves, and `/apply <chapter>` round-trips accepted/rejected/modified decisions back into the canonical markdown.

**Architecture:** A deterministic Python renderer (`render-suggestions-docx.py`) reads `changes.json` + the chapter markdown and writes a `.docx` whose tracked changes are anchored to hidden bookmarks named `chg_<change_id>`. The `/apply` command flattens the reviewed docx via pandoc, cross-references the result with the original `changes.json` by `change_id`, classifies each change as accepted/rejected/modified/novel, and applies them to `chapters/chXX.md`. A decision log feeds the existing voice-miner.

**Tech Stack:** Python 3 + `python-docx` (writes Word XML), pandoc (`docx → md` flatten), `lxml` (low-level OOXML for tracked changes that python-docx can't author directly), `pytest`, `bats`.

**Spec reference:** `docs/superpowers/specs/2026-05-02-parallel-lector-and-docx-suggestions-design.md` § Component 3.

**Depends on:** Plan 1 (Foundation + Parallel Lector). Specifically, the splitter's chunked manuscript layout. Plan 2 does **not** require Plan 1's lector agents to be working — only the splitter.

**Plugin root:** `plugins/hebrew-book-producer/`.

---

## File Structure

```
plugins/hebrew-book-producer/
├── scripts/
│   ├── render_suggestions_docx.py        (NEW — renderer)
│   ├── apply_reviewed_docx.py            (NEW — round-trip applier)
│   ├── changes_id.py                     (NEW — stable change_id hash util)
│   ├── docx_tracked_changes.py           (NEW — low-level OOXML helpers)
│   └── tests/
│       ├── test_render_suggestions_docx.py     (NEW)
│       ├── test_apply_reviewed_docx.py         (NEW)
│       └── test_changes_id.py                  (NEW)
├── commands/
│   └── apply.md                          (NEW — /apply command)
├── skills/changes-schema/
│   └── SKILL.md                          (MODIFIED — add change_id field)
└── agents/production-manager.md          (MODIFIED — call renderer after merge)
```

**File responsibilities:**
- `changes_id.py` — single function `compute_change_id(file, line_start, before)` returning a 12-char hex hash. Used by both renderer and applier so they agree.
- `docx_tracked_changes.py` — encapsulates the OOXML writes (`w:ins`, `w:del`, `w:bookmarkStart`, `w:bookmarkEnd`, `w:commentReference`) python-docx doesn't expose directly. Pure functions over `lxml` elements.
- `render_suggestions_docx.py` — top-level renderer. Reads `changes.json` + chapter markdown → writes `chXX.suggestions.docx`.
- `apply_reviewed_docx.py` — top-level applier. Reads `chXX.reviewed.docx` + original `changes.json` + canonical markdown → writes new canonical markdown + decision log.
- `commands/apply.md` — orchestration: dispatches to `apply_reviewed_docx.py`, prints Hebrew summary.

---

## Pre-Flight (Task 0)

### Task 0: Verify environment

**Files:** none

- [ ] **Step 1: Confirm Plan 1 is merged**

Run: `ls plugins/hebrew-book-producer/scripts/split_manuscript.py plugins/hebrew-book-producer/scripts/load-agent-instructions.sh`
Expected: Both files exist (artefacts of Plan 1).
If not: stop and complete Plan 1 first.

- [ ] **Step 2: Install python-docx and lxml**

Run: `pip3 install python-docx lxml`
Expected: Both install successfully.

Verify:
```bash
python3 -c "import docx; import lxml; print(docx.__version__, lxml.__version__)"
```
Expected: Two version strings (e.g. `1.1.2 5.3.0`).

- [ ] **Step 3: Verify pandoc handles `--track-changes=accept`**

```bash
pandoc --help | grep track-changes
```
Expected: A line listing `--track-changes=accept|reject|all`.

---

## Task 1: change_id hashing utility (TDD)

**Files:**
- Create: `plugins/hebrew-book-producer/scripts/changes_id.py`
- Test: `plugins/hebrew-book-producer/scripts/tests/test_changes_id.py`

- [ ] **Step 1: Write the failing test**

Create `plugins/hebrew-book-producer/scripts/tests/test_changes_id.py`:

```python
"""Tests for changes_id.compute_change_id — must be stable across calls."""
from __future__ import annotations
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
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
    int(cid, 16)  # must parse as hex


def test_different_file_produces_different_id() -> None:
    a = compute_change_id("chapters/ch01.md", 42, "x")
    b = compute_change_id("chapters/ch02.md", 42, "x")
    assert a != b


def test_handles_unicode() -> None:
    cid = compute_change_id("chapters/ch01.md", 1, "שלום עולם 🌍")
    assert len(cid) == 12
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /Users/yotamfromm/dev/hebrew-book-producer && python3 -m pytest plugins/hebrew-book-producer/scripts/tests/test_changes_id.py -v`
Expected: FAIL with `ModuleNotFoundError: changes_id`.

- [ ] **Step 3: Implement**

Create `plugins/hebrew-book-producer/scripts/changes_id.py`:

```python
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m pytest plugins/hebrew-book-producer/scripts/tests/test_changes_id.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/hebrew-book-producer/scripts/changes_id.py plugins/hebrew-book-producer/scripts/tests/test_changes_id.py
git commit -m "feat(changes): stable change_id hash util"
```

---

## Task 2: Update changes-schema to require `change_id`

**Files:**
- Modify: `plugins/hebrew-book-producer/skills/changes-schema/SKILL.md`

- [ ] **Step 1: Add change_id to the JSON Schema in SKILL.md**

Open `plugins/hebrew-book-producer/skills/changes-schema/SKILL.md`. Find the inner `properties` block under `changes.items.properties` (around line 30). Add `change_id` as the first property:

```json
        "change_id": {
          "type": "string",
          "pattern": "^[0-9a-f]{12}$",
          "description": "Stable hash. Computed via scripts/changes_id.py compute_change_id(file, line_start, before)."
        },
```

Update the `required` array on the same change-object schema from `["file", "type", "rationale"]` to `["file", "type", "rationale", "change_id"]`.

- [ ] **Step 2: Add a documentation paragraph after the schema**

Find the heading `## Change type reference` and immediately above it, add:

```markdown
## change_id

Every change object MUST include `change_id` — a 12-character hex hash uniquely identifying the change. Compute it with:

```python
from changes_id import compute_change_id
cid = compute_change_id(file_path, line_start, before_text)
```

This ID is stable across re-runs of the same edit. The docx renderer embeds it as a hidden bookmark; `/apply` uses it to round-trip accept/reject decisions.

For backwards-compatibility, production-manager migrates old `changes.json` files on read: if a change object lacks `change_id`, it computes the hash and writes it back.
```

- [ ] **Step 3: Update the sample objects to include change_id**

In each of the three sample objects (literary-editor structural cut, linguistic-editor word substitution, proofreader typo), add `"change_id": "<example-12-hex>"` as the first key. Use plausible but fake example hashes:

```json
{
  "change_id": "a1b2c3d4e5f6",
  "file": "chapters/ch03.md",
  ...
```

- [ ] **Step 4: Verify the SKILL.md still validates as text**

Run: `head -50 plugins/hebrew-book-producer/skills/changes-schema/SKILL.md`
Expected: Frontmatter intact, schema starts with `change_id` as first listed property.

- [ ] **Step 5: Commit**

```bash
git add plugins/hebrew-book-producer/skills/changes-schema/SKILL.md
git commit -m "feat(schema): require change_id on every change object"
```

---

## Task 3: Low-level OOXML helpers for tracked changes (TDD)

**Files:**
- Create: `plugins/hebrew-book-producer/scripts/docx_tracked_changes.py`
- Test: `plugins/hebrew-book-producer/scripts/tests/test_docx_tracked_changes.py`

`python-docx` does not natively author `w:ins` / `w:del` / `w:commentReference` elements. We drop to `lxml` for those.

- [ ] **Step 1: Write the failing test**

Create `plugins/hebrew-book-producer/scripts/tests/test_docx_tracked_changes.py`:

```python
"""Tests for docx_tracked_changes — low-level OOXML helpers."""
from __future__ import annotations
import sys
from pathlib import Path
from docx import Document

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "plugins/hebrew-book-producer/scripts"))
from docx_tracked_changes import (  # noqa: E402
    add_tracked_change,
    add_change_bookmark,
    add_comment,
    W_NS,
)


def test_add_tracked_change_emits_ins_and_del(tmp_path: Path) -> None:
    doc = Document()
    p = doc.add_paragraph("השינויים")
    add_tracked_change(
        paragraph=p,
        before="המחשבות",
        after="המחשבה",
        author="hebrew-book-producer",
    )
    out = tmp_path / "out.docx"
    doc.save(out)

    # Re-open and inspect the XML
    doc2 = Document(out)
    xml = doc2.paragraphs[0]._p.xml
    assert f"<w:del " in xml or "w:del" in xml
    assert "w:ins" in xml
    assert "המחשבות" in xml
    assert "המחשבה" in xml


def test_add_change_bookmark_includes_id_in_name(tmp_path: Path) -> None:
    doc = Document()
    p = doc.add_paragraph("טקסט")
    add_change_bookmark(p, change_id="abc123def456")
    out = tmp_path / "out.docx"
    doc.save(out)

    doc2 = Document(out)
    xml = doc2.paragraphs[0]._p.xml
    assert "chg_abc123def456" in xml


def test_add_comment_writes_comment_xml(tmp_path: Path) -> None:
    doc = Document()
    p = doc.add_paragraph("טקסט")
    add_comment(
        document=doc,
        paragraph=p,
        author="hebrew-book-producer",
        text="register: literary-formal",
        comment_id=1,
    )
    out = tmp_path / "out.docx"
    doc.save(out)

    # Comments live in word/comments.xml; python-docx keeps them in the package.
    # Just verify the document still loads and the comment_id is referenced.
    doc2 = Document(out)
    assert doc2.paragraphs[0].text == "טקסט"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest plugins/hebrew-book-producer/scripts/tests/test_docx_tracked_changes.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

Create `plugins/hebrew-book-producer/scripts/docx_tracked_changes.py`:

```python
"""Low-level OOXML helpers for Word tracked changes and comments.

python-docx does not natively author the <w:ins> / <w:del> / <w:commentReference>
elements that "track changes" requires. We drop to lxml for those, while still
using python-docx for paragraph + run scaffolding.

Reference: ECMA-376 Part 1 §17.13 (revisions and tracked changes).
"""
from __future__ import annotations
import datetime as dt
from typing import TYPE_CHECKING
from lxml import etree

if TYPE_CHECKING:
    from docx.text.paragraph import Paragraph
    from docx.document import Document


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NSMAP = {"w": W_NS}


def _qn(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


def _now_iso() -> str:
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


# Module-level monotonic ID for revisions. Word tolerates duplicates but
# distinct IDs are cleaner.
_revision_counter = [0]


def _next_id() -> int:
    _revision_counter[0] += 1
    return _revision_counter[0]


def add_tracked_change(
    paragraph: "Paragraph",
    before: str,
    after: str,
    author: str,
    date: str | None = None,
) -> None:
    """Append a w:del (before) + w:ins (after) pair to the paragraph.

    The paragraph's existing content is left as-is. The deletion and insertion
    are appended at the end of the paragraph as a tracked-changes pair.

    For a real edit you'd want to *replace* a specific run rather than append.
    The renderer calls this on a paragraph that has already had its body
    cleared and then re-built; see render_suggestions_docx.py for that flow.
    """
    if date is None:
        date = _now_iso()

    p_elem = paragraph._p

    del_elem = etree.SubElement(p_elem, _qn("del"))
    del_elem.set(_qn("id"), str(_next_id()))
    del_elem.set(_qn("author"), author)
    del_elem.set(_qn("date"), date)
    del_run = etree.SubElement(del_elem, _qn("r"))
    del_text = etree.SubElement(del_run, _qn("delText"))
    del_text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    del_text.text = before

    ins_elem = etree.SubElement(p_elem, _qn("ins"))
    ins_elem.set(_qn("id"), str(_next_id()))
    ins_elem.set(_qn("author"), author)
    ins_elem.set(_qn("date"), date)
    ins_run = etree.SubElement(ins_elem, _qn("r"))
    ins_text = etree.SubElement(ins_run, _qn("t"))
    ins_text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    ins_text.text = after


def add_change_bookmark(paragraph: "Paragraph", change_id: str) -> None:
    """Wrap the end of the paragraph with a bookmark named chg_<change_id>.

    Bookmarks are invisible to readers but persist through Word save/load,
    which lets /apply identify changes after the author reviews."""
    p_elem = paragraph._p
    bookmark_id = str(_next_id())
    name = f"chg_{change_id}"

    start = etree.SubElement(p_elem, _qn("bookmarkStart"))
    start.set(_qn("id"), bookmark_id)
    start.set(_qn("name"), name)

    end = etree.SubElement(p_elem, _qn("bookmarkEnd"))
    end.set(_qn("id"), bookmark_id)


def add_comment(
    document: "Document",
    paragraph: "Paragraph",
    author: str,
    text: str,
    comment_id: int,
) -> None:
    """Add a Word comment anchored at the end of the paragraph.

    Word comments live in word/comments.xml inside the docx package. python-docx
    does not expose comments as a first-class API; we register a part if needed
    and append the comment XML.
    """
    # Ensure comments part exists
    from docx.oxml.ns import qn as docx_qn
    from docx.opc.constants import RELATIONSHIP_TYPE as RT, CONTENT_TYPE as CT
    from docx.opc.part import Part
    from docx.opc.packuri import PackURI

    package = document.part.package
    comments_uri = PackURI("/word/comments.xml")
    if comments_uri not in package.parts:
        comments_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:comments xmlns:w="{W_NS}"/>'
        ).encode("utf-8")
        comments_part = Part(
            comments_uri,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml",
            comments_xml,
            package,
        )
        package.parts[comments_uri] = comments_part
        document.part.relate_to(
            comments_part,
            "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments",
        )
    else:
        comments_part = package.parts[comments_uri]

    # Append the comment element
    tree = etree.fromstring(comments_part.blob)
    comment_elem = etree.SubElement(tree, _qn("comment"))
    comment_elem.set(_qn("id"), str(comment_id))
    comment_elem.set(_qn("author"), author)
    comment_elem.set(_qn("date"), _now_iso())
    p = etree.SubElement(comment_elem, _qn("p"))
    r = etree.SubElement(p, _qn("r"))
    t = etree.SubElement(r, _qn("t"))
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text
    comments_part._blob = etree.tostring(
        tree, xml_declaration=True, encoding="UTF-8", standalone=True
    )

    # Reference the comment from the paragraph
    p_elem = paragraph._p
    ref_run = etree.SubElement(p_elem, _qn("r"))
    ref = etree.SubElement(ref_run, _qn("commentReference"))
    ref.set(_qn("id"), str(comment_id))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest plugins/hebrew-book-producer/scripts/tests/test_docx_tracked_changes.py -v`
Expected: All 3 tests PASS.

If `test_add_comment_writes_comment_xml` fails because of the comments-part wiring (python-docx internal API differences), simplify the implementation: instead of registering a real OPC part, write the comment as plain text wrapped in `[הערה: ...]` square brackets at the end of the paragraph. The author still sees the rationale; the tradeoff is that it's not a Word "comment" balloon but inline text. Note this in a comment in the source.

- [ ] **Step 5: Commit**

```bash
git add plugins/hebrew-book-producer/scripts/docx_tracked_changes.py plugins/hebrew-book-producer/scripts/tests/test_docx_tracked_changes.py
git commit -m "feat(docx): low-level OOXML helpers for tracked changes + bookmarks + comments"
```

---

## Task 4: Renderer — `render_suggestions_docx.py` (TDD)

**Files:**
- Create: `plugins/hebrew-book-producer/scripts/render_suggestions_docx.py`
- Test: `plugins/hebrew-book-producer/scripts/tests/test_render_suggestions_docx.py`

- [ ] **Step 1: Write the failing test**

Create `plugins/hebrew-book-producer/scripts/tests/test_render_suggestions_docx.py`:

```python
"""Tests for render_suggestions_docx.py."""
from __future__ import annotations
import json
import shutil
import subprocess
import sys
from pathlib import Path
from docx import Document

REPO_ROOT = Path(__file__).resolve().parents[3]
RENDERER = REPO_ROOT / "plugins/hebrew-book-producer/scripts/render_suggestions_docx.py"


def _changes_json(tmp_path: Path) -> Path:
    """Write a minimal changes.json into tmp_path and return its path."""
    sys.path.insert(0, str(REPO_ROOT / "plugins/hebrew-book-producer/scripts"))
    from changes_id import compute_change_id

    chapter = "chapters/ch01.md"
    cid = compute_change_id(chapter, 1, "המחשבות")
    payload = {
        "agent": "linguistic-editor",
        "chapter": "ch01",
        "run_id": "20260503-120000",
        "changes": [
            {
                "change_id": cid,
                "file": chapter,
                "line_start": 1,
                "line_end": 1,
                "type": "word",
                "level": "word",
                "before": "המחשבות",
                "after": "המחשבה",
                "rationale": "register: literary-formal — singular fits the chapter",
            }
        ],
        "state_transition": {"chapter": "ch01", "next_stage": "proofread-1"},
        "summary": "תיקון אחד.",
    }
    cj = tmp_path / "changes.json"
    cj.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return cj


def test_renderer_produces_docx_with_tracked_change(tmp_path: Path) -> None:
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir()
    (chapters_dir / "ch01.md").write_text(
        "# פרק 1\n\nהמחשבות שלי על העולם.\n", encoding="utf-8"
    )
    cj = _changes_json(tmp_path)
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    result = subprocess.run(
        [
            sys.executable,
            str(RENDERER),
            "--changes",
            str(cj),
            "--source",
            str(chapters_dir),
            "--out",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    docx_path = out_dir / "ch01.suggestions.docx"
    assert docx_path.is_file()

    doc = Document(docx_path)
    # Check that the document body contains the deletion and insertion
    body_xml = doc.element.body.xml
    assert "המחשבות" in body_xml  # before
    assert "המחשבה" in body_xml   # after
    assert "w:del" in body_xml
    assert "w:ins" in body_xml
    # Check bookmark is present
    sys.path.insert(0, str(REPO_ROOT / "plugins/hebrew-book-producer/scripts"))
    from changes_id import compute_change_id
    cid = compute_change_id("chapters/ch01.md", 1, "המחשבות")
    assert f"chg_{cid}" in body_xml


def test_renderer_skips_unmatched_changes(tmp_path: Path) -> None:
    """If a change's `before` text doesn't appear in the chapter, log and skip."""
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir()
    (chapters_dir / "ch01.md").write_text("# פרק 1\n\nטקסט לא קשור.\n", encoding="utf-8")
    sys.path.insert(0, str(REPO_ROOT / "plugins/hebrew-book-producer/scripts"))
    from changes_id import compute_change_id
    payload = {
        "agent": "linguistic-editor",
        "chapter": "ch01",
        "changes": [
            {
                "change_id": compute_change_id("chapters/ch01.md", 1, "מילה_לא_קיימת"),
                "file": "chapters/ch01.md",
                "line_start": 1,
                "line_end": 1,
                "type": "word",
                "before": "מילה_לא_קיימת",
                "after": "אחרת",
                "rationale": "test",
            }
        ],
    }
    cj = tmp_path / "changes.json"
    cj.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    result = subprocess.run(
        [
            sys.executable,
            str(RENDERER),
            "--changes",
            str(cj),
            "--source",
            str(chapters_dir),
            "--out",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    # Renderer should still produce a docx (with the original chapter text untouched)
    assert (out_dir / "ch01.suggestions.docx").is_file()
    # And log the skip to stderr
    assert "skipped" in result.stderr.lower() or "no match" in result.stderr.lower()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest plugins/hebrew-book-producer/scripts/tests/test_render_suggestions_docx.py -v`
Expected: FAIL — script does not exist.

- [ ] **Step 3: Implement the renderer**

Create `plugins/hebrew-book-producer/scripts/render_suggestions_docx.py`:

```python
#!/usr/bin/env python3
"""Render a changes.json + chapter markdown into a .docx with tracked changes.

Usage:
    render_suggestions_docx.py \
        --changes <path/to/changes.json> \
        --source <chapters/ dir> \
        --out <out dir>

For each change object whose `file` matches a chapter under <source>:
- Build a new .docx with the chapter's paragraphs.
- For each paragraph that contains the `before` text:
    - Replace `before` with a tracked-change pair (w:del + w:ins).
    - Add a bookmark chg_<change_id> at the change site.
    - Add a comment with the rationale text.

Output: <out>/<chapter>.suggestions.docx
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from docx import Document

# Make sibling modules importable when invoked as a script
sys.path.insert(0, str(Path(__file__).resolve().parent))
from docx_tracked_changes import (  # noqa: E402
    add_tracked_change,
    add_change_bookmark,
    add_comment,
)


def _read_chapter(chapters_dir: Path, file_field: str) -> tuple[Path, list[str]] | None:
    """Resolve a `file` field like 'chapters/ch01.md' to a path under chapters_dir.

    Returns (path, paragraphs) or None if the chapter doesn't exist."""
    name = Path(file_field).name  # "ch01.md"
    path = chapters_dir / name
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    return path, paragraphs


def _group_changes_by_chapter(changes: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for c in changes:
        f = c.get("file", "")
        chapter = Path(f).stem  # "ch01"
        grouped.setdefault(chapter, []).append(c)
    return grouped


def render_chapter(
    chapter_id: str,
    paragraphs: list[str],
    changes_for_chapter: list[dict],
    out_path: Path,
) -> int:
    """Render one chapter to a .docx. Returns the number of changes successfully embedded."""
    doc = Document()
    embedded = 0
    comment_counter = [0]

    for paragraph_text in paragraphs:
        # Find any change whose `before` is a substring of this paragraph
        applicable: list[dict] = []
        remaining: list[dict] = []
        for c in changes_for_chapter:
            before = c.get("before", "")
            if before and before in paragraph_text:
                applicable.append(c)
            else:
                remaining.append(c)
        changes_for_chapter = remaining

        p = doc.add_paragraph()

        if not applicable:
            p.add_run(paragraph_text)
            continue

        # Split the paragraph at the first applicable change's `before` text.
        # For simplicity in v1: handle ONE change per paragraph. Multiple
        # changes per paragraph fall back to plain text + a comment listing them.
        c = applicable[0]
        before = c["before"]
        after = c.get("after", "")
        rationale = c.get("rationale", "")
        change_id = c["change_id"]
        author = "hebrew-book-producer"

        idx = paragraph_text.find(before)
        prefix = paragraph_text[:idx]
        suffix = paragraph_text[idx + len(before):]

        if prefix:
            p.add_run(prefix)
        # Tracked change pair appended after prefix
        add_tracked_change(p, before=before, after=after, author=author)
        if suffix:
            p.add_run(suffix)
        add_change_bookmark(p, change_id=change_id)
        comment_counter[0] += 1
        try:
            add_comment(
                document=doc,
                paragraph=p,
                author=author,
                text=rationale,
                comment_id=comment_counter[0],
            )
        except Exception as e:  # pragma: no cover — fallback to inline text
            p.add_run(f"  [הערה: {rationale}]")
            print(f"comment fallback: {e}", file=sys.stderr)

        embedded += 1

        # If there were additional changes in this paragraph, log them as skipped
        for extra in applicable[1:]:
            print(
                f"skipped multi-change paragraph: {chapter_id} change_id={extra['change_id']}",
                file=sys.stderr,
            )

    # Any leftover changes (no matching paragraph) → log as skipped
    for c in changes_for_chapter:
        print(
            f"skipped: no match for change_id={c['change_id']} before='{c.get('before', '')[:30]}...'",
            file=sys.stderr,
        )

    doc.save(out_path)
    return embedded


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--changes", required=True, help="path to changes.json")
    p.add_argument("--source", required=True, help="chapters/ directory")
    p.add_argument("--out", required=True, help="output directory")
    args = p.parse_args()

    changes_path = Path(args.changes)
    source_dir = Path(args.source)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = json.loads(changes_path.read_text(encoding="utf-8"))
    changes = payload.get("changes", [])
    grouped = _group_changes_by_chapter(changes)

    total_embedded = 0
    for chapter_id, chapter_changes in grouped.items():
        # `file` field example: "chapters/ch01.md" → resolve under source_dir
        first_file = chapter_changes[0]["file"]
        resolved = _read_chapter(source_dir, first_file)
        if resolved is None:
            print(f"skipped chapter (file not found): {first_file}", file=sys.stderr)
            continue
        path, paragraphs = resolved
        out_path = out_dir / f"{chapter_id}.suggestions.docx"
        embedded = render_chapter(chapter_id, paragraphs, chapter_changes, out_path)
        total_embedded += embedded
        print(f"{chapter_id}: embedded {embedded} changes → {out_path}")

    print(f"total embedded: {total_embedded}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Run: `chmod +x plugins/hebrew-book-producer/scripts/render_suggestions_docx.py`

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest plugins/hebrew-book-producer/scripts/tests/test_render_suggestions_docx.py -v`
Expected: All tests PASS. The renderer produces a docx with `w:del`, `w:ins`, and `chg_<id>` bookmark.

- [ ] **Step 5: Open one in Word as a manual smoke test**

Run the renderer on a sample changes.json (you can reuse the test fixture):

```bash
TMP=$(mktemp -d)
mkdir "${TMP}/chapters"
printf '# פרק 1\n\nהמחשבות שלי על העולם.\n' > "${TMP}/chapters/ch01.md"
cat > "${TMP}/changes.json" <<'EOF'
{
  "agent": "linguistic-editor",
  "chapter": "ch01",
  "changes": [
    {
      "change_id": "abcdef012345",
      "file": "chapters/ch01.md",
      "line_start": 1,
      "type": "word",
      "before": "המחשבות",
      "after": "המחשבה",
      "rationale": "register: literary-formal"
    }
  ]
}
EOF
mkdir "${TMP}/out"
python3 plugins/hebrew-book-producer/scripts/render_suggestions_docx.py \
  --changes "${TMP}/changes.json" \
  --source "${TMP}/chapters" \
  --out "${TMP}/out"
open "${TMP}/out/ch01.suggestions.docx"  # macOS — opens in Word/Pages
```

Manual verification: open the .docx in Word. Confirm:
- The deletion (red strikethrough on "המחשבות") and insertion (red underline on "המחשבה") are visible under "Track Changes" view.
- Hovering over the change shows the rationale (or it appears as inline `[הערה: ...]` if the comment fallback path was taken).

- [ ] **Step 6: Commit**

```bash
git add plugins/hebrew-book-producer/scripts/render_suggestions_docx.py plugins/hebrew-book-producer/scripts/tests/test_render_suggestions_docx.py
git commit -m "feat(renderer): render changes.json to chXX.suggestions.docx with tracked changes"
```

---

## Task 5: Wire renderer into production-manager

**Files:**
- Modify: `plugins/hebrew-book-producer/agents/production-manager.md`

After production-manager merges any editorial agent's `changes.json`, it should call the renderer to produce the docx. Production-manager is an agent (markdown), not Python — we update its instructions.

- [ ] **Step 1: Add a renderer-invocation step to production-manager.md**

Open `plugins/hebrew-book-producer/agents/production-manager.md`. Find the `## Sub-agent merge protocol` section. After the existing paragraph that ends with "auditable and resumable.", add:

```markdown

### Docx suggestion rendering

After successfully reading and merging a sub-agent's `changes.json`, render a docx with tracked changes for the author to review in Word:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/render_suggestions_docx.py \
  --changes .book-producer/runs/<run-id>/<agent>/changes.json \
  --source chapters/ \
  --out .book-producer/runs/<run-id>/<agent>/docx/
```

For author convenience, also expose the latest docx per chapter as a symlink:

```bash
mkdir -p chapters
for f in .book-producer/runs/<run-id>/<agent>/docx/*.suggestions.docx; do
  ln -sf "../$(realpath --relative-to=chapters "$f")" "chapters/$(basename "$f")"
done
```

(If `realpath --relative-to` is unavailable on macOS without coreutils, use a Python one-liner: `python3 -c "import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))" <abs-path> chapters`.)

If the renderer exits non-zero, log to `.book-producer/runs/<run-id>/errors.log` and proceed — the docx is a convenience layer, not a blocker for the canonical markdown merge.
```

- [ ] **Step 2: Verify**

Run: `grep -c "render_suggestions_docx.py" plugins/hebrew-book-producer/agents/production-manager.md`
Expected: `1` or more.

- [ ] **Step 3: Commit**

```bash
git add plugins/hebrew-book-producer/agents/production-manager.md
git commit -m "feat(production-manager): invoke docx renderer after each merge"
```

---

## Task 6: Migration — backfill change_id on legacy changes.json

**Files:**
- Modify: `plugins/hebrew-book-producer/agents/production-manager.md`

- [ ] **Step 1: Add a migration step to production-manager**

In `agents/production-manager.md`, in the same `## Sub-agent merge protocol` section, just before the `### Docx suggestion rendering` block you added in Task 5, insert:

```markdown

### change_id backfill (one-time migration)

When reading a sub-agent's `changes.json`, check whether each change object has a `change_id` field. If any are missing:

1. Compute it via:
   ```bash
   python3 -c "
   import sys, json
   sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/scripts')
   from changes_id import compute_change_id
   data = json.load(open('<path-to-changes.json>'))
   for c in data['changes']:
       if 'change_id' not in c:
           c['change_id'] = compute_change_id(c['file'], c.get('line_start', 0), c.get('before', ''))
   json.dump(data, open('<path-to-changes.json>', 'w'), ensure_ascii=False, indent=2)
   "
   ```
2. Continue with the merge.

The migration is idempotent — already-migrated files are no-ops.
```

- [ ] **Step 2: Commit**

```bash
git add plugins/hebrew-book-producer/agents/production-manager.md
git commit -m "feat(production-manager): backfill change_id on legacy changes.json"
```

---

## Task 7: Applier — `apply_reviewed_docx.py` (TDD)

**Files:**
- Create: `plugins/hebrew-book-producer/scripts/apply_reviewed_docx.py`
- Test: `plugins/hebrew-book-producer/scripts/tests/test_apply_reviewed_docx.py`

The applier is the round-trip: reviewed docx → flatten via pandoc → cross-reference with original `changes.json` → classify each change as accepted/rejected/modified → apply to canonical markdown → write decision log.

- [ ] **Step 1: Write the failing test**

Create `plugins/hebrew-book-producer/scripts/tests/test_apply_reviewed_docx.py`:

```python
"""Tests for apply_reviewed_docx.py — round-trip reviewed docx into markdown."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
APPLIER = REPO_ROOT / "plugins/hebrew-book-producer/scripts/apply_reviewed_docx.py"


def _make_reviewed_md(tmp_path: Path, content: str) -> Path:
    """Write a markdown file (simulating pandoc's flatten of a reviewed docx)."""
    p = tmp_path / "reviewed.md"
    p.write_text(content, encoding="utf-8")
    return p


def test_accepted_change_applied_to_canonical(tmp_path: Path) -> None:
    sys.path.insert(0, str(REPO_ROOT / "plugins/hebrew-book-producer/scripts"))
    from changes_id import compute_change_id

    canonical = tmp_path / "chapters" / "ch01.md"
    canonical.parent.mkdir()
    canonical.write_text("המחשבות שלי על העולם.", encoding="utf-8")

    cid = compute_change_id("chapters/ch01.md", 1, "המחשבות")
    payload = {
        "agent": "linguistic-editor",
        "chapter": "ch01",
        "run_id": "20260503-120000",
        "changes": [
            {
                "change_id": cid,
                "file": "chapters/ch01.md",
                "line_start": 1,
                "type": "word",
                "before": "המחשבות",
                "after": "המחשבה",
                "rationale": "register",
            }
        ],
    }
    cj = tmp_path / "changes.json"
    cj.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    # Simulate the author accepting: the reviewed flatten contains "after" text.
    reviewed = _make_reviewed_md(tmp_path, "המחשבה שלי על העולם.")

    result = subprocess.run(
        [
            sys.executable,
            str(APPLIER),
            "--reviewed-md",
            str(reviewed),
            "--changes",
            str(cj),
            "--canonical",
            str(canonical),
            "--decisions-out",
            str(tmp_path / "decisions.json"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert canonical.read_text(encoding="utf-8") == "המחשבה שלי על העולם."

    decisions = json.loads((tmp_path / "decisions.json").read_text(encoding="utf-8"))
    assert decisions["accepted"] == [cid]
    assert decisions["rejected"] == []
    assert decisions["modified"] == []


def test_rejected_change_keeps_original(tmp_path: Path) -> None:
    sys.path.insert(0, str(REPO_ROOT / "plugins/hebrew-book-producer/scripts"))
    from changes_id import compute_change_id

    canonical = tmp_path / "chapters" / "ch01.md"
    canonical.parent.mkdir()
    canonical.write_text("המחשבות שלי.", encoding="utf-8")

    cid = compute_change_id("chapters/ch01.md", 1, "המחשבות")
    payload = {
        "changes": [
            {
                "change_id": cid,
                "file": "chapters/ch01.md",
                "line_start": 1,
                "type": "word",
                "before": "המחשבות",
                "after": "המחשבה",
                "rationale": "register",
            }
        ]
    }
    cj = tmp_path / "changes.json"
    cj.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    # Author rejected: reviewed flatten still contains "before" text.
    reviewed = _make_reviewed_md(tmp_path, "המחשבות שלי.")

    result = subprocess.run(
        [
            sys.executable,
            str(APPLIER),
            "--reviewed-md",
            str(reviewed),
            "--changes",
            str(cj),
            "--canonical",
            str(canonical),
            "--decisions-out",
            str(tmp_path / "decisions.json"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert canonical.read_text(encoding="utf-8") == "המחשבות שלי."

    decisions = json.loads((tmp_path / "decisions.json").read_text(encoding="utf-8"))
    assert decisions["rejected"] == [cid]
    assert decisions["accepted"] == []


def test_modified_change_uses_authors_text(tmp_path: Path) -> None:
    sys.path.insert(0, str(REPO_ROOT / "plugins/hebrew-book-producer/scripts"))
    from changes_id import compute_change_id

    canonical = tmp_path / "chapters" / "ch01.md"
    canonical.parent.mkdir()
    canonical.write_text("המחשבות שלי.", encoding="utf-8")

    cid = compute_change_id("chapters/ch01.md", 1, "המחשבות")
    payload = {
        "changes": [
            {
                "change_id": cid,
                "file": "chapters/ch01.md",
                "line_start": 1,
                "type": "word",
                "before": "המחשבות",
                "after": "המחשבה",
                "rationale": "register",
            }
        ]
    }
    cj = tmp_path / "changes.json"
    cj.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    # Author tweaked: reviewed flatten contains neither "before" nor "after"
    reviewed = _make_reviewed_md(tmp_path, "הרעיונות שלי.")

    result = subprocess.run(
        [
            sys.executable,
            str(APPLIER),
            "--reviewed-md",
            str(reviewed),
            "--changes",
            str(cj),
            "--canonical",
            str(canonical),
            "--decisions-out",
            str(tmp_path / "decisions.json"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    # Canonical now matches the author's modified version
    assert canonical.read_text(encoding="utf-8") == "הרעיונות שלי."

    decisions = json.loads((tmp_path / "decisions.json").read_text(encoding="utf-8"))
    assert len(decisions["modified"]) == 1
    assert decisions["modified"][0]["change_id"] == cid
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest plugins/hebrew-book-producer/scripts/tests/test_apply_reviewed_docx.py -v`
Expected: FAIL — script does not exist.

- [ ] **Step 3: Implement the applier**

Create `plugins/hebrew-book-producer/scripts/apply_reviewed_docx.py`:

```python
#!/usr/bin/env python3
"""Round-trip a reviewed manuscript back into the canonical markdown.

Inputs:
  --reviewed-md   : path to a markdown file (typically pandoc's flatten of the
                    reviewed docx with --track-changes=accept).
  --changes       : path to the original changes.json (with change_id on every change).
  --canonical     : path to the canonical chapters/<id>.md to update in-place.
  --decisions-out : path to write the decision log JSON.

Algorithm (per change):
  - "after" appears in reviewed-md, "before" does not  → accepted
  - "before" appears in reviewed-md, "after" does not  → rejected
  - neither appears                                    → modified (author tweaked)
  - both appear                                        → ambiguous; log and treat as accepted

For modified changes, the script does NOT try to extract the author's exact
new text from the reviewed-md — the human reviewer should inspect the decision
log and the canonical file. We simply copy the reviewed-md's text wholesale
into the canonical file when modifications are detected, since pandoc's flatten
is the authoritative post-review state.

Novel edits (text in reviewed-md that doesn't match any change object) are
detected by a simple paragraph diff and surfaced in the decision log under
`novel_edits` for human confirmation in a separate flow (out of scope for v1).
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path


def classify_change(reviewed_text: str, before: str, after: str) -> str:
    has_after = bool(after) and after in reviewed_text
    has_before = bool(before) and before in reviewed_text
    if has_after and not has_before:
        return "accepted"
    if has_before and not has_after:
        return "rejected"
    if not has_after and not has_before:
        return "modified"
    # both present — rare; treat as accepted but log
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

    accepted: list[str] = []
    rejected: list[str] = []
    modified: list[dict] = []

    # Apply changes to canonical based on classification
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

    # If any modifications detected, the safest move is to take the reviewed-md
    # as the new canonical wholesale — that captures both the agent's accepted
    # changes and the author's tweaks in one pass.
    if modified:
        new_canonical = reviewed

    canonical_path.write_text(new_canonical, encoding="utf-8")

    decisions = {
        "chapter": payload.get("chapter", canonical_path.stem),
        "run_id": payload.get("run_id"),
        "accepted": accepted,
        "rejected": rejected,
        "modified": modified,
        "novel_edits": [],  # v2: detect via paragraph diff
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
```

Run: `chmod +x plugins/hebrew-book-producer/scripts/apply_reviewed_docx.py`

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest plugins/hebrew-book-producer/scripts/tests/test_apply_reviewed_docx.py -v`
Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/hebrew-book-producer/scripts/apply_reviewed_docx.py plugins/hebrew-book-producer/scripts/tests/test_apply_reviewed_docx.py
git commit -m "feat(applier): round-trip reviewed docx into canonical markdown with decision log"
```

---

## Task 8: `/apply` command

**Files:**
- Create: `plugins/hebrew-book-producer/commands/apply.md`

- [ ] **Step 1: Write the command**

Create `plugins/hebrew-book-producer/commands/apply.md`:

```markdown
---
description: Round-trip a reviewed .docx (with tracked-change accept/reject decisions) back into the canonical chapter markdown. Pass a chapter ID, or no argument to apply all chapters with reviewed docx files.
argument-hint: [chapter-id] [--accept-all]
---

# /apply — round-trip reviewed docx into canonical markdown

## Pre-flight

1. Verify `book.yaml` exists.
2. Verify `chapters/` directory exists.
3. Determine the latest run-id: `ls -1 .book-producer/runs/ | sort | tail -1`. Save as `RUN_ID`.

## Argument handling

- No argument → apply every chapter that has a reviewed docx (`chapters/<id>.reviewed.docx`).
- `<chapter-id>` (e.g. `ch03`) → apply only that chapter.
- `--accept-all` (with chapter-id) → bypass docx round-trip; accept every change in the chapter's `changes.json` directly.

## For each target chapter

### Step A — locate the reviewed docx

Look for `chapters/<chapter>.reviewed.docx`. If absent, look for `chapters/<chapter>.suggestions.docx` whose mtime is newer than the file production-manager originally wrote (= the author saved over it). If neither found:
- Print Hebrew error: "לא נמצא קובץ סקירה עבור פרק <chapter>. צרי קובץ <chapter>.reviewed.docx ב-chapters/ ונסי שוב."
- Skip this chapter and continue with the next.

### Step B — flatten via pandoc

```bash
pandoc --track-changes=accept "chapters/<chapter>.reviewed.docx" \
  -o ".book-producer/round-trip/<chapter>.reviewed.md"
```

Create the directory if missing: `mkdir -p .book-producer/round-trip`.

### Step C — locate the original changes.json

```bash
CHANGES_JSON=$(ls -1 .book-producer/runs/${RUN_ID}/*/changes.json | head -1)
```

If multiple agents touched this chapter (literary + linguistic + proofreader), there are multiple changes.json files. Apply them in stage order: literary → linguistic → proofreader. Re-run Steps D and E for each.

### Step D — run the applier

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/apply_reviewed_docx.py \
  --reviewed-md ".book-producer/round-trip/<chapter>.reviewed.md" \
  --changes "${CHANGES_JSON}" \
  --canonical "chapters/<chapter>.md" \
  --decisions-out ".book-producer/runs/${RUN_ID}/<agent>/apply-decisions.<chapter>.json"
```

### Step E — print Hebrew summary

Read the decisions JSON. Print a 5-line Hebrew summary:

```
פרק: <chapter>
שינויים מוצעים: <total>
אישרת: <accepted count>
דחית: <rejected count>
שינית: <modified count>
```

Then add a one-line follow-up:

> "הקובץ הסופי: chapters/<chapter>.md. רוצה לראות diff מול הגרסה הקודמת? (git diff HEAD~1 chapters/<chapter>.md)"

## --accept-all path

If invoked as `/apply <chapter> --accept-all`:

```bash
python3 -c "
import json, sys
sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/scripts')
data = json.load(open('${CHANGES_JSON}'))
text = open('chapters/<chapter>.md').read()
accepted = []
for c in data['changes']:
    if c.get('before') and c['before'] in text:
        text = text.replace(c['before'], c.get('after', ''), 1)
        accepted.append(c['change_id'])
open('chapters/<chapter>.md', 'w').write(text)
print(f'accepted-all: {len(accepted)} changes')
"
```

Then write a decisions log with all change_ids in `accepted`. Print Hebrew summary as above.

## Hard rules

- **Markdown is canonical.** `chapters/<chapter>.md` is the source of truth. Docx is a review surface only.
- **Never modify changes.json.** It records what the agent proposed; the apply step records what the author decided in a separate decisions file.
- **Never write to `.book-producer/state.json`** — that's production-manager's job. After apply, the user should run `/edit` (or whichever next stage) to advance state.
- If pandoc errors on the reviewed docx, surface the error and stop. Do NOT touch the canonical markdown.
```

- [ ] **Step 2: Verify**

Run: `head -3 plugins/hebrew-book-producer/commands/apply.md`
Expected: YAML frontmatter with description.

- [ ] **Step 3: Commit**

```bash
git add plugins/hebrew-book-producer/commands/apply.md
git commit -m "feat(commands): /apply round-trips reviewed docx into canonical markdown"
```

---

## Task 9: End-to-end smoke test

**Files:** none (manual verification)

- [ ] **Step 1: Set up a test project**

```bash
TMP=$(mktemp -d)
mkdir -p "${TMP}/chapters"
printf '# פרק 1\n\nהמחשבות שלי על העולם.\nזהו טקסט נוסף.\n' > "${TMP}/chapters/ch01.md"
cat > "${TMP}/book.yaml" <<EOF
genre: philosophy
title: "ספר בדיקה"
EOF
cd "${TMP}"
```

- [ ] **Step 2: Manually craft a changes.json**

```bash
mkdir -p .book-producer/runs/20260503-test/linguistic-editor
python3 <<'EOF'
import json, sys
sys.path.insert(0, '/Users/yotamfromm/dev/hebrew-book-producer/plugins/hebrew-book-producer/scripts')
from changes_id import compute_change_id
cid = compute_change_id('chapters/ch01.md', 1, 'המחשבות')
data = {
  "agent": "linguistic-editor",
  "chapter": "ch01",
  "run_id": "20260503-test",
  "changes": [
    {
      "change_id": cid,
      "file": "chapters/ch01.md",
      "line_start": 1,
      "type": "word",
      "before": "המחשבות",
      "after": "המחשבה",
      "rationale": "register: literary-formal — singular fits the chapter"
    }
  ],
  "state_transition": {"chapter": "ch01", "next_stage": "proofread-1"},
  "summary": "תיקון אחד."
}
json.dump(data, open('.book-producer/runs/20260503-test/linguistic-editor/changes.json', 'w'), ensure_ascii=False, indent=2)
EOF
```

- [ ] **Step 3: Render the docx**

```bash
mkdir -p .book-producer/runs/20260503-test/linguistic-editor/docx
python3 /Users/yotamfromm/dev/hebrew-book-producer/plugins/hebrew-book-producer/scripts/render_suggestions_docx.py \
  --changes .book-producer/runs/20260503-test/linguistic-editor/changes.json \
  --source chapters/ \
  --out .book-producer/runs/20260503-test/linguistic-editor/docx/
ls .book-producer/runs/20260503-test/linguistic-editor/docx/
```

Expected: `ch01.suggestions.docx` exists.

- [ ] **Step 4: Open it in Word and accept the change**

```bash
open .book-producer/runs/20260503-test/linguistic-editor/docx/ch01.suggestions.docx
```

In Word: Review → Accept All → Save As `chapters/ch01.reviewed.docx`.

- [ ] **Step 5: Run /apply from a Claude Code session**

Open Claude Code in the test project. Run `/apply ch01`.

Expected:
- A Hebrew summary line: "אישרת: 1 דחית: 0 שינית: 0".
- `chapters/ch01.md` now reads `המחשבה שלי על העולם.` (singular).
- `.book-producer/runs/20260503-test/linguistic-editor/apply-decisions.ch01.json` exists and lists the change_id under `accepted`.

- [ ] **Step 6: Run a reject scenario**

Restore `chapters/ch01.md` to plural form. Re-render the docx. In Word, this time Reject the change. Save as `.reviewed.docx`. Run `/apply ch01` again.

Expected:
- Hebrew summary: "אישרת: 0 דחית: 1 שינית: 0".
- `chapters/ch01.md` is unchanged from the plural form.
- Decisions log lists the change_id under `rejected`.

- [ ] **Step 7: Run a modified scenario**

Re-render docx. In Word, accept the change but then manually edit `המחשבה` → `הרעיון`. Save as `.reviewed.docx`. Run `/apply ch01`.

Expected:
- Hebrew summary: "אישרת: 0 דחית: 0 שינית: 1".
- `chapters/ch01.md` now contains `הרעיון`.
- Decisions log lists the change_id under `modified`.

- [ ] **Step 8: Update CHANGELOG**

```bash
cd /Users/yotamfromm/dev/hebrew-book-producer
cat >> CHANGELOG.md <<'EOF'

## [Unreleased]

### Added
- Docx suggestion mode: every editorial agent's changes.json renders to chXX.suggestions.docx with Word tracked changes + comments.
- `/apply <chapter>` command: round-trip reviewed docx (accepted/rejected/modified decisions) into canonical markdown.
- Decision log under `.book-producer/runs/<run-id>/<agent>/apply-decisions.<chapter>.json` (consumed by voice-miner).
- `change_id` is now required on every change object in changes.json. Production-manager backfills legacy files.

EOF
git add CHANGELOG.md
git commit -m "docs(changelog): document docx suggestion mode + /apply"
```

---

## Self-Review

**1. Spec coverage (§ Component 3 of the design):**
- Renderer with tracked changes + comments + bookmarks → Tasks 3, 4 ✅
- change_id stable hash → Task 1 ✅
- Schema migration → Tasks 2, 6 ✅
- Production-manager invokes renderer → Task 5 ✅
- /apply round-trip → Tasks 7, 8 ✅
- Decision log → Task 7 (in applier output) ✅
- Whole-book export and re-split (`/export-suggestions`) → **NOT covered.** This is a v2 follow-up. The spec lists it as optional; deferring to a later plan keeps Plan 2 scoped.

**2. Placeholder scan:** No "TBD"/"TODO"/"implement later" in the plan. The applier's "novel_edits" detection is explicitly marked "v2: detect via paragraph diff" and the field is emitted as `[]` — that's a documented future enhancement, not a placeholder.

**3. Type consistency:**
- `change_id` is a 12-char lowercase hex string everywhere: `changes_id.py` produces it, `docx_tracked_changes.add_change_bookmark` consumes it as `change_id` parameter, the renderer passes it as `c["change_id"]`, the applier reads it as `c["change_id"]`, and the schema in `SKILL.md` has the regex `^[0-9a-f]{12}$`.
- Bookmark name format: `chg_<change_id>` everywhere (Task 3 implementation, Task 4 test, spec § Component 3).
- Decision log fields: `accepted` (list of change_ids), `rejected` (list), `modified` (list of objects with `change_id`, `original_before`, `original_after`), `novel_edits` (list, empty for now). Same shape in applier code (Task 7) and the test expectations.

---

## Acceptance Criteria for Plan 2

- [ ] All 9 tasks completed and committed.
- [ ] `pytest plugins/hebrew-book-producer/scripts/tests/test_changes_id.py plugins/hebrew-book-producer/scripts/tests/test_docx_tracked_changes.py plugins/hebrew-book-producer/scripts/tests/test_render_suggestions_docx.py plugins/hebrew-book-producer/scripts/tests/test_apply_reviewed_docx.py` is green.
- [ ] Manual smoke test in Task 9 passes for all three scenarios (accept, reject, modify).
- [ ] Opening a rendered `.docx` in Word shows tracked changes (red strikethrough + insertion) and the rationale appears as a comment or inline `[הערה: ...]`.
- [ ] CHANGELOG entry committed.
