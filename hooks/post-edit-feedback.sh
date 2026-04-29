#!/usr/bin/env bash
# post-edit-feedback.sh — append a unified diff of the just-completed Edit
# to .book-producer/memory.md so the next session sees what changed.
#
# Failure here MUST NOT block anything — log and exit 0 always.

set -u

PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
SNAP_DIR="${PROJECT_ROOT}/.book-producer/snapshots"
MEM_FILE="${PROJECT_ROOT}/.book-producer/memory.md"

mkdir -p "$(dirname "${MEM_FILE}")" 2>/dev/null || exit 0

# Tool-call payload arrives on stdin.
payload="$(cat 2>/dev/null || true)"
[ -z "${payload}" ] && exit 0

# Strict: require jq. No regex JSON parsing.
if ! command -v jq >/dev/null 2>&1; then
  exit 0
fi

file=$(printf '%s' "${payload}" | jq -r '.tool_input.file_path // .params.file_path // empty' 2>/dev/null || true)

[ -z "${file}" ] && exit 0
[ ! -f "${file}" ] && exit 0

# Find the most recent snapshot of this file.
base="$(basename "${file}")"
latest_snap="$(ls -1t "${SNAP_DIR}"/*-"${base}".bak 2>/dev/null | head -1)"
[ -z "${latest_snap}" ] && exit 0

# Compute the unified diff (truncate at 200 lines to keep memory.md sane).
diff_out="$(diff -u "${latest_snap}" "${file}" 2>/dev/null | head -200)"
[ -z "${diff_out}" ] && exit 0

ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
{
  echo ""
  echo "## ${ts} — ${file}"
  echo ""
  echo '```diff'
  echo "${diff_out}"
  echo '```'
} >> "${MEM_FILE}" 2>/dev/null || true

exit 0
