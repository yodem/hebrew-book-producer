#!/usr/bin/env bash
set -euo pipefail
root="${CLAUDE_PROJECT_DIR:-$(pwd)}"
[[ -f "$root/book.yaml" ]] || exit 0
[[ -x "$root/plugins/hebrew-book-producer/skills/voice/voice-sync.sh" ]] || exit 0
VOICE_PROJECT_ROOT="$root" bash "$root/plugins/hebrew-book-producer/skills/voice/voice-sync.sh" pull \
  || echo "[voice-pull] non-fatal: $?" >&2
