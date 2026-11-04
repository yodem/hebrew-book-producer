#!/usr/bin/env bash
# load-agent-instructions.sh — fetch a per-agent instruction page from Trove (formerly CandleKeep).
#
# Usage: load-agent-instructions.sh <agent_key>
#
# Reads book.yaml -> agent_instructions.<agent_key>, fetches the Trove
# item by ID, writes to .ctx/<agent-key-dashed>-instructions.md.
#
# No-op if:
#   - book.yaml is missing
#   - agent_instructions.<agent_key> is missing or null
#   - the cache file already exists (idempotent for parallel sub-agents)
#
# Fail-open: on Trove error, write a stub and exit 0.

set -u

# shellcheck source=trove-lib.sh
. "${BASH_SOURCE[0]%/*}/trove-lib.sh"

AGENT_KEY="${1:-}"
if [ -z "${AGENT_KEY}" ]; then
  echo "usage: load-agent-instructions.sh <agent_key>" >&2
  exit 2
fi

CACHE_NAME="${AGENT_KEY//_/-}-instructions.md"
CACHE_FILE=".ctx/${CACHE_NAME}"

if [ -f "${CACHE_FILE}" ]; then
  exit 0
fi

if [ ! -f book.yaml ]; then
  echo "WARN: no book.yaml in $(pwd); skipping ${AGENT_KEY}" >&2
  exit 0
fi

if ! command -v yq >/dev/null 2>&1; then
  echo "WARN: yq not installed; cannot read book.yaml" >&2
  exit 0
fi

INSTR_ID=$(yq ".agent_instructions.${AGENT_KEY} // \"\"" book.yaml 2>/dev/null | tr -d '"')

if [ -z "${INSTR_ID}" ] || [ "${INSTR_ID}" = "null" ]; then
  echo "WARN: no agent_instructions.${AGENT_KEY} in book.yaml; skipping" >&2
  exit 0
fi

mkdir -p .ctx

if ! command -v trove >/dev/null 2>&1; then
  echo "WARN: trove CLI not installed; writing stub for ${AGENT_KEY}" >&2
  cat > "${CACHE_FILE}" <<STUB
# ${AGENT_KEY} instructions — UNAVAILABLE

trove CLI is not installed; Trove item \`${INSTR_ID}\` could not be fetched.
[UNVERIFIED — agent should fall back to general session-cached references]
STUB
  exit 0
fi

if ! trove_fetch "${INSTR_ID}" "${CACHE_FILE}"; then
  echo "WARN: trove read of ${INSTR_ID} failed; writing stub" >&2
  cat > "${CACHE_FILE}" <<STUB
# ${AGENT_KEY} instructions — UNAVAILABLE

Trove item \`${INSTR_ID}\` could not be fetched.
[UNVERIFIED — agent should fall back to general session-cached references]
STUB
  exit 0
fi

CHARS=$(wc -c < "${CACHE_FILE}" | tr -d ' ')
if [ "${CHARS}" -lt 50 ]; then
  echo "WARN: ${INSTR_ID} returned <50 chars; treating as unavailable" >&2
fi

exit 0
