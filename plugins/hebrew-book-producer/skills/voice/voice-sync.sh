#!/bin/bash
# voice-sync.sh — pull/push AUTHOR_VOICE.md to/from CandleKeep
# Usage: voice-sync.sh {pull|push|status}
# Env:
#   VOICE_PROJECT_ROOT — overrides $(pwd) for testing
#   VOICE_WRITER_NAME  — overrides writer name lookup; default reads from profile.json/book.yaml

set -euo pipefail

action=${1:-status}
root="${VOICE_PROJECT_ROOT:-$(pwd)}"
profile="$root/AUTHOR_VOICE.md"
voice_dir="$root/.voice"
id_cache="$voice_dir/.candlekeep-id"

# Resolve writer name (best-effort; empty is fine)
writer="${VOICE_WRITER_NAME:-}"
if [[ -z "$writer" ]]; then
  if [[ -f "$root/.academic-writer/profile.json" ]]; then
    writer=$(grep -E '"writer_name"' "$root/.academic-writer/profile.json" 2>/dev/null \
      | sed -E 's/.*"writer_name"[[:space:]]*:[[:space:]]*"([^"]*)".*/\1/' || true)
  elif [[ -f "$root/book.yaml" ]]; then
    writer=$(grep -E '^author:' "$root/book.yaml" 2>/dev/null \
      | sed -E 's/^author:[[:space:]]*"?([^"]*)"?$/\1/' || true)
  fi
fi
[[ -z "$writer" ]] && writer="<unknown>"
title="Voice Profile — $writer"

if ! command -v ck >/dev/null 2>&1; then
  echo "voice-sync: ck not available — local-only mode"
  exit 0
fi

ensure_id() {
  if [[ -f "$id_cache" ]]; then
    cat "$id_cache"
    return 0
  fi
  # Title fallback
  id=$(ck books list --json 2>/dev/null \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(next((b['id'] for b in d if b.get('title')=='$title'),''))" \
    || true)
  if [[ -n "$id" ]]; then
    mkdir -p "$voice_dir"
    echo "$id" > "$id_cache"
  fi
  echo "$id"
}

case "$action" in
  status)
    if [[ -f "$id_cache" ]]; then
      echo "voice-sync status: cached id=$(cat "$id_cache"), title=$title"
    else
      echo "voice-sync status: no cached candlekeep id"
    fi
    ;;
  pull)
    id=$(ensure_id)
    if [[ -z "$id" ]]; then
      echo "voice-sync pull: no remote book yet (run push to create)"
      exit 0
    fi
    ck books read "$id" --format md > "$profile.tmp"
    # Last-write-wins by `> Updated` stamp comparison
    local_stamp=$(grep -m1 '^> Updated' "$profile" 2>/dev/null | sed -E 's/^> Updated ([0-9-]+).*/\1/' || echo "0")
    remote_stamp=$(grep -m1 '^> Updated' "$profile.tmp" 2>/dev/null | sed -E 's/^> Updated ([0-9-]+).*/\1/' || echo "0")
    if [[ "$remote_stamp" > "$local_stamp" ]]; then
      mv "$profile.tmp" "$profile"
      echo "voice-sync pull: remote ($remote_stamp) overwrote local ($local_stamp)"
    else
      rm "$profile.tmp"
      echo "voice-sync pull: local ($local_stamp) is newer or equal to remote ($remote_stamp); kept local"
    fi
    ;;
  push)
    id=$(ensure_id)
    if [[ -z "$id" ]]; then
      id=$(ck books create --title "$title" --format md --content "$profile" --json 2>/dev/null \
        | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null || true)
      if [[ -n "$id" ]]; then
        mkdir -p "$voice_dir"
        echo "$id" > "$id_cache"
        echo "voice-sync push: created remote book id=$id"
      else
        echo "voice-sync push: ck unavailable or books subcommand unsupported — local-only mode"
      fi
    else
      ck books update "$id" --content "$profile" 2>/dev/null || \
        echo "voice-sync push: ck update failed — local-only mode"
      echo "voice-sync push: updated remote book id=$id"
    fi
    ;;
  *)
    echo "usage: $0 {pull|push|status}" >&2
    exit 2
    ;;
esac
