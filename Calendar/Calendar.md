---
title: Calendar
tags:
  - index
---

# Calendar

Anything anchored to a date.

| | |
|---|---|
| `Daily/` | `YYYY-MM-DD.md` — brief, log, and the `## Changes` audit trail |
| [[Weekly]] | `YYYY-Wnn.md` — output of `weekly-review` |
| [[Cooldowns]] | Every fixed waiting period you're inside, with its unlock date |

## Anatomy of a daily note

Three sections, three owners. They are not interchangeable.

| Section | Who writes it | What goes in it |
|---|---|---|
| `## Brief` | The `daily-brief` routine | Weather, events, deadlines, project momentum, one suggested focus |
| `## Log` | **You** — and the AI, for events | Thoughts and things that happened, timestamped `HH:MM` |
| `## Changes` | `AIOS/scripts/logchange.py` | One line per vault write. **Receipts, not content.** |

## Related

- [[Home]]
- [[vault-map]]
