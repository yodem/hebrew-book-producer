#!/usr/bin/env bash
# voice-migrate.sh — silent legacy migration on first run after voice v1 ships.
# Idempotent. Detects legacy artifacts in either plugin's project layout and migrates them.

set -euo pipefail

root="${VOICE_PROJECT_ROOT:-$(pwd)}"

# Profile scope: only run in projects that actually use one of the plugins
if [[ ! -f "$root/.academic-writer/profile.json" \
   && ! -f "$root/AUTHOR_VOICE.md" \
   && ! -f "$root/book.yaml" ]]; then
  exit 0
fi

voice_dir="$root/.voice"
mkdir -p "$voice_dir/legacy" "$voice_dir/interview"
marker="$voice_dir/.migrated"

if [[ -f "$marker" ]]; then
  echo "voice-migrate: already migrated ($(cat "$marker")); skipping"
  exit 0
fi

profile="$root/AUTHOR_VOICE.md"
seeded=0

# Academic Helper legacy: .academic-writer/profile.json
aw_profile="$root/.academic-writer/profile.json"
if [[ -f "$aw_profile" ]]; then
  cp "$aw_profile" "$voice_dir/legacy/profile.json"
  python3 - <<'PYEOF' "$aw_profile" "$profile"
import json, sys, datetime
src, dst = sys.argv[1], sys.argv[2]
with open(src) as f:
    d = json.load(f)
voice = d.get("voice", {}) or {}
fp = d.get("style_fingerprint", {}) or {}
writer = d.get("writer_name", "<unknown>")
today = datetime.date.today().isoformat()
lines = [
    f"> Updated {today} by academic-writer (migrated from profile.json)",
    "",
    f"# Voice Profile — {writer}",
    "",
    "## Core voice (cross-project)",
    "",
]
if voice.get("register"):
    lines.append(f"- Register: {voice['register']}")
if voice.get("banned_words"):
    lines.append("")
    lines.append("### Banned words")
    for w in voice["banned_words"]:
        lines.append(f"- {w}")
if voice.get("phrase_bank"):
    lines.append("")
    lines.append("### Phrase bank")
    for p in voice["phrase_bank"]:
        lines.append(f"- {p}")
lines += ["", "## Terminology", "", "_Migrated; populate via `:voice` Stage 2._", ""]
lines += ["## Academic-specific", ""]
if fp.get("avg_sentence_len"):
    lines.append(f"- Average sentence length: {fp['avg_sentence_len']} words")
if fp.get("preferred_connectives"):
    lines.append("- Preferred connectives: " + ", ".join(fp["preferred_connectives"]))
lines += ["", "## Non-fiction-book-specific", "", "_Empty — populated when same writer uses hebrew-book-producer._", ""]
with open(dst, "w") as f:
    f.write("\n".join(lines) + "\n")
# Strip voice fields from original profile.json
d["voice"] = "see ./AUTHOR_VOICE.md (migrated " + today + ")"
d.pop("style_fingerprint", None)
with open(src, "w") as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
PYEOF
  seeded=1
fi

# hebrew-book-producer legacy: AUTHOR_VOICE.md at root (already there!), no migration content needed
# Just archive a copy and reformat to four-section structure.
hb_profile="$root/AUTHOR_VOICE.md"
if [[ -f "$hb_profile" && "$seeded" -eq 0 ]]; then
  cp "$hb_profile" "$voice_dir/legacy/AUTHOR_VOICE.md"
  python3 - <<'PYEOF' "$hb_profile"
import sys, datetime, re
path = sys.argv[1]
text = open(path).read()
today = datetime.date.today().isoformat()
# If already four-section structure, just stamp.
if all(s in text for s in ("## Core voice", "## Terminology",
                            "## Academic-specific", "## Non-fiction-book-specific")):
    if not text.startswith("> Updated"):
        text = f"> Updated {today} by hebrew-book-producer (re-stamped)\n\n" + text
    open(path, "w").write(text)
    sys.exit(0)
# Otherwise, wrap legacy content under "## Non-fiction-book-specific"
writer = "<unknown>"
m = re.search(r"#\s*Voice Profile\s*—\s*(.+)", text)
if m: writer = m.group(1).strip()
new = f"""> Updated {today} by hebrew-book-producer (migrated from legacy AUTHOR_VOICE.md)

# Voice Profile — {writer}

## Core voice (cross-project)

_Empty — populate via `:voice` Stage 2._

## Terminology

_Empty._

## Academic-specific

_Empty — populated when same writer uses Academic Helper._

## Non-fiction-book-specific

{text.strip()}
"""
open(path, "w").write(new)
PYEOF
  seeded=1
fi

date -u +"%Y-%m-%dT%H:%M:%SZ" > "$marker"
if [[ "$seeded" -eq 1 ]]; then
  echo "voice-migrate: migrated legacy artifacts to AUTHOR_VOICE.md"
else
  echo "voice-migrate: no legacy artifacts found; recorded marker"
fi
