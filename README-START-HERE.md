---
title: README-START-HERE
tags:
  - index
---

# Read this first

This is a **blueprint for an AI-run Obsidian vault**. It is empty on purpose —
folders, conventions, templates, scripts and skills, with none of anyone's
personal notes in it.

The idea: you keep your life in plain markdown files, and an AI reads and writes
them for you. It remembers what you told it last week. It writes things down
without being asked. Every session starts knowing who you are instead of starting
from zero.

It takes about 10 minutes of your time (plus however long you want to spend on
the questions in step 3). Works the same on Linux, macOS and Windows — every
script in here checks which OS it's on and does the right thing for it. Do the
three steps in order.

---

## Step 0 — What you need

- **[Obsidian](https://obsidian.md)** — free, and available for Linux, macOS
  and Windows. It's just a markdown editor; the files are plain text folders
  on your disk, readable by anything.
- **Claude Cowork** (the desktop app's folder mode) or **Claude Code** — anything
  that can read and write files in a folder. Chat alone will not work, because
  chat cannot touch your files. (If you're only using a plain chat window
  right now, stop and switch to one of these first — nothing below will work
  otherwise, and that's the single most common reason someone thinks this
  blueprint is broken when it's actually just not connected to your files.)
- **Python 3.8+** — for the automation (chat backup, health checks). Most
  Linux and macOS machines already have it. On Windows, get it from
  [python.org](https://www.python.org/downloads/windows/) and tick **"Add
  python.exe to PATH"** during install — that's the step almost everyone
  misses, and without it nothing below can find `python3`.
- **A sync folder** — Dropbox, Syncthing, iCloud, whatever you already use. Put
  the vault inside it so it reaches your other machines. Optional but you'll
  regret skipping it.

---

## Step 1 — Put the folder somewhere real

Copy this whole folder to where you want it to live, and rename it to whatever
you want your vault called. For example:

```
~/Dropbox/My Vault
```

Then in Obsidian: **Open folder as vault** → pick that folder.

You'll land on `Home.md`. That's your dashboard from now on.

---

## Step 2 — Point your AI at the folder

In Cowork, connect the folder (the app asks which folder it may use). In Claude
Code, just `cd` into it.

`CLAUDE.md` at the root tells the AI what to read at the start of every session.
It's one paragraph long, and that's deliberate — everything real lives in `AIOS/`,
so switching to a different AI later means writing one new pointer file and
changing nothing else.

---

## Step 3 — Say "set yourself up"

That's it. That's the whole step. Type exactly that, or anything close to it
("set up this vault", "get started", "install this"), and the AI does the
rest of the list below **in this one conversation**, without you needing to
ask again for each part:

1. Runs the setup scripts — creates the folders the automation needs, and
   tries to turn on automatic chat backup using whatever your OS actually has
   (cron on Linux/macOS, Task Scheduler on Windows).
2. Gets the vault's skills active — copied straight into `.claude/skills/` if
   you're on Claude Code (instant, nothing to click), or explained honestly if
   you're on Cowork, where saving a skill needs your one-click confirmation
   and can't happen silently. Either way, the vault behaves correctly from
   this conversation onward regardless of whether you click save on anything
   — see `AIOS/skills/README.md` if you want the detail.
3. Interviews you — starts on Section 1 of `AIOS/setup-questions.md` right
   away, a few questions at a time, saving your answers as it goes. **Section
   1 (10 questions) is all it takes to make the vault usable**; the other 7
   sections make it good, and you can stop after any of them — it'll offer
   the rest later. Prefer typing over talking? Open `AIOS/setup-questions.md`,
   fill in the `→` lines yourself, and say *"process my setup answers"*
   instead — same result, no conversation.
4. **Runs a real self-check and shows you the result** — `AIOS/me.md` filled
   in or not, which skills are actually active, whether the chat backup found
   your machine's Claude folder, whether the scheduled jobs are really there.
   Not "trust me" — an actual pass/fail table. You can re-run this yourself
   any time:

   ```
   python3 AIOS/scripts/setup-check.py
   ```

   Worth doing a day or two after setup, too — to confirm a scheduled job
   really survived and wasn't just installed inside a disposable session that
   got thrown away (see the note in `AIOS/scripts/setup.py` if that phrase
   means nothing to you yet — the short version: this needs to run on your
   own computer, in Claude Code or Cowork's on-device mode, for the
   automation to actually stick).

`AIOS/me.md` is the single most important file that comes out of this. It's
what makes the AI treat you like you and not like a generic user.

---

## Then what

Just talk to it normally. It writes things down as you go.

Things worth typing, once you're running:

| Type this | What happens |
|---|---|
| `log <thought>` | Timestamped into today's daily note, in your words |
| `next` | Rebuilds one page listing every project's next action |
| `daily-brief` | Today's brief into today's daily note |
| `project-status <name>` | Under 200 words: where it stands, what's next |
| `decide <question>` | Real trade-offs, a recommendation, and what would change its mind |
| `weekly-review` | Reads the week, tells you bluntly what slipped |
| `vault-check` | Checks for broken links, dead indexes, stale tables. Reports only |
| `tidy` | Finds orphan notes and messy tags. Proposes before changing |

All of those are defined in plain English in `AIOS/skill-map.md`. Edit that file
to change them — no code involved.

The full guide, including why it's shaped this way: `AIOS/how-to-use-this.md`.

---

## Keeping up with the blueprint

This blueprint keeps getting better after you download it. Rather than making
you re-download and lose your notes, your vault can pull the improvements in
itself. Say:

> **update my vault from the blueprint**

It fetches the latest version, works out what's actually different from your
copy, and reads the changes out to you one at a time in plain English —
*"screenshots get their own folder now, want it?"* — and applies only what you
pick. Anything you turn down is remembered and never asked about again.

It cannot touch anything you wrote. Your notes, your `Privat/` folder and your
answers in `AIOS/me.md` are off limits to it, and everything it does change is
backed up first, so *"undo the last blueprint update"* is a real thing you can
say. Details: `AIOS/skill-map.md` §`update-vault`.

Prefer the terminal?

```
python3 AIOS/scripts/blueprint-update.py --interactive
```

---

## If something doesn't work

Run this — it's the one command that tells you what's actually true, instead
of guessing:

```
python3 AIOS/scripts/setup-check.py
```

It checks Python, the vault's shape, whether `me.md` is filled in, whether the
skills are active, whether a scheduler was found and the backup/snapshot jobs
are really installed in it, whether your chat folder was found, and whether
git is set up (if you're using it). Each line is marked `[ OK ]`, `[WARN]` (often
normal — read the detail) or `[FAIL]` (something's actually broken). More
detail, including the most common failure modes, is in
`AIOS/how-to-use-this.md` §7.

## Housekeeping

**Delete the example notes** once you've looked at them. They're about a made-up
person and exist only to show what a filled-in note looks like:

- `Efforts/EXAMPLE Bike Restoration.md`
- `Atlas/Media/EXAMPLE Dune.md`
- `Atlas/About Me/EXAMPLE How I learn.md`
- `Calendar/Daily/EXAMPLE daily note.md`

**`Privat/` is off limits to the AI.** Every skill in here refuses to read or
write inside it. Put anything you don't want an AI seeing in there. If you don't
want a private folder at all, delete it — but then also delete the `Privat/`
lines from `CLAUDE.md`, `AIOS/me.md` and `AIOS/vault-map.md`, or the AI will keep
protecting a folder that isn't there.

**Delete this file** when you're done with it, and delete `AIOS/setup-questions.md`
and the `setup-vault` skill once the interview is finished.

---

## The one habit that matters

When you decide something in a chat, make sure it lands in the project note.
`auto-capture` does this on its own most of the time — but when you notice it
didn't, say so.

That's the whole difference between a vault that compounds and one that rots.
