#!/usr/bin/env bash
# verify-citation.sh — validate a Hebrew religious citation against Sefaria.
#
# Usage: verify-citation.sh "<reference>"
#        e.g. verify-citation.sh "Berakhot 10a"
#             verify-citation.sh "Mishneh Torah, Repentance 3:2"
#             verify-citation.sh "Genesis 1:1"
#
# Method: tries `sefaria` CLI if installed; otherwise falls back to a curl call
# against the public Sefaria API (https://www.sefaria.org/api/texts/...).
#
# Output (stdout):
#   line 1: VERIFIED | UNVERIFIED | NOT-FOUND
#   line 2: canonical-ref (Sefaria's normalised reference) or original on miss
#   line 3+: notes (if any)
#
# Exit codes: 0 = verified, 1 = not found, 2 = no network / no tool, 3 = bad input.
#
# Designed to be called from the hazal-citation skill or proofreader agent
# *only when MCP tooling is unavailable* — the agent should prefer the
# Sefaria MCP tools when running inside Claude Code.

set -u

if [ $# -ne 1 ] || [ -z "${1:-}" ]; then
  echo "Usage: $0 \"<reference>\"" >&2
  exit 3
fi

ref="$1"

# Try sefaria CLI first.
if command -v sefaria >/dev/null 2>&1; then
  out=$(sefaria text "${ref}" 2>/dev/null || true)
  if [ -n "${out}" ]; then
    echo "VERIFIED"
    echo "${ref}"
    exit 0
  fi
fi

# Try public API via curl. URL-encode spaces to %20 and tabs out other unsafe chars.
if command -v curl >/dev/null 2>&1; then
  # Sefaria's URL convention replaces spaces with underscores and uses commas as-is.
  encoded=$(printf '%s' "${ref}" | sed 's/ /%20/g')
  resp=$(curl -fsSL --max-time 10 "https://www.sefaria.org/api/texts/${encoded}?context=0" 2>/dev/null || true)
  if [ -n "${resp}" ]; then
    # Look for an empty-or-missing text field. Sefaria returns {"error":"..."} on miss.
    if printf '%s' "${resp}" | grep -q '"error"'; then
      echo "NOT-FOUND"
      echo "${ref}"
      exit 1
    fi
    if printf '%s' "${resp}" | grep -q '"ref"'; then
      # Extract the canonical ref.
      canonical=$(printf '%s' "${resp}" | grep -oE '"ref"[[:space:]]*:[[:space:]]*"[^"]+"' | head -1 | sed -E 's/.*"ref"[[:space:]]*:[[:space:]]*"([^"]+)"/\1/')
      echo "VERIFIED"
      echo "${canonical:-${ref}}"
      exit 0
    fi
  fi
fi

# Neither tool nor API worked.
echo "UNVERIFIED"
echo "${ref}"
echo "Note: cannot reach Sefaria. Mark this citation [UNVERIFIED] in the manuscript."
exit 2
