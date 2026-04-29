---
name: hebrew-connectives
description: Hebrew logical-connector reference for editorial work. Maps logical relations (Addition / Contrast / Cause / Result / Concession) to the correct Hebrew connector. Used by linguistic-editor to verify that connectors actually match the relation they introduce.
user-invocable: false
---

# hebrew-connectives — using the right מילת קישור

## When to invoke

- Linguistic-editor encounters a sentence that uses a connector — verify the connector matches the relation.
- Author or AI used "אולם" where "לכן" was meant — flag the mismatch.

## Reference table

The single source of truth is [`references/connectives-table.md`](./references/connectives-table.md). All editorial work MUST reference that table — do not invent connectors from memory.

## How to use this skill

1. Identify the **logical relation** the writer is trying to introduce (Addition / Contrast / Cause / Result / Concession).
2. Look up the appropriate connectors in the table.
3. Verify the connector in the manuscript is in the right column.
4. If not, propose a replacement.

## Common error patterns

| Wrong | Why wrong | Suggest |
|---|---|---|
| "אולם, נוסף על כך…" | "אולם" is contrast; "נוסף על כך" is addition. They contradict in the same sentence. | Pick one relation. |
| "ולפיכך, מנגד…" | Same — Result + Contrast in one breath. | Pick one. |
| "שכן, מאידך גיסא" | Cause + Contrast. | Pick one. |

## Frequency rule

A 24,000-character chapter (one printing sheet / גיליון דפוס) should contain roughly **4–8 instances of each relation**, not bunched. If you see 6 contrast connectors in 3 paragraphs and zero cause connectors anywhere, the argument structure is unbalanced — flag for the literary-editor.

## Hard rules

- The table is authoritative. Do not invent connectors.
- A connector must match its relation. No exceptions.
- "אבל" is informal; its formal equivalent is "אולם" or "ברם". Match register.
