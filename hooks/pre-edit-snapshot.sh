#!/usr/bin/env bash
# pre-edit-snapshot.sh — snapshot a file before any Edit/Write tool call.
# Reads tool-call payload from stdin (JSON) and snapshots the target file
# to .book-producer/snapshots/<timestamp>-<basename>.bak in the project root.
#
# Failure here MUST NOT block the edit — log and exit 0 always.

set -u

PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
SNAP_DIR="${PROJECT_ROOT}/.book-producer/snapshots"
mkdir -p "${SNAP_DIR}" 2>/dev/null || exit 0

# Tool-call payload arrives on stdin as JSON.
payload="$(cat 2>/dev/null || true)"

# Extract file_path from payload. Use a tolerant grep — the format may vary
# across Claude Code versions and we'd rather skip than crash.
file=""
if command -v jq >/dev/null 2>&1; then
  file="$(printf '%s' "${payload}" | jq -r '.tool_input.file_path // .params.file_path // empty' 2>/dev/null || true)"
fi
if [ -z "${file}" ]; then
  file="$(printf '%s' "${payload}" | grep -oE '"file_path"[[:space:]]*:[[:space:]]*"[^"]+"' | head -1 | sed -E 's/.*"file_path"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')"
fi

# Nothing to snapshot if no file or file doesn't exist yet (Write of a new file).
[ -z "${file}" ] && exit 0
[ ! -f "${file}" ] && exit 0

ts="$(date +%Y%m%d-%H%M%S)"
base="$(basename "${file}")"
cp "${file}" "${SNAP_DIR}/${ts}-${base}.bak" 2>/dev/null || true

# Optionally prune snapshots older than 30 days to keep the dir small.
find "${SNAP_DIR}" -name '*.bak' -mtime +30 -delete 2>/dev/null || true

exit 0
