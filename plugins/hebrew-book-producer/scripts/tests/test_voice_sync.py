"""Tests for voice-sync.sh utility (hebrew-book-producer port)."""
import subprocess
from pathlib import Path
import os

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT = REPO_ROOT / "plugins" / "hebrew-book-producer" / "skills" / "voice" / "voice-sync.sh"


def test_script_exists_and_executable():
    assert SCRIPT.is_file()
    assert os.access(SCRIPT, os.X_OK)


def test_no_op_when_ck_missing(tmp_path):
    env = os.environ.copy()
    # Force ck-missing by clearing PATH
    env["PATH"] = "/dev/null"
    env["VOICE_PROJECT_ROOT"] = str(tmp_path)
    (tmp_path / "AUTHOR_VOICE.md").write_text("# stub\n")
    r = subprocess.run([str(SCRIPT), "push"], env=env, capture_output=True, text=True)
    assert r.returncode == 0
    assert "ck not available" in (r.stdout + r.stderr).lower()


def test_status_reports_no_id_cache(tmp_path):
    env = os.environ.copy()
    env["VOICE_PROJECT_ROOT"] = str(tmp_path)
    (tmp_path / ".voice").mkdir()
    # status runs only when a ck binary is on PATH; give it a stub so the test
    # does not depend on a real ck install (status itself never calls ck).
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    stub = stub_bin / "ck"
    stub.write_text("#!/bin/sh\nexit 1\n")
    stub.chmod(0o755)
    env["PATH"] = f"{stub_bin}{os.pathsep}{env.get('PATH', '')}"
    r = subprocess.run([str(SCRIPT), "status"], env=env, capture_output=True, text=True)
    assert "no cached candlekeep id" in (r.stdout + r.stderr).lower()
