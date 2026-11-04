"""trove-lib.sh: title lookup over both `trove items list --json` shapes, locked
books skipped, multi-part reads followed, and the read header stripped."""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

LIB = Path(__file__).resolve().parents[1] / "trove-lib.sh"
pytestmark = pytest.mark.skipif(shutil.which("jq") is None, reason="jq not installed")

ITEMS = [
    {"id": "cmlocked", "title": "Hebrew Linguistic Reference", "locked": True},
    {"id": "cmreal", "title": "Hebrew Linguistic Reference", "locked": False},
    {"id": "cmother", "title": "Other", "locked": False},
]

STUB = r'''#!/bin/bash
# stub trove: list prints $STUB_LIST; read serves two parts of book cmreal
if [ "$2" = "list" ]; then cat "$STUB_LIST"; exit 0; fi
if [ "$2" = "read" ]; then
  case "$*" in
    *"--pages all"*) printf '%s\n' "────" "Book" "ID: cmreal | 2 pages" "Version: 1" "────" "" "── Page 1 ──" "" "# One" "first" "" "Stopped after page 1 to stay under 20,000 bytes. Next: trove items read cmreal --pages 2-2" ;;
    *"--pages 2-2"*) printf '%s\n' "── Page 2 ──" "" "# Two" "second" ;;
    *) exit 1 ;;
  esac
  exit 0
fi
exit 1
'''


def _run(tmp_path, shape, script):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    stub = bin_dir / "trove"
    stub.write_text(STUB)
    stub.chmod(0o755)
    listing = tmp_path / "list.json"
    listing.write_text(json.dumps({"items": ITEMS, "enrichmentQueue": []} if shape == "object" else ITEMS))
    env = dict(os.environ, PATH=f"{bin_dir}{os.pathsep}{os.environ['PATH']}", STUB_LIST=str(listing))
    return subprocess.run(["bash", "-c", f'. "{LIB}"; {script}'], env=env, capture_output=True, text=True, cwd=tmp_path)


@pytest.mark.parametrize("shape", ["object", "array"])
def test_find_by_title_skips_locked(tmp_path, shape):
    r = _run(tmp_path, shape, 'trove_find_by_title "Hebrew Linguistic Reference"')
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "cmreal"


def test_find_by_title_missing(tmp_path):
    r = _run(tmp_path, "object", 'trove_find_by_title "Nope"')
    assert r.returncode != 0 and r.stdout.strip() == ""


def test_fetch_follows_next_and_body_strips_header(tmp_path):
    r = _run(tmp_path, "object", 'trove_fetch cmreal raw.md && trove_body raw.md body.md')
    assert r.returncode == 0, r.stderr
    raw = (tmp_path / "raw.md").read_text()
    assert "Next: trove" not in raw and "second" in raw
    assert (tmp_path / "body.md").read_text() == "# One\nfirst\n\n# Two\nsecond\n"
