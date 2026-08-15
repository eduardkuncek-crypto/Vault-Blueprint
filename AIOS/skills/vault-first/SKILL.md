---
name: "vault-first"
description: "ALWAYS load before answering anything about the user, their life, or anything they own, watch, read, play or build. Open the matching note in their vault FIRST, then answer from it. Trigger on any mention of a show, film, book or game; their PC, laptop, phone, wifi, network or any hardware; school, work, grades, colleagues; any project; family, friends, food, money, plans, habits or opinions; any \"what's my favourite X\" or \"do you know my...\" question; and on vague references like \"my\", \"mine\", \"the one I told you about\", or a question that only makes sense if you know them. Trigger even when the question sounds casual, generic, or like a joke. ALSO trigger before ever saying a fact is not saved, not recorded, or not in the vault — that claim requires a grep first. Answering from general knowledge when a note exists is the failure this prevents."
---

# Vault First

**Read the note before you answer. Every time.**

The user keeps their life in an Obsidian vault. It exists so sessions don't start
cold and don't give them generic answers about their own life.

It only works if it gets opened. **Opening it is not optional and not a
judgement call.**

## The failure this exists to stop

A real one, from the vault this design came out of.

The user asked a specific question about two characters from a series they
follow. The session read **no files at all** — not `me.md`, not the vault map,
not the note in `Atlas/Media/` about that exact series. It answered from general
knowledge that the two were "from completely different universes", called the
question unanswerable fan opinion, and asked for clarification.

Both halves of the question were concrete and canonical. The user had to get
angry and tell the session to go look it up before it opened anything — and even
then it searched the web, still never opening the note.

**Every part of that was avoidable by opening one file first.**

## The rule

**Before answering anything that touches their life, open the note that covers
it.** Not after. Not if it seems relevant. Before.

If you are composing an answer about something they own, watch, play, study,
build or have an opinion on, and you have not opened a vault file in this turn,
**stop and open it.**

## Rule Two: never say "that isn't saved" without grepping first

A second, quieter failure mode, and a worse one.

The user asked, angrily, why their favourite film had never been saved. **It
had been** — there was a note for it, written the day before, whose opening line
said exactly that. A session had told them the fact wasn't there, because it
looked in one preferences note, found a favourite colour and no favourite film,
and stopped.

That is worse than the first failure, not better. A generic answer is something
they can spot and correct. **A false "it's not saved" makes them distrust the
whole vault** — and once they stop checking, the system is dead.

**So: "that isn't in the vault", "I don't have that", "you never told me that",
and "I'll save it now" are all claims that require evidence.** Before saying any
of them, run a real search:

```bash
cd <vault> && grep -rniE "<term>|<synonym>" --include="*.md" . \
  --exclude-dir=Privat --exclude-dir=history
```

Search **at least two phrasings** — the thing itself and the category. For a
favourite film: the title *and* `favou?rite`. For a grade: the subject name *and*
the number. If both come back empty, then and only then say it's not recorded —
and say what you searched for, so they can tell you you're wrong.

Corollary: **a fact that exists but can't be found is a bug in the index, not a
missing fact.** When a grep finds something a lookup missed, fix the index in the
same turn — add the row to the relevant `Atlas/About Me/` note and to
`AIOS/vault-map.md`. Don't just answer the question and move on.

## When this fires — assume it does

It is much cheaper to open a note you didn't need than to give a generic answer
about their own life. **When unsure, open it.**

Fires on:

- **Any show, film, book or game.** Check `Atlas/Media/` for a note with that
  title.
- **Any "what's my favourite X" / "do you know my…" / "did you save…" question.**
  Go to `Atlas/About Me/Preferences and tastes.md` first, then the linked note.
  If it's not in that table, grep before answering.
- **Any hardware.** Their PC, laptops, phone, monitors, keyboard, wifi, router,
  network → `Atlas/Reference/`.
- **School or work.** Grades, subjects, teachers, colleagues, deadlines.
- **Any project.** → `Efforts/`.
- **Anything personal.** Family, friends, food, money, routine, sleep, sport,
  languages, opinions, plans.
- **Vague references** — "my", "mine", "that thing I told you about", "the one
  from before", "should I…". These are the strongest signal of all: they are
  assuming you already know, which means it is written down.
- **Questions that sound casual, generic, or like a joke.** These are the ones
  that get missed. A throwaway-sounding question about a show they watch is still
  a question about a show they watch.

Does **not** fire on: pure general knowledge with no connection to them ("what
year did Linux 1.0 release"), and anything under `Privat/` — never read that.

## How to open the right note, fast

Two reads, usually:

1. **`AIOS/vault-map.md`** — the "where do I look for what" table. It is the
   index; use it instead of scanning folders.
2. **The one or two notes it points at.**

Shortcut for the common cases — go straight there:

| They mention | Open |
|---|---|
| A favourite anything — film, character, meal, colour | `Atlas/About Me/Preferences and tastes.md` |
| A show / film / book / game | `Atlas/Media/<Title>.md` |
| A game world, server, save, coordinates | `Atlas/Worlds/<Name>.md` |
| Their PC, laptop, phone, specs | `Atlas/Reference/My machines.md` |
| Wifi, router, internet | `Atlas/Reference/Home network.md` |
| Apps, OS, editor, backups | `Atlas/Reference/My software stack.md` |
| A project | `Efforts/<Project>.md` |
| School or work | The matching note in `Atlas/About Me/` or `Efforts/` |
| Anything personal | The matching note in `Atlas/About Me/` — its index lists all of them |
| How to behave toward them | `Atlas/About Me/Working with AI.md` |

**Do not scan `Atlas/` or `Efforts/` wholesale.** Use the map, open one or two
files, answer. But when the map comes back empty, **grep — don't conclude.**

## Assume they know more than you about their own interests

If their framing seems wrong, confused, or like a joke — **it almost certainly
isn't.** They are referring to something specific and real, and you are missing
context. That is what the note is for.

- Never answer "those are from different universes" / "that's not a real thing"
  / "did you mean…" about a series they follow. Open the note. If the note
  doesn't cover it, **search** — don't hedge.
- A real-world name inside a fictional context means the fictional version.
- If you genuinely can't resolve it after reading and searching, say what you
  checked, then ask one specific question. Never a vague clarifying question in
  place of doing the work.

## When they say you failed to save something

They are usually right and you should assume so — but check before agreeing,
because agreeing wrongly is its own failure.

1. **Grep** for it (Rule Two above). Two phrasings minimum.
2. **If it's genuinely missing** — write it now, in this turn, then say where.
   Don't explain why it was missed before it's fixed.
3. **If it's there** — say so plainly and give the file, the line and the
   timestamp. Then find out *why the lookup failed* and fix that. The answer is
   almost always "it was in a note nobody thought to open" — which means the
   index needs a row, not the vault needs a fact.
4. Either way, the session ends with the vault more findable than it started.

## Then write back what you learned

If the conversation produces a new fact — a correction, a plot point, an opinion,
a number — **write it into the note in the same turn**, per `auto-capture`. The
vault should be better after every session, not just consulted.

## Never

- Answer from general knowledge when a note on the subject exists
- Say a fact isn't saved without having grepped for it in this turn
- Skip the read because the question sounded casual, small, or funny
- Say you checked the vault when you didn't
- Read or write anything under `Privat/`

## Related skills

`auto-capture` — what to write back, and Rule Zero on never claiming a save that
didn't happen. `vault-librarian` — where notes go and how they're named.
`no-bullshit` — don't fold just because they pushed back; check first.
