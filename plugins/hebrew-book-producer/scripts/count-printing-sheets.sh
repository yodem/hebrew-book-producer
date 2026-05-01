#!/usr/bin/env bash
# count-printing-sheets.sh — compute גיליון דפוס count.
#
# Usage: count-printing-sheets.sh <file.md>
#        count-printing-sheets.sh .            # all *.md in cwd
#
# Strips YAML frontmatter and Markdown headings/structure before counting.
# Reports characters, words, sheets (24,000 chars per sheet).

set -eu

CHARS_PER_SHEET=24000

count_one() {
  local f="$1"
  if [ ! -f "${f}" ]; then
    printf "  %s — not a file\n" "${f}" >&2
    return 1
  fi

  # Strip YAML frontmatter (between leading --- pairs), then strip ATX headings,
  # blockquote markers, list markers, and Markdown emphasis tokens.
  local content
  content="$(awk '
    BEGIN { in_fm = 0; line = 0 }
    {
      line++
      if (line == 1 && $0 == "---") { in_fm = 1; next }
      if (in_fm && $0 == "---") { in_fm = 0; next }
      if (in_fm) next
      print
    }
  ' "${f}" | sed -E '
    s/^#{1,6}[[:space:]]+//
    s/^>[[:space:]]?//
    s/^[[:space:]]*[-*+][[:space:]]+//
    s/`[^`]*`//g
    s/\[([^]]+)\]\([^)]+\)/\1/g
    s/\*\*([^*]+)\*\*/\1/g
    s/\*([^*]+)\*/\1/g
  ')"

  local chars words sheets_int sheets_frac
  chars=$(printf '%s' "${content}" | wc -m | tr -d ' ')
  words=$(printf '%s' "${content}" | wc -w | tr -d ' ')
  # Two-decimal sheet count without bc (use awk).
  sheets_str=$(awk -v c="${chars}" -v cps="${CHARS_PER_SHEET}" 'BEGIN { printf "%.2f", c/cps }')

  printf "  %-50s  %8s chars  %7s words  %5s sheets\n" "${f}" "${chars}" "${words}" "${sheets_str}"

  # Emit machine-readable as well (for production-manager to parse).
  printf '{"file":"%s","chars":%s,"words":%s,"sheets":%s}\n' "${f}" "${chars}" "${words}" "${sheets_str}" >&2
}

if [ $# -eq 0 ]; then
  echo "Usage: $0 <file.md|directory>" >&2
  exit 2
fi

target="$1"
echo "## Printing-sheet count (גיליון דפוס = ${CHARS_PER_SHEET} characters)"
echo

if [ -d "${target}" ]; then
  total_chars=0
  while IFS= read -r f; do
    count_one "${f}" || true
    chars=$(printf '%s' "$(cat "${f}" 2>/dev/null)" | wc -m | tr -d ' ')
    total_chars=$((total_chars + chars))
  done < <(find "${target}" -type f -name '*.md' | sort)
  total_sheets=$(awk -v c="${total_chars}" -v cps="${CHARS_PER_SHEET}" 'BEGIN { printf "%.2f", c/cps }')
  printf "\n  %-50s  %8s chars  %12s  %5s sheets\n" "TOTAL" "${total_chars}" "" "${total_sheets}"
else
  count_one "${target}"
fi
