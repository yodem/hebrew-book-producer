#!/usr/bin/env bash
# trove-fetch.sh <id> <out-file>: write a whole Trove book to <out-file> (for agents and commands).
# Exits 1 if the trove CLI is missing or the read fails; the caller decides whether to stub.
set -u
[ $# -eq 2 ] || { echo "usage: trove-fetch.sh <id> <out-file>" >&2; exit 2; }
. "${BASH_SOURCE[0]%/*}/trove-lib.sh"
trove_fetch "$1" "$2"
