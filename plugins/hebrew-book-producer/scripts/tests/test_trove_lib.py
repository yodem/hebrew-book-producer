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
    {"id": "cmlockedbook00000000001", "title": "Hebrew Linguistic Reference", "locked": True},
    {"id": "cmrealbook0000000000001", "title": "Hebrew Linguistic Reference", "locked": False},
    {"id": "cmotherbook000000000001", "title": "Other", "locked": False},
    {"id": "cmlockedonly00000000001", "title": "Locked Only", "locked": True},
    {"id": "cmdupbook00000000000001", "title": "Dup", "locked": False},
    {"id": "cmdupbook00000000000002", "title": "Dup", "locked": False},
]

STUB = r'''#!/bin/bash
# stub trove: list prints $STUB_LIST; read serves two parts of book cmrealbook0000000000001
if [ "$2" = "list" ]; then cat "$STUB_LIST"; exit 0; fi
if [ "$2" = "read" ]; then
  case "$*" in
    *"--pages all"*) printf '%s\n' "────" "Book" "ID: cmrealbook0000000000001 | 2 pages" "Version: 1" "────" "" "── Page 1 ──" "" "# One" "first" "" "Stopped after page 1 to stay under 20,000 bytes. Next: trove items read cmrealbook0000000000001 --pages 2-2" ;;
    *"--pages 2-2"*) printf '%s\n' "────" "Book" "ID: cmrealbook0000000000001 | 2 pages" "Version: 1" "────" "" "── Page 2 ──" "" "# Two" "second" ;;
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
    assert r.stdout.strip() == "cmrealbook0000000000001"


def test_find_by_title_missing(tmp_path):
    r = _run(tmp_path, "object", 'trove_find_by_title "Nope"')
    assert r.returncode != 0 and r.stdout.strip() == ""


def test_fetch_follows_next_and_body_strips_header(tmp_path):
    r = _run(tmp_path, "object", 'trove_fetch cmrealbook0000000000001 raw.md && trove_body raw.md body.md')
    assert r.returncode == 0, r.stderr
    raw = (tmp_path / "raw.md").read_text()
    assert "Next: trove" not in raw and "second" in raw
    assert raw.count("Version: 1") == 1, "continuation header must be stripped"
    assert (tmp_path / "body.md").read_text() == "# One\nfirst\n\n# Two\nsecond\n"


def test_fetch_refuses_bad_id(tmp_path):
    r = _run(tmp_path, "object", 'trove_fetch "x;rm -rf /" raw.md')
    assert r.returncode != 0 and not (tmp_path / "raw.md").exists()


def test_find_by_title_refuses_ambiguous(tmp_path):
    r = _run(tmp_path, "object", 'trove_find_by_title "Dup"')
    assert r.returncode != 0


def test_find_by_title_error_is_distinct_from_missing(tmp_path):
    missing = _run(tmp_path, "object", 'trove_find_by_title "Nope"; echo "rc=$?"')
    ambiguous = _run(tmp_path, "object", 'trove_find_by_title "Dup"; echo "rc=$?"')
    assert "rc=1" in missing.stdout and "rc=2" in ambiguous.stdout


def test_body_works_in_c_locale(tmp_path):
    r = _run(tmp_path, "object", 'export LC_ALL=C; trove_fetch cmrealbook0000000000001 raw.md && trove_body raw.md body.md')
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "body.md").read_text() == "# One\nfirst\n\n# Two\nsecond\n"


def test_locked_only_match_is_an_error(tmp_path):
    r = _run(tmp_path, "object", 'trove_find_by_title "Locked Only"; echo "rc=$?"')
    assert "rc=2" in r.stdout


def test_empty_listing_is_an_error(tmp_path):
    r = _run(tmp_path, "object", 'printf "" > list.json; trove_find_by_title "Nope"; echo "rc=$?"')
    assert "rc=2" in r.stdout
