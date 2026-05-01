#!/usr/bin/env bash
# load-candlekeep-guide.sh — fetch the user's curated writing-craft knowledge
# from CandleKeep and cache under .ctx/ in the project root.
#
# Design principle: CandleKeep is for the AUTHOR'S KNOWLEDGE LAYER —
# craft books, the author's own evolving thesis notebook, voice fingerprints,
# anti-AI patterns the author has flagged before, tone/style observations.
# It is NOT for canonical primary texts (Tanakh, Talmud, Rambam, etc.) —
# those live in Sefaria and are queried directly via the Sefaria MCP tool
# (mcp__claude_ai_Sefaria__get_text), the sole validator for religious sources.
#
# Always loads:
#   cmok9h0m10ahik30zt8yt0lt2  → .ctx/writers-guide.md       (King/Zinsser/Penn/Shapiro compendium)
#   cmnudfue5003rmy0zlxt7ioa1  → .ctx/agent-team-guide.md    (Building Your Agent Team)
#
# Optional, controlled by book.yaml:
#   thesis_notebook: <ck-id>          → .ctx/thesis-notebook.md
#         The author's own CandleKeep notebook for THIS book — running thesis,
#         chapter ideas, voice observations, things they want to come back to.
#         Created by the author with `ck items create` outside this plugin.
#
#   craft_extras: [<ck-id>, ...]      → .ctx/craft-extras/<id>.md
#         Additional craft references the author has curated — e.g. another
#         writing book, a style guide, a translation theory text, an idiolect
#         analysis from a previous project.
#
# Fail-open: if CandleKeep is unavailable, write a stub for missing items
# and exit 0. Idempotent: re-fetches only if cached file is older than 12h.
#
# Citation lookups (Tanakh, Bavli, Yerushalmi, Midrash, Rambam, Shulchan Arukh)
# are NOT handled by this script — they go directly to the Sefaria MCP tool
# (mcp__claude_ai_Sefaria__get_text) inside the cite-master skill.

set -u

PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
CTX_DIR="${PROJECT_ROOT}/.ctx"
mkdir -p "${CTX_DIR}/craft-extras"

# Always-on writing-craft references (verified against the user's library).
GUIDE_ID_WRITERS="cmok9h0m10ahik30zt8yt0lt2"        # The Writer's Guide
GUIDE_ID_AGENT_TEAM="cmnudfue5003rmy0zlxt7ioa1"     # Building Your Agent Team
GUIDE_ID_HE_LINGUISTICS="cmomjonvy0fdmk30zwef79c48" # Hebrew Linguistic Reference (yodem/hebrew-linguistics-data)

# fetch_guide <ID> <output-path-under-.ctx> <description>
fetch_guide() {
  local id="$1"
  local out="${CTX_DIR}/$2"
  local desc="$3"

  if [ -s "${out}" ]; then
    local age=$(( $(date +%s) - $(stat -f %m "${out}" 2>/dev/null || stat -c %Y "${out}" 2>/dev/null || echo 0) ))
    if [ "${age}" -lt 43200 ]; then
      echo "  (cached, ${age}s old)  ${desc}"
      return 0
    fi
  fi

  if command -v ck >/dev/null 2>&1; then
    if ck items get "${id}" > "${out}" 2>/dev/null; then
      local chars
      chars=$(wc -m < "${out}" | tr -d ' ')
      if [ "${chars}" -gt 100 ]; then
        echo "  fetched ${chars} chars  ${desc}"
        return 0
      fi
    fi
  fi

  cat > "${out}" <<STUB
# ${desc} — UNAVAILABLE

CandleKeep item \`${id}\` could not be loaded.
Either ck CLI is not installed, or this item is not accessible.

[UNVERIFIED — agents may not assume content from this reference is loaded]
STUB
  echo "  STUB (unavailable)  ${desc}"
}

echo "Loading CandleKeep references — author knowledge layer"
echo

# ── Always-on craft references ──────────────────────────────
fetch_guide "${GUIDE_ID_WRITERS}"        "writers-guide.md"                 "The Writer's Guide (craft)"
fetch_guide "${GUIDE_ID_AGENT_TEAM}"     "agent-team-guide.md"              "Building Your Agent Team (multi-agent design)"
fetch_guide "${GUIDE_ID_HE_LINGUISTICS}" "hebrew-linguistic-reference.md"   "Hebrew Linguistic Reference (Academy + curated blogs; shared with academic-writer)"

# ── Author's own thesis notebook (optional) ─────────────────
if [ -f "${PROJECT_ROOT}/book.yaml" ]; then
  thesis_id=$(grep -E '^thesis_notebook:[[:space:]]*' "${PROJECT_ROOT}/book.yaml" | head -1 | sed -E 's/^thesis_notebook:[[:space:]]*//; s/[[:space:]]*#.*$//; s/^"//; s/"$//' | tr -d ' ')
  if [ -n "${thesis_id}" ]; then
    fetch_guide "${thesis_id}" "thesis-notebook.md" "Author's thesis notebook (per-project)"
  fi
fi

# ── Author's curated craft extras (optional) ────────────────
if [ -f "${PROJECT_ROOT}/book.yaml" ]; then
  # Parse a YAML list:  craft_extras: [id1, id2, ...]   OR a multi-line list.
  # Tolerant single-line parser:
  extras_line=$(grep -E '^craft_extras:[[:space:]]*\[' "${PROJECT_ROOT}/book.yaml" | head -1)
  if [ -n "${extras_line}" ]; then
    ids=$(printf '%s' "${extras_line}" | sed -E 's/^craft_extras:[[:space:]]*\[//; s/\][[:space:]]*$//; s/"//g; s/,/ /g')
    for id in ${ids}; do
      [ -z "${id}" ] && continue
      fetch_guide "${id}" "craft-extras/${id}.md" "Author craft-extra: ${id}"
    done
  fi
fi

# ── Author voice profile (optional, per-project) ────────────
# Reads author_profile.overview from book.yaml and caches to .ctx/author-profile.md
if [ -f "${PROJECT_ROOT}/book.yaml" ]; then
  profile_overview_id=$(grep -A 10 '^author_profile:' "${PROJECT_ROOT}/book.yaml" \
    | grep -E '^\s+overview:' | head -1 \
    | sed -E 's/.*overview:[[:space:]]*//; s/[[:space:]]*#.*$//; s/^"//; s/"$//' | tr -d ' ')
  if [ -n "${profile_overview_id}" ] && [ "${profile_overview_id}" != '""' ]; then
    fetch_guide "${profile_overview_id}" "author-profile.md" "Author voice profile — overview"
  fi
fi

echo
echo "Done. Cached references in: ${CTX_DIR}/"
echo
echo "NOTE on canonical religious texts (Tanakh, Bavli, Yerushalmi, Midrash, Rambam, etc.):"
echo "  Those are NOT cached here. The cite-master skill queries Sefaria directly"
echo "  via the MCP tool mcp__claude_ai_Sefaria__get_text (sole validator)."
echo "  CandleKeep is for the author's curated knowledge layer (craft, thesis, voice),"
echo "  not canonical primary texts."

exit 0
