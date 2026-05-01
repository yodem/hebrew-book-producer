#!/usr/bin/env bash
# session-start.sh — runs once at the start of every Claude Code session
# in a project where this plugin is enabled. Caches the CandleKeep
# references (writers-guide, agent-team-guide, hebrew-linguistic-reference)
# under .ctx/ so every subsequent agent reads them locally — without
# depending on $CLAUDE_PLUGIN_ROOT being set in their own Bash tool calls.
#
# Hook input (JSON on stdin) is ignored; we always run.
# Hooks always exit 0 — the plugin must not block the session if
# CandleKeep is unavailable.

set -u

# Discard hook input — we don't need it here.
cat >/dev/null

# CLAUDE_PLUGIN_ROOT is reliably set by the Claude Code runtime in hook
# execution contexts.
loader="${CLAUDE_PLUGIN_ROOT:-}/scripts/load-candlekeep-guide.sh"

if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] || [ ! -x "${loader}" ]; then
  # Plugin not in expected location, or loader missing — fail open.
  exit 0
fi

# The loader writes to .ctx/ in the project root.
bash "${loader}" >/dev/null 2>&1 || true

exit 0
