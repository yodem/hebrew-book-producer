#!/usr/bin/env bash
# voice-pull.sh — SessionStart hook: pull AUTHOR_VOICE.md from CandleKeep.
# Preserves the local `writer:` section if the remote copy does not contain it.
set -euo pipefail

root="${CLAUDE_PROJECT_DIR:-$(pwd)}"
[[ -f "$root/book.yaml" ]] || exit 0
[[ -x "$root/plugins/hebrew-book-producer/skills/voice/voice-sync.sh" ]] || exit 0

profile="$root/AUTHOR_VOICE.md"

# Save local writer: section before the pull (best-effort; empty string if not present)
local_writer_section=""
if [[ -f "$profile" ]]; then
  # Extract everything from '## Writer Configuration' to end-of-file (or next ## heading)
  local_writer_section=$(awk '
    /^## Writer Configuration/ { found=1 }
    found && /^## / && !/^## Writer Configuration/ { found=0 }
    found { print }
  ' "$profile" || true)
fi

# Perform the pull (last-write-wins by > Updated stamp)
VOICE_PROJECT_ROOT="$root" bash "$root/plugins/hebrew-book-producer/skills/voice/voice-sync.sh" pull \
  || echo "[voice-pull] non-fatal: $?" >&2

# If pull succeeded and post-pull file lacks ## Writer Configuration, re-merge local section
if [[ -f "$profile" ]] && [[ -n "$local_writer_section" ]]; then
  if ! grep -q '^## Writer Configuration' "$profile" 2>/dev/null; then
    # Append the preserved section at the end of the file
    printf '\n%s\n' "$local_writer_section" >> "$profile"
    echo "[voice-pull] re-merged local writer: section (remote did not have it)" >&2
  fi
fi
