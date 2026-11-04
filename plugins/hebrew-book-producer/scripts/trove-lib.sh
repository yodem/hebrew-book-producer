#!/usr/bin/env bash
# trove-lib.sh: shared Trove helpers for the loaders. Source it; do not run it.
#
#   trove_find_by_title <exact title>   prints the id of the one readable book with that title;
#                                       returns 1 when there is none, 2 on error or ambiguity
#   trove_fetch <id> <out-file>         writes the whole book to <out-file>, following the
#                                       "Next: trove items read ..." line that ends a partial read
#
# Both return non-zero on any failure and never print secrets.

# Trove ids are lowercase alphanumeric; anything else is refused before it reaches a command.
trove_valid_id() { [[ "${1:-}" =~ ^[a-z0-9]{10,40}$ ]]; }

# `trove items list --json` returns {"items": [...]}; older builds returned a bare array.
# Locked books stay in the list but cannot be read, so they are skipped.
trove_find_by_title() {
  local title="$1"
  command -v trove >/dev/null 2>&1 || return 2
  command -v jq >/dev/null 2>&1 || return 2
  local ids listing
  listing=$(trove items list --json --no-session 2>/dev/null) || return 2
  printf '%s' "$listing" | jq -e 'type == "object" or type == "array"' >/dev/null 2>&1 || return 2
  # A matching book that is locked exists but cannot be read: that is an error, not a miss.
  if printf '%s' "$listing" | jq -e --arg t "$title" \
      '[(if type == "object" then .items else . end)[] | select(.title == $t)] | (length > 0 and all(.locked == true))' >/dev/null 2>&1; then
    echo "WARN: the Trove book titled '$title' is locked" >&2
    return 2
  fi
  ids=$(printf '%s' "$listing" | jq -r --arg t "$title" \
    '[(if type == "object" then .items else . end)[] | select(.title == $t and (.locked != true)) | .id] | sort | .[]' 2>/dev/null) || return 2
  [ -n "$ids" ] || return 1
  if [ "$(printf '%s\n' "$ids" | wc -l | tr -d ' ')" -gt 1 ]; then
    echo "WARN: several readable Trove books are titled '$title'; refusing to guess. Rename or remove the extra copies." >&2
    return 2
  fi
  trove_valid_id "$ids" || return 2
  printf '%s\n' "$ids"
}

# _trove_read_retry <out> <id> <args...>: one read, retried up to 3 times on "Too many requests".
_trove_read_retry() {
  local out="$1"; shift
  local id="$1"; shift
  local try err
  for try in 1 2 3 4; do
    err=$(trove items read "$id" "$@" --no-session 2>&1 > "$out") && return 0
    case "$err" in *"Too many requests"*) sleep $((try * 3)) ;; *) return 1 ;; esac
  done
  return 1
}

trove_fetch() {
  local id="$1" out="$2" tmp part last next prefix ver first_ver=""
  trove_valid_id "$id" || { echo "WARN: not a Trove id: '$id'" >&2; return 1; }
  command -v trove >/dev/null 2>&1 || return 1
  tmp=$(mktemp) || return 1
  part=$(mktemp) || { rm -f "$tmp"; return 1; }
  local -a args=(--pages all)
  local i
  for i in $(seq 1 100); do
    if ! _trove_read_retry "$part" "$id" "${args[@]}"; then
      rm -f "$tmp" "$part"; return 1
    fi
    last=$(grep -v '^[[:space:]]*$' "$part" | tail -1)
    # Only the last line counts, and it must name this book.
    # Accept only a strict page spec for this same id; book text is never parsed as a command.
    next=""
    prefix="Next: trove items read ${id} "
    if [[ "$last" =~ ^(Stopped|Not\ read\ yet|.*continues) && "$last" == *"$prefix"* ]]; then
      next="${last##*"$prefix"}"
      next="${next%"${next##*[![:space:]]}"}"
      [[ "$next" =~ ^--pages\ ([0-9]+(-[0-9]+)?(,[0-9]+(-[0-9]+)?)*|all)(\ --part\ [0-9]+)?$ ]] || next=""
    fi
    # All parts must come from the same version of the book.
    ver=$(grep -m1 -E '^Version: [0-9]+' "$part" | tr -dc '0-9')
    if [ "$i" -eq 1 ]; then first_ver="$ver"
    elif [ "$ver" != "$first_ver" ]; then
      echo "WARN: $id changed during the read (version $first_ver -> $ver); try again" >&2
      rm -f "$tmp" "$part"; return 1
    fi
    # Every part repeats the read header; keep it only on the first part.
    if [ "$i" -gt 1 ]; then
      _trove_strip_header "$part" || { rm -f "$tmp" "$part"; return 1; }
    fi
    if [ -z "$next" ]; then
      cat "$part" >> "$tmp" && mv "$tmp" "$out" || { rm -f "$tmp" "$part"; return 1; }
      rm -f "$part"
      return 0
    fi
    if [ "$next" = "${args[*]}" ]; then
      echo "WARN: trove read of $id repeats '$next'; stopping" >&2
      rm -f "$tmp" "$part"; return 1
    fi
    grep -vxF "$last" "$part" >> "$tmp" || [ $? -eq 1 ] || { rm -f "$tmp" "$part"; return 1; }
    read -r -a args <<< "$next"
  done
  echo "WARN: trove read of $id did not finish after 100 parts" >&2
  rm -f "$tmp" "$part"; return 1
}

# _trove_strip_header <file>: drop a leading "────" / title / ID / Version / "────" block in place.
_trove_strip_header() {
  local f="$1" t
  t=$(mktemp) || return 1
  # Leading blank lines, then the header block, then the blank lines after it.
  awk 'state == 0 && /^[[:space:]]*$/ { next }
       state == 0 && /^(─)+$/ { state = 1; next }
       state == 0 { state = 3; print; next }
       state == 1 { if ($0 ~ /^(─)+$/) state = 2; next }
       state == 2 && /^[[:space:]]*$/ { next }
       { state = 3; print }' "$f" > "$t" && mv "$t" "$f" || { rm -f "$t"; return 1; }
}

# trove_body <in> <out>: strip the read header and "── Page N ──" markers from a
# trove_fetch file, leaving the book's own markdown (pages were split on "# " headings).
trove_body() {
  awk '
    hdr < 2 { if ($0 ~ /^(─)+$/) { hdr++; if (hdr == 2) skipblank = 1 }; next }
    /^── Page [0-9]+( \(part [0-9]+ of [0-9]+\))? ──$/ { skipblank = 1; next }
    skipblank && /^[[:space:]]*$/ { skipblank = 0; next }
    { skipblank = 0; print }
  ' "$1" > "$2"
}
