---
title: how-to-use-this
tags:
  - index
---

# How to use this

The full guide. [[README-START-HERE]] gets you running in 30 minutes; this
explains why it's shaped this way and what to do when it misbehaves.

---

## 0. The one idea you have to get

**The vault is the memory. The AI is just the thing that reads and writes it.**

A chat window forgets everything when you close it. A folder of markdown files
doesn't. So instead of explaining yourself to an AI every session, you explain
yourself **once**, into files — and every session starts by reading them.

That's it. Everything else here is plumbing for that one idea.

Two consequences worth sitting with:

- **You own it.** It's plain text on your disk. No export, no lock-in, no
  subscription holding it hostage. Switch AI providers and the vault doesn't
  care.
- **It compounds.** Session 1 knows nothing. Session 50 knows what you decided in
  session 12 and why you abandoned the thing from session 30. That only works if
  decisions actually get written down — which is what `auto-capture` is for.

---

## 1. Folder mode or chat?

**Folder mode.** Chat cannot read or write files, which means it cannot use any
of this. In Claude that means Cowork (desktop app, connect a folder) or Claude
Code (terminal, `cd` into the vault).

If you find yourself pasting note contents into a chat window, you're in the
wrong mode.

---

## 2. The three layers

The vault has three layers and they don't mix:

**1. Your notes** — `Atlas/`, `Calendar/`, `Efforts/`. This is the actual
content. Structure is **ACE**:

- **Atlas** — things that stay true. Reference, knowledge, media, tastes.
- **Calendar** — things tied to a date. Daily notes, weekly reviews.
- **Efforts** — things you're actively pushing. One note per project.

If you can't decide where something goes, ask: *is this timeless, dated, or
being worked on?*

**2. The AI layer** — `AIOS/`. Identity, maps, templates, scripts, skill copies.
You rarely open this. The AI opens it constantly.

**3. The private half** — `Privat/`. Nothing reads it. Not the AI, not the
scripts, not the checks. It exists so the other two layers can be fully open.

The reason for the split: an AI that can read everything is useful but
uncomfortable, and an AI that can read nothing is useless. Drawing one hard line
lets you stop thinking about it.

---

## 3. What a skill actually is

A skill is a markdown file with a name, a description, and instructions. That's
the whole format:

```markdown
---
name: "vault-librarian"
description: "Conventions for writing notes into the vault. Use whenever
creating, editing, moving or naming any note."
---

# Vault Librarian

## Where a note goes
...
```

The **description** is the important part — it's what the AI reads to decide
whether to load the skill at all. A vague description means the skill never
fires. Write it as *"use when the user does X, Y or Z"*, with the actual words
someone would say.

Skills live in your AI's storage. `AIOS/skills/` holds plain-markdown copies so
they survive, sync, and stay readable by other tools.

---

## 4. Skills vs routines — and when to promote one

**Routines** live in `AIOS/skill-map.md` as plain English. You say the name, the
AI follows the steps. Zero setup, easy to edit, but they only fire when you name
them.

**Skills** fire on their own, based on what you're talking about.

Start everything as a routine. Promote it to a skill when:

- you run it more than about once a week, **and**
- it needs to trigger without you naming it, **or**
- it needs reference files or scripts

Keep the routine in `skill-map.md` afterwards as the plain-markdown fallback.

---

## 5. What gets saved, and what doesn't

**Automatic** — `auto-capture` writes these without being asked:

- Any durable fact about you → its own note in `Atlas/About Me/`
- Decisions → the project's decisions log in `Efforts/`
- Something you watch, read or play → its own note in `Atlas/Media/`
- Things you're curious about → a row in `Atlas/Radar.md`
- Game world state, including read off screenshots → `Atlas/Worlds/`
- Commitments → a `- [ ]` checkbox in the relevant note
- **And a receipt line in today's `## Changes`** for every one of the above

**Only on request:** full chat transcripts (`save-chat`).

**Never:** anything under `Privat/`.

### Why `## Changes` exists

`me.md` says *never tell me something was saved before it was*. Without a
receipt, that rule is unenforceable — you'd have to take the AI's word for it.

So every vault write also appends one line to today's daily note under
`## Changes`, via `AIOS/scripts/logchange.py`. Open today's note and you can see
exactly what was written and where.

**The daily note is the receipt. The subject note is the content.** If facts
start landing *in* `## Changes` instead of in real notes, something has gone
wrong — that rebuilds the catch-all file the whole design bans, just spread
across ninety dated files.

---

## 6. Keeping it from getting dumber

This is the failure mode nobody warns you about.

**Notes are free.** They're loaded on demand, only when relevant, via
`vault-map.md`. You can have a thousand.

**The always-on instruction layer is not free.** Skill descriptions, `me.md`,
`vault-map.md`, `skill-map.md`, and the body of every always-on skill get loaded
*in full, on every single session*, before you type a word. Every line you add
there is paid forever.

So when a rule isn't being followed, the instinct is to add more text explaining
it. That's almost always wrong. **A failing rule needs a mechanism, not more
words.**

Worked example: "never say something was saved when it wasn't" was in `me.md`
and kept failing. Adding emphasis didn't work. What worked was a *script* that
writes a receipt — now the claim is checkable, and the rule enforces itself.

Run `python3 AIOS/scripts/context-budget.py` before adding text to any always-on
file. It tells you the floor and shouts if it's grown more than 10%.

---

## 7. When something doesn't work

**Start with `python3 AIOS/scripts/setup-check.py`.** It tests most of this
directly instead of you guessing from symptoms — read that output first.

| Symptom | Cause, usually |
|---|---|
| AI gives generic answers about your own life | `vault-first` isn't active, or `me.md` is still placeholders |
| AI never writes anything down | `auto-capture` isn't active. Check `AIOS/skills/README.md` for how "active" works on your platform |
| AI says "that isn't saved" and it is | Index bug. The fact exists but nothing points at it — add a row to `vault-map.md` |
| An index note lists nothing | A ```dataview block in a vault without the Dataview plugin. Use a `.base` instead |
| AI can't see the vault at all | Folder isn't connected, or it's on a network/FUSE mount some tools can't read |
| Answers got vaguer as skills grew | Context floor. Run `context-budget.py` |
| Two versions of a note | Sync conflict. `vault-check.py` finds them. Diff before deleting |
| A skill's description is showing up as text | Duplicated YAML frontmatter block. There must be exactly one |
| Chats aren't backing up | Run `python3 AIOS/scripts/backup-cowork.py` directly and read what it prints — it lists every path it checked for your Claude app's data. Usually either the AI session doing the setup was a cloud sandbox (can't see your local files at all — this has to run on your own machine) or Claude's storage moved to a new path this script doesn't know about yet |
| A scheduled job (backup, snapshot, changelog-check) isn't firing | Run `python3 AIOS/scripts/setup-check.py` — if it says "installed" but nothing's actually happening, the job was very likely installed inside a disposable cloud session and thrown away with it. Re-run `AIOS/scripts/setup.py` from a real terminal on your own computer |
| Setup ran on Windows and nothing scheduled | Task Scheduler needs `schtasks.exe` on PATH, which is standard on every Windows install — if `AIOS/scripts/scheduler.py --status` reports no scheduler, something unusual is blocking it (locked-down work laptop, etc.); the scripts still work fine run by hand |
| A note count or scheduled-job claim doesn't match reality | Nothing in this vault should ever claim success without having just checked — if it did, that's a bug in whatever said it, not a fact about the vault. Re-run the relevant script and trust its output over any earlier claim |

When a rule fails twice, don't restate it louder. Ask what mechanism would make
the failure impossible or visible.

---

## 8. The trap

**Do not spend your time polishing this system instead of using it.**

Building a beautiful vault is more fun than doing the work the vault is for. You
will feel productive. You will have accomplished nothing.

Signs you're in it: reorganising folders for the third time, writing skills you
never invoke, tuning tag schemes, reading about note-taking methods.

The vault is worth exactly what you put through it. A messy vault with your real
decisions in it beats a perfect empty one, every time.

---

## 9. If you only remember three things

1. **Fill in `me.md`.** Nothing else works without it.
2. **When you decide something, make sure it lands in the project note.** That's
   the whole compounding mechanism.
3. **Don't polish. Use it.**

## Related

- [[Home]]
- [[me]]
- [[vault-map]]
- [[skill-map]]
