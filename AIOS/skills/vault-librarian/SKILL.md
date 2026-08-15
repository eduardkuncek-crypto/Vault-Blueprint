---
name: "vault-librarian"
description: "Conventions for writing notes into the user's Obsidian vault — which folder a note belongs in, required frontmatter, tag scheme, file naming, linking rules, and how to create a new home when a fact doesn't fit anywhere. Use whenever creating, editing, moving, or naming any note in the vault, when the user says \"write this down\" / \"save this\" / \"make a note\", or when unsure where something goes."
---

# Vault Librarian

Conventions for the user's Obsidian vault. Follow these without being asked.

Read `AIOS/vault-map.md` before placing a note anywhere unfamiliar.

## Where a note goes

Ask one question: **what kind of thing is this?**

| The note is... | It goes in |
|---|---|
| A fact about them as a person — grades, family, routine, money, opinions, tastes, habits, how they want to be worked with | `Atlas/About Me/` |
| Something they watch, read or play | `Atlas/Media/<Title>.md` |
| Game world / save / server state — coordinates, seeds, mods, versions | `Atlas/Worlds/<World>.md` |
| Them working to understand a concept | `Atlas/Knowledge/` |
| Something they'll look up, not read — specs, cheatsheets, their own hardware | `Atlas/Reference/` |
| Saved from the web | `Atlas/Clippings/` |
| Something they're curious about but haven't started | A row in `Atlas/Radar.md` (not a new note) |
| Tied to a specific date | `Calendar/Daily/` or `Calendar/Weekly/` |
| A project with a next action | `Efforts/` |
| About the AI setup itself | `AIOS/` |

## If it fits none of those — make a home. Don't ask, don't skip.

**You have permission to create structure.** Use it rather than stalling. The
escalation:

1. **A note already exists for the subject** → append to it.
2. **The category exists but the note doesn't** → create the note in that folder,
   and add it to that folder's index table.
3. **The category itself doesn't exist** → create a new subfolder under `Atlas/`,
   give it an index note named after the folder, and register it in **both**
   `Atlas/Atlas.md` and `AIOS/vault-map.md`.
4. **Genuinely a one-off with no subject** → today's daily note, under `## Log`.

Never let "there's nowhere for this" become a reason a fact is lost. A three-line
note linked to an index beats a fact appended to something unrelated, and beats
no note at all.

**Do not create a new *top-level* folder** (a sibling of `Atlas/`, `Calendar/`,
`Efforts/`, `AIOS/`, `Privat/`) without asking — that changes the ACE structure
the vault is built on. New subfolders inside `Atlas/` are fine and expected.

## Every note gets

- Frontmatter with at least `title` and `tags`
- At least one wikilink to a related note, and a link **up** to its index.
  **No orphans.**
- A row in its folder's index table, where that folder has one
- A filename without accented characters — safer across tools and sync clients.
  Accents are fine in the title field and in body text.

## Naming

| Kind | Pattern | Example |
|---|---|---|
| Daily note | `YYYY-MM-DD.md` | `2026-07-30.md` |
| Weekly review | `YYYY-Wnn.md` | `2026-W31.md` |
| Project | Title Case | `Home Server.md` |
| Knowledge note | Sentence case, named after the concept | `Systemd units.md` |
| Media note | The actual title | `The Left Hand of Darkness.md` |
| About Me note | Sentence case, named after the subject | `Daily routine.md` |
| Index note | Same name as its folder | `Atlas/Atlas.md`, `Atlas/About Me/About Me.md` |

## Tags

- **Type:** `#index` `#project` `#knowledge` `#daily` `#weekly` `#clipping`
  `#radar` `#media` `#world` `#about-me` `#reference`
- **Domain:** whatever the user's life actually contains. Add them as needed;
  delete ones that never get used.

Status goes in frontmatter, never in tags. Allowed values per folder are in
`AIOS/vault-map.md`, and `AIOS/scripts/vault-check.py` enforces them.

## Templates

Reuse these rather than inventing a structure:

- `AIOS/templates/project.md`
- `AIOS/templates/learn-note.md`
- `AIOS/templates/media-note.md`
- `AIOS/templates/daily-note.md`
- `AIOS/templates/weekly-review.md`

## Hard rules

1. **Never read or write anything under `Privat/`.** Not to check, not to index,
   not to summarise. Nothing.
2. **Never overwrite a daily note.** Append under the existing heading.
3. **Ask before deleting or moving** an existing note. Creating and appending is
   fine, and creating is encouraged.
4. **When a decision gets made in conversation, write it into that project's
   decisions log table in `Efforts/`.** This is what stops the next session
   re-arguing settled questions.
5. **Never say a note was written before the write succeeded.** See Rule Zero in
   `auto-capture`. Write, confirm, then say so, naming the file.

## Keep the maps honest

If you add a note in a place the vault map doesn't describe, or create a new
folder, or notice a fact in `AIOS/vault-map.md` that no longer matches reality —
**fix the map in the same turn.** A stale map is worse than no map: it sends the
next session to the wrong place confidently.

## Related

Full detail: `AIOS/vault-map.md`. Working style: `AIOS/me.md`. What to capture
and when: the `auto-capture` skill.
