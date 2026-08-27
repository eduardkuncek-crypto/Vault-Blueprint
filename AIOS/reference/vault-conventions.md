---
title: vault-conventions
tags:
  - reference
---

# vault-conventions.md

> [!important] Opened on demand, never boot-loaded
> Mechanics for *writing* a note — naming, tags, status values, daily-note
> anatomy. `AIOS/vault-map.md` keeps a one-line pointer here so this doesn't
> have to load every session. Read this before creating or editing a note,
> or let the `vault-librarian` skill open it for you.

## Naming and structure conventions

| Thing | Convention |
|---|---|
| Daily notes | `YYYY-MM-DD.md` in `Calendar/Daily/` |
| Weekly reviews | `YYYY-Wnn.md` (ISO week) in `Calendar/Weekly/` |
| Event notes | `Calendar/Events/YYYY/<Title>.md` — created by `event.py`, never by hand |
| Project notes | Title Case, named after the project, in `Efforts/` |
| Knowledge notes | Named after the concept, sentence case: `Systemd units.md` |
| Media notes | The actual title, exactly as written: `The Left Hand of Darkness.md` |
| Index notes | Named after their folder: `Atlas/Atlas.md`, `Efforts/Efforts.md` |
| Frontmatter | Every note has `title` and `tags`. Projects add `status` and `started`. |
| Links | Wikilinks internally (`[[Note name]]`), `[text](url)` for external only |
| Accented characters in filenames | Avoid them — safer across tools and sync clients. Accents are fine in note titles and body text. |

Full naming scheme, and how to check a subject doesn't already have a note:
[[naming]].

### Anatomy of a daily note — three sections, three owners

A daily note has `## Brief`, `## Diary` and `## Changes`, and they are
**not** interchangeable:

| Section | Who writes it | What goes in it |
|---|---|---|
| `## Brief` | The `daily-brief` routine | Weather, calendar, deadlines, project momentum, one suggested focus |
| `## Diary` | **You** — and the AI, for real-life things you mention | What actually happened that day, one plain line per event, no timestamp, no marker. `diary.py` writes here; `AIOS/generated/happened.md` indexes every line ever written so "when did I…" is a lookup, not a guess. |
| `## Changes` | `AIOS/scripts/logchange.py` | One timestamped line per vault write — what changed and which file. **Receipts, not content.** |

> [!warning] `## Changes` is not storage
> The line says *what* changed and *where*. The fact itself lives in its
> subject note. An AI that starts putting facts directly into `## Changes`
> has rebuilt the catch-all file `me.md` bans, just spread across ninety
> dated files.

> [!tip] Why "Diary", not "Log"
> A section literally named `## Log` tends to fill up with the AI narrating
> its own vault work — which is what `## Changes` is already for. Naming it
> `## Diary` makes the ownership obvious: this section is about your life,
> not the AI's bookkeeping.

### Tag scheme

- **Type:** `#index`, `#project`, `#knowledge`, `#reference`, `#media`, `#world`,
  `#radar`, `#about-me`, `#daily`, `#weekly`, `#clipping`, `#generated`, `#event`
- **Domain:** add your own — `#linux`, `#selfhosting`, `#music`, `#work`,
  whatever your life actually contains. Don't keep tags you never use.
- **Media subtype** (on `Atlas/Media/` notes, alongside `#media`): `#book`,
  `#film`, `#show`, `#game`, and so on
- Status lives in frontmatter, not in tags.

### Status vocabulary — per folder

`AIOS/scripts/vault-check.py` enforces this table. If you change it here,
change it there too.

| Folder | Allowed `status:` values |
|---|---|
| `Efforts/` | `active` · `planned` · `upcoming` · `stalled` · `parked` · `done` |
| `Atlas/Media/` | `watching` · `reading` · `playing` · `finished` · `dropped` · `on hold` |
| `Atlas/Worlds/` | `active` · `parked` · `dead` · `unconfirmed` |
| `Calendar/Events/` | `upcoming` · `happening` · `done` · `cancelled` — derived automatically by `event.py --sync`; `cancelled` is the one value a human sets that a sync never overwrites |

`stalled` means: it has a real next action and nothing is happening. That's a
different problem from `parked`, which means it's deliberately off. Keeping them
separate is the point — one needs a nudge, the other needs leaving alone.

### Knowledge vs Reference — the boundary blurs, so here's the test

*Would I re-read this to understand something, or to copy a command out of it?*
Understanding → `Knowledge/`. Copying → `Reference/`.

In practice `Reference/` swallows almost everything, and that's survivable.
Wikilinks resolve by filename in Obsidian, so a note in the "wrong" folder isn't
broken — it's just untidy. Don't spend an afternoon reorganising this.

### Live views — use a `.base`, not `dataview`

**Dataview is a community plugin and isn't installed by default.** A
` ```dataview ` block in a vault without it renders as a grey box that links
nothing — which silently breaks index notes, and you won't notice for weeks.

**Bases** is a core Obsidian plugin and is enabled out of the box. Use it. Create
a `.base` file and embed it in the folder's index note with `![[Name.base]]`. A
folder whose index embeds a base never needs its list updated by hand again.

Suggested ones to make once you have notes: `Efforts/Efforts.base` (projects by
status), `Atlas/Media/Media.base` (what you're on right now).

## Related

- [[vault-map]] — the folder map, and where to look for what
- [[naming]] — the naming scheme in full, and the duplicate-note check
- [[me]]
