---
name: changes-schema
description: Defines the `changes.json` output schema for editorial agents (literary-editor, linguistic-editor, proofreader). Invoke when an editorial agent is about to write its structured output, or when production-manager is validating an incoming changes.json. Do NOT use for prose review or state management — this skill defines the handoff contract only.
user-invocable: false
---

# changes-schema — structured editorial handoff

## When to invoke

- An editorial agent (literary-editor, linguistic-editor, proofreader) is writing its `changes.json` output.
- Production-manager is validating or merging a `changes.json` from a sub-agent.

## JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["agent", "chapter", "changes", "state_transition"],
  "properties": {
    "agent": {
      "enum": ["literary-editor", "linguistic-editor", "proofreader"]
    },
    "chapter": {"type": "string"},
    "run_id": {"type": "string"},
    "changes": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["file", "type", "rationale"],
        "properties": {
          "file": {"type": "string"},
          "line_start": {"type": "integer"},
          "line_end": {"type": "integer"},
          "type": {
            "enum": [
              "typo", "punctuation", "word", "sentence",
              "register", "structural", "cut", "move",
              "TK", "voice-flag", "idea-flag"
            ]
          },
          "level": {"enum": ["letter", "word", "sentence", "idea"]},
          "before": {"type": "string"},
          "after": {"type": "string"},
          "rationale": {"type": "string"}
        }
      }
    },
    "state_transition": {
      "type": "object",
      "required": ["chapter", "next_stage"],
      "properties": {
        "chapter": {"type": "string"},
        "next_stage": {
          "enum": [
            "literary", "linguistic", "proofread-1",
            "typeset", "proofread-2-pending", "done"
          ]
        }
      }
    },
    "summary": {
      "type": "string",
      "description": "5-line Hebrew report per report.md shape in PIPELINE.md"
    }
  }
}
```

## Change type reference

| type | used by | meaning |
|---|---|---|
| `typo` | proofreader | spelling / letter error |
| `punctuation` | proofreader | missing or wrong punctuation |
| `word` | linguistic-editor, proofreader | word substitution |
| `sentence` | linguistic-editor | sentence-level rewrite or restructure |
| `register` | linguistic-editor | register mismatch fixed |
| `structural` | literary-editor | section or paragraph moved / reordered |
| `cut` | literary-editor | material removed |
| `move` | literary-editor | material moved to another position |
| `TK` | literary-editor | gap marked "to come" for author to fill |
| `voice-flag` | any | potential voice violation — author must approve |
| `idea-flag` | proofreader | idea-level inconsistency — not auto-fixed |

## Sample objects

### Literary-editor structural cut

```json
{
  "file": "chapters/ch03.md",
  "line_start": 120,
  "line_end": 135,
  "type": "cut",
  "level": "idea",
  "before": "הפסקה שמתחילה ב'יתרה מכך, הנושא של הזהות...'",
  "after": null,
  "rationale": "חוזרת על חומר שכבר נאמר בפסקה 3 — פגיעה בקצב"
}
```

### Linguistic-editor word substitution

```json
{
  "file": "chapters/ch05.md",
  "line_start": 44,
  "line_end": 44,
  "type": "word",
  "level": "word",
  "before": "לפיכך",
  "after": "לכן",
  "rationale": "register: journalistic — 'לכן' matches the chapter's declared register; 'לפיכך' is literary-formal"
}
```

### Proofreader typo

```json
{
  "file": "chapters/ch02.md",
  "line_start": 78,
  "line_end": 78,
  "type": "typo",
  "level": "letter",
  "before": "המחשבות",
  "after": "המחשבות",
  "rationale": "doubled ו — should be 'המחשבות'"
}
```

## How to write `changes.json`

Each editorial agent writes its output to:
```
.book-producer/runs/<run-id>/<agent-name>/changes.json
```

The `run-id` is an ISO-like timestamp (e.g., `20260501-140000`) assigned by production-manager at spawn time and passed to the sub-agent as context.

## Hard rules

- Every change object MUST have `file`, `type`, and `rationale`.
- `before` and `after` are optional for `TK`, `idea-flag`, `voice-flag` (which flag without changing text).
- `idea-flag` and `voice-flag` changes are NEVER auto-applied — they surface in `PROOF_NOTES.md` or `LITERARY_NOTES.md` for human review.
- Production-manager validates schema before merging. Malformed files → logged to `errors.log`, human review required.
