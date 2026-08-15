---
title: Home
tags:
  - index
---

# Home

> [!tip] If you're confused, read this box and nothing else
> `Atlas`, `Calendar`, `Efforts` are **your** notes. `AIOS/` is **instructions
> for the AI** — you never need to open it. That's the whole layout.

> [!warning] Not set up yet?
> If `AIOS/me.md` still has `<< >>` placeholders in it, start at
> [[README-START-HERE]]. Takes about 30 minutes.

## What I'm working on

The live table with status and next actions is in [[Efforts]].

| | |
|---|---|
| [[Next Actions]] | **What to actually do now.** Every project's next action + every open checkbox, one page |
| [[Efforts]] | Projects. Status, blockers, the reasoning. |
| [[Radar]] | Books, shows, games, tools I want to check out |
| [[Atlas]] | Knowledge, reference, clippings — things that stay true |
| [[Calendar]] | Daily notes and weekly reviews |
| [[Inbox]] | Stuff I dumped for the AI to deal with |

`Privat/` — the private half. **The AI never touches it.**

## Things to type at the AI

Just talk normally. These specific words trigger a routine:

| Type this | What happens |
|---|---|
| `log <thought>` | Timestamped into today's daily note, in your words |
| `next` | Rebuilds [[Next Actions]] from every project note |
| `daily-brief` | Today's brief into today's daily note |
| `project-status <project>` | Under 200 words: where it stands, what's next |
| `decide <question>` | Real trade-offs with numbers, plus a recommendation |
| `learn <topic>` | Creates a structured note in `Atlas/Knowledge/` |
| `weekly-review` | Reads the week, tells you bluntly what slipped |
| `save-chat` | Dumps the conversation into `AIOS/history/` |
| `tidy` | Finds orphan notes and messy tags. Proposes before changing |
| `vault-check` | Checks for broken links, dead indexes, stale tables. Reports only |

Full definitions: [[skill-map]]. Edit that file in plain English to change them.

## What saves itself

You don't have to ask. The `auto-capture` skill writes these on its own:

- Decisions you make out loud → the project's decisions log
- Things you want to check out → [[Radar]]
- Commitments ("I'll do X") → a `- [ ]` task in the project note
- Something you watch, read or play → its own note in [[Media]]
- Game world state, including from screenshots → [[Worlds]]
- Durable facts about you → its own note in [[About Me]]

**Not** saved automatically: full chat transcripts. Say `save-chat` when you want
one. (*"Save facts, not chat logs."*)

If it captures too much noise, say *"auto-capture is over-capturing."* If it
misses something, say *"auto-capture should also save X."* Don't switch it off.

## The one habit that matters

**When you decide something in a chat, make sure it lands in the project note.**
It usually happens automatically — but if you notice it didn't, say so. This is
the difference between a vault that compounds and one that rots.

## Under the hood

You don't need this to use the vault. It's here when you want it.

| File | What it is |
|---|---|
| [[how-to-use-this]] | The full guide — setup, vocabulary, troubleshooting |
| [[me]] | Who you are and how the AI should work with you |
| [[vault-map]] | Where everything lives (the AI reads this) |
| [[skill-map]] | Every skill and routine, editable in plain English |

`CLAUDE.md` at the vault root is a one-line pointer at `AIOS/me.md`. Switching AI
providers means writing one new pointer file — nothing else changes.
