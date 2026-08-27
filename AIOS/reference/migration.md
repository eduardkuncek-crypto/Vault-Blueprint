---
title: migration
tags:
  - reference
---

# migration.md — hand this file to a different AI

> [!important] Opened on demand, never boot-loaded
> Refreshed on request — say **"make vault migratable"**. Regenerates the
> factual inventory below (skills, routines, scripts) automatically, then a
> person or AI still has to fill in the judgement half by hand: how to
> rebuild trigger-based behaviour in whatever system you're switching to.

This vault's automation layer is provider-agnostic by design — it's plain
Markdown and stdlib Python, not a Claude-specific format. But *automatic
firing* (a skill triggering on a keyword, a routine running on a schedule)
is a platform feature, not a vault feature, and that's the part that doesn't
travel for free. This file is the map of what needs to be manually rebuilt,
and what doesn't.

## What you don't need to do anything about

- Every note. Plain Markdown, readable by anything.
- Every script in `AIOS/scripts/`. Plain stdlib Python — run with
  `python3 AIOS/scripts/<name>.py` on any system with Python 3.9+.
- The boot files (`CLAUDE.md`, `AIOS/me.md`, `AIOS/character.md`,
  `AIOS/vault-map.md`, `AIOS/skill-map.md`). Point your new AI at them the
  same way — a one-line pointer file plus the actual content in `AIOS/`.

## What actually breaks when the provider changes

- **Automatic skill triggering.** A skill firing on "he mentions a show" or
  "he pushes back on a fact" without being named is a platform feature. On a
  system without native skill triggering, the fallback is the plain-markdown
  copy in `AIOS/skills/<name>/SKILL.md` — read it and follow it by hand, or
  paste its contents into the new system's own instruction layer.
- **Scheduled routines.** Anything that fires on a timer (a daily brief, an
  hourly backup) depends on whatever scheduler the new platform gives you —
  cron, Task Scheduler, or nothing at all. `AIOS/scripts/scheduler.py` (in
  the blueprint tooling, not shipped as vault content) is one example of
  wrapping that per-OS difference; a new AI without local shell access can't
  install a schedule at all and needs a human to do it outside the chat.
- **Connectors** (calendar, mail, anything the `daily-brief` routine reads
  from). Re-authorize them in the new system; nothing here can carry an
  OAuth token across providers.

<!-- BEGIN GENERATED: inventory -->

*(not yet built — run `python3 AIOS/scripts/migration-scan.py --write`)*

<!-- END GENERATED: inventory -->

### How to actually run the scripts

Every script in `AIOS/scripts/` is invoked the same way on any OS with
Python 3.9+ installed:

```bash
python3 AIOS/scripts/<name>.py [args]
```

No virtual environment, no pip install — everything here is deliberately
plain standard-library Python so it never rots waiting on a dependency
update.

### Rebuilding session-start behaviour

Whatever replaces "read these files at the start of every session" on the
new platform, point it at, in order: `AIOS/me.md`, `AIOS/character.md` (if
you've customised it), `AIOS/vault-map.md`, `AIOS/skill-map.md`,
`Atlas/About Me/Working with AI.md`.

### `migration-scan.py` counts non-cron routines as one bucket

The generated block above splits routines into "fires on a schedule" and
"fires on request or a trigger phrase" by pattern-matching the *fires*
column of the Routines table in `skill-map.md`. If a routine's fires
description doesn't obviously say "scheduled" or a time, it's counted as
on-request — check the actual row if something looks miscategorized.

### Rebuilding the scheduled routines

For each routine in the "fires on a schedule" list above: on Linux/macOS,
install a cron entry calling the matching script; on Windows, a Task
Scheduler task. Or just run the script by hand on the cadence you actually
want — nothing in this vault requires the schedule to be automatic, only
that the routine's *output* (a rewritten file) stays current when you do
run it.

### Rebuilding the connectors

Re-connect calendar/mail/whatever the `daily-brief` routine used, in
whatever way the new platform authorizes third-party services. Nothing in
this vault stores a credential — that's platform-side by design.

### What stays behind on purpose

`Privat/` never gets copied anywhere by any script here, including this
migration. If a new AI needs access to it, that's a decision you make by
hand, every time, never delegated to automation.

## The rules that carry over regardless of what you are

Everything in `AIOS/me.md` §How to work with me and §House rules for
touching my vault is written to be provider-agnostic — "be direct", "don't
guess", "capture as it happens" don't depend on which AI is reading them.
Read that file into whatever system replaces this one and the actual
*behavior* travels even when the automatic-firing mechanism doesn't.

## How to check you actually rebuilt this and didn't just say you did

Run `python3 AIOS/scripts/setup-check.py` (if the blueprint tooling is
still around) or manually confirm: does a skill actually fire without being
named? Does a scheduled routine actually run on its own? If either answer is
no, the migration isn't done — it's declared.

## Why this file isn't kept continuously up to date

Migration prep isn't a continuous process — there's no natural moment to
re-run it except when you actually need it. The generated block above is
rebuilt every time the `migrate` routine runs, so it's never stale *when it
matters*, even though it isn't refreshed on every vault write the way
`where.md` or `commands.md` are.

## Related

- [[skill-map]] — the routines table this is generated from
- [[vault-map]]
- [[me]]
