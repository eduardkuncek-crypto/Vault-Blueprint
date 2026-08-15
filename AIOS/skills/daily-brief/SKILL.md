---
name: "daily-brief"
description: "Compile the user's daily brief and write it into today's Obsidian daily note, or append a timestamped thought via the `log` routine. Use when they say \"daily brief\", \"brief me\", \"what's on today\", \"morning brief\", \"log ...\", or when the scheduled morning task runs."
---

# Daily Brief

Write today's brief into `Calendar/Daily/YYYY-MM-DD.md` in the user's vault.

## Before writing

Get today's real date — check it, don't assume.

If the file doesn't exist, create it from `AIOS/templates/daily-note.md`.
If it exists, **fill in the Brief section only. Never touch anything below
`## Log`.**

## What goes in the brief

Gather what's actually available. Skip sections you have no data for rather than
writing filler.

1. **Weather** — for wherever they live, per `AIOS/me.md`. Search for it; don't
   guess.
2. **Today's events** — from a calendar connector if one is available. If not,
   skip the section silently.
3. **Unread and important email** — from a mail connector if one is available.
   Important means: money, school or work, something expecting a reply. Not
   newsletters.
4. **Deadlines** — check dated items in `Efforts/`.
5. **Project momentum** — which notes in `Efforts/` changed in the last 3 days,
   and which haven't been touched in over a week. Name the stale ones; that's the
   useful half.
6. **Cooldowns** — check `Calendar/Cooldowns.md` if it exists. Anything unlocking
   **today** goes near the top with the action it enables. Anything unlocking
   within 7 days gets one heads-up line. Neither? Write nothing — no "no
   cooldowns" filler. Compare against the real date, don't eyeball it.
7. **Suggested focus** — exactly one thing. Pick what unblocks the most other
   work, and say in one line why.

## Tone

Short. This gets read in under a minute. No preamble, no encouragement, no
"Good morning!". Bullets, not paragraphs.

If nothing is happening today, say so in one line. A brief that pads itself out
teaches them to stop reading it.

## The `log` routine

When they say `log` followed by a thought:

1. Get the current time (`HH:MM`).
2. Clean up **only** obvious typos. Keep their wording, their phrasing, their
   voice. Do not make it more articulate. Do not expand it.
3. Append under `## Log` in today's daily note:

   `**14:32** — the thought, in their words`

4. Confirm in one short line. Don't repeat the entry back at them.

## Never

- Overwrite anything they typed themselves
- Read or write anything under `Privat/`
- Invent calendar events, email, or weather when the source isn't connected

## Related

Conventions: the `vault-librarian` skill and `AIOS/vault-map.md`.
