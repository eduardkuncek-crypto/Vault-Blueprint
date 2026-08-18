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
