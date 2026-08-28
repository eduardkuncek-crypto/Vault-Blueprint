---
title: Events
tags:
  - index
  - event
---

# Events

Dated things that aren't projects and aren't diary entries: a trip, an
appointment, an exam week. One note per event, `Calendar/Events/YYYY/<Title>.md`.

**Never create one by hand.** Use `event.py` — it writes the note *and* links
it into every daily note it covers:

```
python3 AIOS/scripts/event.py "<Title>" --start YYYY-MM-DD [--end YYYY-MM-DD / --open] --where "..."
python3 AIOS/scripts/event.py --today       # what's on today
python3 AIOS/scripts/event.py --upcoming 14 # the next two weeks
```

## Events

| Title | Dates | Status |
|---|---|---|
| | | |

> [!note] This folder stays empty until you use it
> Nothing creates an event automatically. The first row shows up the moment
> you run `event.py` for something real.

Template: `AIOS/templates/event-note.md`

## Related

- [[Calendar]]
