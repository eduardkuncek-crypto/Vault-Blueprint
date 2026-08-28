---
title: blueprint-changes
tags:
  - reference
---

# What changed in the blueprint

This is the file that turns a pile of file diffs into a question a human can
answer. When someone runs the updater, this is what they read:

> **[3] Screenshots get their own folder**
> Right now a picture you send lands in `Inbox/` with everything else. This
> gives pictures their own home under `AIOS/history/`, writes a little note
> next to each one saying what was in it, and keeps an index of the lot. Want
> it?

Without an entry here they'd instead read *"updates the script shot.py"*, which
tells them nothing and gets declined out of caution.

> [!important] The rule for writing one
> **Describe what changes for the person, not what changed in the code.** They
> have never read your code and never will. "Screenshots get saved somewhere
> better now" is right. "Refactors `shot.py` to use `pathlib`" is wrong — it's
> true, and it's useless.
>
> Anything with no entry here still gets offered — the updater falls back to a
> generated description and their AI reads the raw diff. Nothing is ever
> invisible. An entry just makes it a decision they can actually make.

## The format

Blocks in any order. Newest at the top is easiest to read.

```
### id: some-stable-id
title: One line, plain English, no jargon
files: AIOS/scripts/thing.py, AIOS/reference/thing.md
needs: nothing            (or: Python 3.9+, or: a GitHub account — optional)

The body. Two or three sentences. What's different for them afterwards, and
why they might want it. Write it like you're telling a friend, because you
are.
```

- **`id:`** never changes once shipped. It's what "they said no to this
  already" is keyed on. Change the id and everyone who declined gets asked
  again.
- **`files:`** every file the change touches. Those files then get grouped
  under this one question instead of appearing as six separate ones.
- **`needs:`** anything extra required. Leave it as `nothing` most of the time.
- Editing the body of a shipped entry is fine and re-asks nobody. Editing the
  **files** re-asks the people who declined it, once, marked as *"you said no
  to this before, it has changed since"*. That's deliberate.

---

## Changes

### id: setup-checks-catch-up
title: The self-check now actually checks for all seven skills, and the setup interview reminds itself to index new notes
files: AIOS/scripts/setup-check.py, AIOS/skills/setup-vault/SKILL.md
needs: nothing

Two small honesty fixes found by actually running a fresh setup end to end.
The self-check script was still only looking for six of the seven shipped
skills, so it could never have told you the seventh (`update-vault`) failed
to copy. And the setup interview could leave a new `Atlas/About Me/` note
created but not linked from that folder's index — findable by luck, not by
looking. Both now do what they were already supposed to.

### id: character-voice-file
title: A file for teaching your AI how you talk, not just what you want
files: AIOS/character.md, AIOS/vault-map.md
needs: nothing

A new optional file, `AIOS/character.md`, read right after `me.md`. `me.md`
covers *what* the AI should do; this one covers *how it sounds* while doing
it — the difference between an answer that's technically right and one that
reads like a person instead of a corporate report. It ships as a template
with a few blanks: what your style actually is, what tics annoy you, and
space for one real "before/after" example from your own conversations,
which turns out to matter more than any abstract rule. Delete it if you
don't want a separate voice file — nothing else depends on it.

### id: vault-conventions-split
title: Naming and formatting rules moved to their own file
files: AIOS/reference/vault-conventions.md, AIOS/vault-map.md
needs: nothing

The naming scheme, tag list, status values, and the anatomy of a daily note
used to live inside `vault-map.md`, which loads every single session. They
now live in `AIOS/reference/vault-conventions.md`, opened only when you're
actually writing or naming a note. Nothing about the rules changed — just
where they live, so the file that loads every time you type something stays
lighter.

### id: routines-reference-split
title: Routine instructions moved out of the main tooling file
files: AIOS/reference/routines.md, AIOS/skill-map.md
needs: nothing

The full step-by-step for every routine (`daily-brief`, `changelog`, `tidy`,
and the rest) used to live directly in `skill-map.md`. That file now keeps a
short one-line lookup table — trigger phrase, what it does — and the actual
steps moved to `AIOS/reference/routines.md`, opened only when a routine is
running. Same effect as the conventions split: less always-loaded text, same
capability.

### id: naming-duplicate-check
title: A check before creating a note, so you don't end up with two notes about the same thing
files: AIOS/reference/naming.md, AIOS/scripts/route-check.py
needs: nothing

Before creating a new note, your AI can now check whether one already
covers the subject — "Bike Purchase" and "Buying a bike" would otherwise
both get created, and then only one of them ever gets found again. The
check also finds collisions that already happened, and flags filenames that
break the vault's naming scheme. A small table in `naming.md` lets you mark
two similarly-named notes as genuinely different things, so the check
doesn't keep asking about ones you've already confirmed.

### id: diary-and-when
title: A real diary section, and a way to ask "when did I do X"
files: AIOS/scripts/diary.py, AIOS/scripts/notelock.py, AIOS/scripts/logchange.py, AIOS/scripts/capture.py, AIOS/templates/daily-note.md, AIOS/reference/vault-conventions.md
needs: nothing

The daily note's `## Log` section is now `## Diary` — a plain space for
what actually happened that day, written by you or by the AI the moment
you mention something, no timestamps or markers required. The real change
is underneath: every diary line ever written gets indexed, so asking "when
did I go to the lake?" is an instant, honest lookup instead of an AI
guessing its way through old notes. It will say plainly when there's no
record, rather than making one up. Also fixes a real bug: two scripts
writing the same daily note at once could previously corrupt it; they now
share a lock.

### id: dated-events
title: Trips, appointments and exam weeks get their own kind of note that links itself into your calendar
files: AIOS/scripts/event.py, AIOS/templates/event-note.md, AIOS/scripts/logchange.py
needs: nothing

A new note type for anything with a start and end date that isn't a project
— a trip, a hospital appointment, an exam week. Create one and it
automatically shows up on every day it covers, in that day's note, with its
status ("upcoming" / "happening" / "done") kept current on its own. Before
this, a note like that could sit in a folder for its entire duration without
anything on the actual days pointing at it.

### id: move-and-verify
title: Renaming or moving a file, and checking nothing broke, are both one command now
files: AIOS/scripts/move.py, AIOS/scripts/verify.py, AIOS/reference/moves.md, AIOS/scripts/paths.py
needs: nothing

Renaming or relocating a note used to mean manually finding and fixing
every place that mentioned its old path — easy to miss one. One command now
does the move and rewrites every mention across the whole vault, and keeps
a running history of what moved where. A second new command lets your AI
snapshot the vault before a big change and diff it after, so "did anything
break" gets a real answer — files added, removed, or suspiciously
shortened — instead of a reassurance.

### id: where-and-scale-generators
title: Two self-updating index files — what every note is about, and how big each folder is
files: AIOS/scripts/route-check.py, AIOS/scripts/vault-map.py
needs: nothing

Two files now keep themselves current automatically: one indexes every note
by the words that actually distinguish it, so finding something is one grep
instead of an AI opening files at random; the other keeps an honest,
per-folder note count instead of a hand-typed number that goes stale within
days.

### id: taste-commands-migration-generators
title: Three more files that keep themselves current
files: AIOS/scripts/taste.py, AIOS/scripts/commands.py, AIOS/scripts/migration-scan.py, AIOS/reference/migration.md, AIOS/reference/setup.md
needs: nothing

A taste profile that compiles everything you like/dislike into one place
instead of scattered across notes; a flat list of every command and trigger
phrase in the vault, for when you've forgotten the exact wording; and an
inventory step for the file you'd hand to a different AI if you ever
switch, so it can't quietly go out of date.

### id: stale-and-orphan-check
title: A check for facts that have probably gone stale, and notes nothing links to
files: AIOS/scripts/stale-check.py
needs: nothing

A report-only check that flags two things a broken-link checker can't see:
a note whose content has a shelf life and is past it (a "currently watching"
note nobody's touched in a month), and a note that exists and is correct but
that nothing else links to, so it's only findable by luck.

### id: project-status-and-chronicle-scripts
title: A few routines that used to be manual are now one command
files: AIOS/scripts/project-status.py, AIOS/scripts/chronicle.py, AIOS/scripts/capture.py
needs: nothing

"Where does this project actually stand" and "write up this old
conversation with decisions pulled to the top" both used to mean an AI
reading a full note or retyping a transcript by hand. Both are now a single
script call — faster, and the same every time.

### id: canon-correction-in-auto-capture
title: Corrections to a fact now get tracked so they reach every note that repeats it
files: AIOS/skills/auto-capture/SKILL.md
needs: nothing

If a fact gets corrected in one note but the vault has it written in three
others, the old fix left the other three wrong — no error, no broken link,
just quietly out of date. The capture skill now registers a corrected fact
in one place and checks the whole vault for the old wording, in the same
turn as the correction.

### id: daily-brief-events-and-receipt
title: Daily brief now shows today's events and logs its own receipt
files: AIOS/skills/daily-brief/SKILL.md
needs: nothing

The daily brief now pulls in anything from the new dated-events feature
that's happening today, and logs a one-line receipt of its own run — small,
but it closes the last gap where a vault write could happen with no record
of it.

### id: me-md-new-defaults
title: A few new default working habits
files: AIOS/me.md
needs: nothing

Three small defaults added to the "how to work with me" template: check
whether a repeated manual step should just be a script before doing it by
hand again; don't open a file just to append to it when a blind-write
command already exists; and after any change touching several files, show
what was actually touched instead of just saying it's fine.

### id: vault-updates-from-blueprint
title: Your vault can now pull in blueprint improvements by itself
files: AIOS/scripts/blueprint-update.py, AIOS/scripts/blueprint-manifest.py, AIOS/scripts/blueprint-release.py, AIOS/reference/blueprint-changes.md, AIOS/skills/update-vault/SKILL.md, UPDATE-MY-VAULT.md
needs: nothing

Until now, if the blueprint got better after you downloaded it, you'd never
find out. This adds a way to check.

Say **"update my vault from the blueprint"** and your AI fetches the latest
version, works out what's actually different from your copy, and reads the
changes out to you one at a time in plain English. You pick what you want.
Anything you say no to is remembered and never brought up again.

It cannot touch your writing. Your notes, your `Privat/` folder, and your own
answers in `AIOS/me.md` are off limits to it by design, not by good intentions
— the four files that are half yours (`CLAUDE.md`, `me.md`, `vault-map.md`,
`skill-map.md`) can only ever be merged by your AI, sentence by sentence, never
overwritten by a script. Everything it does change is backed up first, so
"undo the last blueprint update" is a real thing you can say.

Also works from the terminal on its own, if you'd rather:
`python3 AIOS/scripts/blueprint-update.py --interactive`
