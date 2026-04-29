#!/usr/bin/env bash
# load-candlekeep-guide.sh — fetch the canonical writer's guide from CandleKeep
# and cache it to .ctx/writers-guide.md in the project root.
#
# CandleKeep item ID: cmok9h0m10ahik30zt8yt0lt2
# ("The Writer's Guide: How to Write, Edit, and Proofread a Book" — v2)
#
# Fail-open: if CandleKeep is unavailable, write a stub and exit 0 so the
# pipeline continues in degraded mode.

set -u

GUIDE_ID="cmok9h0m10ahik30zt8yt0lt2"
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
CTX_DIR="${PROJECT_ROOT}/.ctx"
GUIDE_FILE="${CTX_DIR}/writers-guide.md"

mkdir -p "${CTX_DIR}"

# If we already cached it this session and it's non-empty, skip.
if [ -s "${GUIDE_FILE}" ]; then
  age_seconds=$(( $(date +%s) - $(stat -f %m "${GUIDE_FILE}" 2>/dev/null || stat -c %Y "${GUIDE_FILE}" 2>/dev/null || echo 0) ))
  # Re-fetch if older than 12 hours; otherwise reuse.
  if [ "${age_seconds}" -lt 43200 ]; then
    echo "writers-guide cached (age: ${age_seconds}s) — skipping fetch"
    exit 0
  fi
fi

# Try to fetch via ck CLI.
if command -v ck >/dev/null 2>&1; then
  if ck items get "${GUIDE_ID}" > "${GUIDE_FILE}" 2>/dev/null; then
    chars=$(wc -m < "${GUIDE_FILE}" | tr -d ' ')
    if [ "${chars}" -gt 1000 ]; then
      echo "writers-guide cached: ${chars} chars from CandleKeep item ${GUIDE_ID}"
      exit 0
    fi
  fi
fi

# Fail-open: write a stub.
cat > "${GUIDE_FILE}" <<'STUB'
# Writer's Guide — STUB

CandleKeep is not available in this session.

The plugin runs in degraded mode without craft references from
King, Zinsser, Penn, Shapiro, or the Hebrew editorial conventions.

To enable:
  1. Install CandleKeep CLI: see https://candlekeep.cloud
  2. Run `ck auth login`
  3. Verify item access: `ck items get cmok9h0m10ahik30zt8yt0lt2`

Continuing without the guide. Editorial agents will rely on their
built-in instructions only.
STUB

echo "writers-guide stub written (CandleKeep unavailable)"
exit 0
