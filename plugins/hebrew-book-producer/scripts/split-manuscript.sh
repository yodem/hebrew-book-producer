#!/usr/bin/env bash
# split-manuscript.sh — entry point for the manuscript splitter.
# Calls split_manuscript.py and prints a Hebrew confirmation summary.
#
# Usage:
#   split-manuscript.sh <input> [--out <dir>] [--quiet]
#
# Where <input> is a folder, .md, or .docx file.
# --quiet skips the post-split summary (used by orchestrator).

set -euo pipefail

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(dirname "$(dirname "$(realpath "$0")")")}"
SPLITTER_PY="${PLUGIN_ROOT}/scripts/split_manuscript.py"

if [ ! -x "${SPLITTER_PY}" ]; then
  echo "error: ${SPLITTER_PY} not found or not executable" >&2
  exit 2
fi

INPUT=""
OUT_DIR=".book-producer"
QUIET=0

while [ $# -gt 0 ]; do
  case "$1" in
    --out)
      OUT_DIR="$2"
      shift 2
      ;;
    --quiet)
      QUIET=1
      shift
      ;;
    -*)
      echo "unknown flag: $1" >&2
      exit 2
      ;;
    *)
      if [ -z "${INPUT}" ]; then
        INPUT="$1"
      else
        echo "unexpected positional arg: $1" >&2
        exit 2
      fi
      shift
      ;;
  esac
done

if [ -z "${INPUT}" ]; then
  echo "usage: split-manuscript.sh <input> [--out <dir>] [--quiet]" >&2
  exit 2
fi

python3 "${SPLITTER_PY}" "${INPUT}" --out "${OUT_DIR}"

if [ "${QUIET}" -eq 1 ]; then
  exit 0
fi

N_CHUNKS=$(python3 -c "import json,sys; d=json.load(open('${OUT_DIR}/manuscript-index.json')); print(len(d['chunks']))")
STRATEGY=$(python3 -c "import json,sys; d=json.load(open('${OUT_DIR}/manuscript-index.json')); print(d['split_strategy'])")
echo "זיהיתי ${N_CHUNKS} פרקים (split: ${STRATEGY})."
echo "כדי לראות את הרשימה: cat ${OUT_DIR}/manuscript-index.json"
