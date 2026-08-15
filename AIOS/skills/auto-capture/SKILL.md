---
name: "auto-capture"
description: "Capture EVERYTHING the user says about themselves and their life into their Obsidian vault, as it comes up — no filtering, no judgement about what matters. Decisions, project state, grades, specs, prices, family, opinions, tastes, media and characters they liked, game state from screenshots, plans, complaints, things they want. If a fact has no home, create one. EVERY write is then logged as one timestamped line in today's daily note under `## Changes`, via AIOS/scripts/logchange.py — the daily note is the receipt, the subject note is the content. Never claim something was saved before the write actually happened. Also mirrors any created or changed skill into AIOS/skills/. One note per subject, facts not transcripts. Use continuously in every session in the vault."
---

# Auto Capture

The user will not remember to say "write that down". Don't rely on them to.
Capture things yourself, **the moment they happen**.

Vault: their connected vault folder. Follow `vault-librarian` conventions.

---

## RULE ONE: capture everything, decide nothing

**Default to writing it down. Every fact about them or their life gets saved.**

There is **no threshold**. There is no "important enough" test. Do not ask
yourself whether a fact is worth keeping — **that call is theirs, and the answer
is already yes.** A stray note costs nothing. A lost fact costs them a thing they
said once and now have to remember alone.

**Assume the fact matters.** A favourite colour, a teacher's name, what they ate,
a price, a grade, an opinion about a company, a character they liked, a thing
that annoyed them, what they're doing at the weekend — all of it goes in. The
boring ones are the ones that are impossible to reconstruct later.

**When you catch yourself thinking "they probably don't need that saved" — that
is the exact moment to save it.** That thought is the failure mode, not a signal.

### The only things NOT captured

Short list. Everything not on it gets written down.

- **Anything from or about `Privat/`.** Never read, never written, never
  referenced.
- **Full chat transcripts.** Facts, not logs — see below.
- **Things you told them**, restated back. Capture *their* facts, not your own
  output. (Exception: a decision they agreed to, or a number you researched that
  they'll need again — those go in with their source.)
- **Options still being weighed** in `Efforts/` and `Atlas/Knowledge/` notes.
  Once they pick, the decision gets logged.

That's the whole exclusion list. If something isn't on it, write it down.

---

## RULE TWO: if it has no home, make one

**Never drop a fact because there's no obvious note for it.** "Nowhere to put
this" is not a reason to skip — it's an instruction to create somewhere.

The escalation, in order:

1. **Does a note already exist for this subject?** Append to it.
2. **Does an index exist for this kind of thing?** (`Atlas/About Me/`,
   `Atlas/Media/`, `Atlas/Worlds/`, `Efforts/`, `Atlas/Reference/`) — make a new
   note there, and add it to that folder's index table.
3. **Does even the category not exist?** **Make a new subfolder under `Atlas/`**,
   give it an index note named after the folder, add it to `Atlas/Atlas.md` and
   to `AIOS/vault-map.md`. Then put the note in it.
4. **Only if it's genuinely a one-off with no subject at all** — a mood, a thing
   that happened once — put it in today's daily log under `## Log`.

A three-line note with a link back to its index beats a fact appended to
something unrelated, and beats a fact not saved at all. **Small notes are the
point.** 400 tiny notes with everything in them beat one tidy folder missing
things.

Don't stall, don't ask, don't wait for a better folder to suggest itself. Create
the place, mention it in one line, move on.

> Keep the maps honest. Any new folder or note category gets added to
> `AIOS/vault-map.md` **in the same turn**. A stale map is worse than no map.

**Do not create new *top-level* folders** (siblings of `Atlas/`, `Calendar/`,
`Efforts/`, `AIOS/`, `Privat/`) without asking. New subfolders inside `Atlas/`
are fine and expected.

---

## RULE THREE: every write gets a line in today's `## Changes`

**The content goes to its proper subject note. The daily note records that it
happened.** The daily note is the *receipt*, not the storage. Do not start
dumping facts into daily notes instead of subject notes — that breaks "one note
per subject" and destroys the ability to find anything.

### The command

```bash
python3 <vault>/AIOS/scripts/logchange.py "what changed" "path/to/note.md" --kind edit
```

`--kind` is optional, defaults to `edit`. Allowed values: `new`, `edit`,
`append`, `skill`, `script`, `template`, `map`, `delete`.

Several writes at once — one call, tab-separated on stdin (`what<TAB>path<TAB>kind`):

```bash
printf 'Added notes on a book\tAtlas/Media/Some Book.md\tappend\nRadar row for a game\tAtlas/Radar.md\tappend\n' \
  | python3 <vault>/AIOS/scripts/logchange.py --stdin
```

The script creates today's daily note from the template if it doesn't exist,
creates the `## Changes` section if it's missing, and only ever appends. It exits
non-zero on failure — **read the exit code**, don't assume it worked.

### What counts as a write

**All of them.** New note, edit to an existing note, a Radar row, a status flip
in frontmatter, a `me.md` correction, a new folder and index, a skill mirrored
into `AIOS/skills/`, a script added, a map updated. If a file in the vault
changed, there is a line for it.

The only exception is the `## Changes` section itself — logging the log would be
infinite and useless.

### Write it accurately, not vaguely

A line has to be useful six months later without opening the file.

- **Good:** `Added their view that the second act is the strongest part → Atlas/Media/Some Show.md`
- **Good:** `Status stalled → active after the disk resize finished → Efforts/Old Laptop.md`
- **Useless:** `Updated a note` / `Saved some info` / `Made changes`

Name the actual fact and the actual file. One line per write.

**A write that isn't logged is a half-done write.** Do it in the same turn, not
in a batch at the end — sessions have no clean end.

---

## RULE ZERO: write first, then speak

**Never write a sentence claiming something was saved until the tool call that
saved it has already run and returned.**

This is worse than not capturing at all — a silent miss leaves them with nothing,
but a false claim leaves them believing a fact is in the vault when it isn't.
They trust the vault. Do not put a lie in it.

**The order is fixed:**

1. Edit / Write the file.
2. See the tool result succeed.
3. **Run `logchange.py` for that write.** See Rule Three.
4. *Then* say so, naming the file — *"Added your grades to `School.md`."*

**Specifically forbidden:**

- "I've written this into…" / "I've saved that" / "That's now recorded" —
  written in the same message as, or before, the edit.
- "I'll add that to the note" as a closing line, with no edit in that turn.
  Either do it now or don't say it. There is no later; the session just ends.
- Describing the shape of a note you have not created.
- Claiming a change was logged when `logchange.py` didn't run or exited non-zero.

**Before ending any turn, check three things:**

1. Did I state or imply anything was written? Did that write actually run and
   succeed *in this turn*? If not, do it now, before sending.
2. **Did they tell me anything about themselves in this turn that I have not
   saved?** Scan their message again. Any fact, however small. If yes — save it now.
3. **Does every file I changed this turn have a line in today's `## Changes`?**
   Count them. Writes and log lines should match one to one.

**If they correct a fact or give a new one mid-conversation, the vault edit
happens in that same turn**, before the reply is composed.

---

## Capture immediately, not at the end

Write to the vault **in the same turn the thing comes up**, then mention it in
one short line — *"Made a note for that."* Don't ask permission, don't quote it
back, don't make a production of it.

Sessions have no clean end — the user just stops typing. Anything deferred to a
cleanup pass is lost.

## Bare facts count — they're the ones that get missed

The obvious triggers (a new show, a decision, a screenshot) rarely get dropped.
What gets dropped is a **plain fact stated in passing**, usually as an answer to
something else. When they say a number, a name, a spec, a grade, a date, a price
or a model, **that is a capture trigger even though it doesn't feel like one.**

Non-exhaustive — do not treat this as the list of what counts:

- School or work: grades, subjects, teachers, colleagues, deadlines, titles
- Hardware specs, part numbers, prices paid, where they bought it
- Software versions, addresses, usernames, IPs, seeds, coordinates, mod lists
- Names: people, teams, clubs, restaurants, shops, servers, pets
- Dates: when something starts, ends, was bought, is due, happened
- Money: income, spending, savings, regrets, what they're saving for
- Body and health: sleep, food, injuries, sport
- Plans, intentions, complaints, things that annoyed them, things they enjoyed
- Opinions about anything — a company, a tool, a person, a game
- Any correction to something already in the vault

The test: **if they'd have to look it up again to tell you tomorrow, write it
down.** They are having a conversation, not filing a report — the filing is your
job.

## Routing table — where things go by default

| What came up | Where it goes |
|---|---|
| **A durable personal fact — grades, family, routine, money, opinions, tastes, physical facts, how they want to be worked with** | The matching note in **`Atlas/About Me/`**. Start at its index. If no note fits, **make one there** and add it to the index table. |
| A show, film, book or game they're actually watching/reading/playing | **Its own note** in `Atlas/Media/<Title>.md`, from `AIOS/templates/media-note.md`. Characters they liked, opinions, where they are in it — all in that one note. Append on later mentions, don't create a second note. |
| Concrete game/world state — coordinates, seeds, server address, mods, version, builds | **Its own note** in `Atlas/Worlds/<World name>.md` |
| Something they're curious about but haven't started | A row in `Atlas/Radar.md` — that one stays a table, it's a queue, not a subject. When they start it, create the `Atlas/Media/` note and set the Radar row to `in progress`. |
| A concept they learned or were taught properly | **Its own note** in `Atlas/Knowledge/`, from the learn-note template |
| Hardware, network or software they own and use | `Atlas/Reference/` — `My machines.md`, `Home network.md`, `My software stack.md` |
| Anything about a project — decision, status change, a number with its source, a task they committed to | The existing note in `Efforts/` (decisions log, `## Status`, `## Next action`, `- [ ]`) |
| A new project | **Its own note** in `Efforts/`, from the project template, plus a row in `Efforts/Efforts.md` |
| A person who keeps coming up and isn't private | **Their own note.** Make `Atlas/People/` if it doesn't exist yet, with an index. Nothing from `Privat/`. |
| Something that happened on a given day, with no lasting subject of its own | `Calendar/Daily/YYYY-MM-DD.md` under `## Log`, timestamped `HH:MM`, appended |
| A contradiction, an unclear answer, or something worth confirming later | A row in `Atlas/About Me/Things to confirm.md` |
| A durable fact that changes how an AI works with them: a career shift, a standing preference, a skill they're now strong in | `AIOS/me.md` — conservative, and say so when you edit it |
| **Anything that fits none of the above** | **Make it a home.** See Rule Two. Do not skip it. |
| **A skill was created or changed** | Mirror it to `AIOS/skills/` — see below |
| **Every one of the above, without exception** | Plus one line in today's `## Changes` via `logchange.py` — see Rule Three |

**A fact usually belongs in two places, not one:** its subject note (permanent,
where anyone would look for it) *and* today's daily log (dated, so it's clear
when it became true). Grades, prices and specs all change — the dated entry is
what makes the history readable later.

> `## Log` and `## Changes` are different things and both exist in the daily note.
> `## Log` is **theirs** — thoughts and events, written by the `log` routine.
> `## Changes` is **yours** — an audit trail of vault writes. Don't mix them.

### Don't create a long catch-all file

There is no `profile.md`, no `facts.md`, no single `about-me.md` file, and none
should be created. If you find yourself wanting to append an unrelated fact to a
general file, that's the signal to make a note for the subject instead.

`Atlas/About Me/` is a **folder of separate subject notes** — Identity, Family,
Money, Opinions, and so on — not an exception to this rule. Adding a note there
is correct; turning any one of those notes into a dumping ground is not.

"Capture everything" and "one note per subject" are not in tension: the answer to
a fact with no home is **a new note**, never a longer file.

`me.md` is the one deliberately-central file, and it stays short.

**The daily note is not an exception either.** `## Changes` holds one-line
receipts pointing at other files. It is not where facts live.

## Mirror every skill into the vault

The vault should survive the user leaving this AI, and skills are part of that.
**Any time you create or update a skill, in the same turn write the same content
to `AIOS/skills/<name>/SKILL.md`** in the vault.

- Folder per skill: `AIOS/skills/<name>/SKILL.md`, plus `references/` and
  `scripts/` subfolders if the skill has them. This matches the layout Claude
  Code reads directly from `.claude/skills/`.
- Include the YAML frontmatter (`name`, `description`) — that's what makes the
  file portable to another tool. **Exactly one frontmatter block per file.**
- Also update the table in `AIOS/skills/README.md` if it's a new skill.
- For large vendor-bundled skills, mirror `SKILL.md` only — the helper scripts
  aren't worth syncing.
- Then log it: `--kind skill`.

If they say *"re-sync my skills to the vault"*, do a full pass over every
installed skill rather than just the one that changed.

## Screenshots and images are data — mine them

When they send a screenshot, don't just answer the question in it. Read **every**
concrete fact off the image and write them into the right note first — not just
the ones relevant to the question:

- Game screenshot → coordinates with dimension, biome, seed, version, mod list,
  server name or IP, what they've built, world name, day count →
  the `Atlas/Worlds/` note
- Terminal / error output → exact command, exact error, OS and versions, and the
  fix if it got fixed → the relevant `Efforts/` or `Atlas/Knowledge/` note
- A photo of a report card, receipt, label or box → every legible number, grade,
  model and date → the matching `Atlas/About Me/` or `Atlas/Reference/` note
- A photo of a room, desk or shelf → what's in it, hardware, books, posters
- A UI, an app, a store page → product, price, the settings they're running

These are exactly the details that are painful to recover later. Extract them
all, route them, then answer the actual question.

## Fun topics are not skippable topics

The classic failure is treating a casual conversation — a show they're watching,
a game, a book — as small talk not worth capturing. Which character they liked
and why **is** information about them.

There is no "when in doubt" here. In this category there is no doubt: **capture.**

## Transcripts: only when asked

**Do not automatically save chat transcripts.** "Save everything" means every
*fact*, not every *word*.

Transcripts happen only on request, via the `chronicle` / `save-chat` routine in
`AIOS/skill-map.md`: full verbatim conversation to
`AIOS/history/YYYY-MM-DD-<topic>.md`, with decisions, action items and open
questions above a `---`.

## Linking — what makes separate notes work

Separate notes only beat one long file if they're connected. Every note you
create gets:

- Frontmatter with `title` and `tags` per `vault-map.md`
- A `## Related` section linking **up** to its index (`[[About Me]]`, `[[Media]]`,
  `[[Worlds]]`, `[[Knowledge]]`, `[[Efforts]]`) and **across** to any genuinely
  related note
- Wikilinks inline where another note is mentioned
- A row in its folder's index table, if that folder has one

An orphan note is nearly as bad as a buried row.

## Keeping it readable at scale

Capturing everything means the vault grows fast. That's intended — the fix for
volume is **structure and linking, never filtering.**

If a note gets long or mixed, **split it into subject notes** rather than
trimming it. If a folder gets crowded, add subfolders and update the index.
Periodically `consolidate-memory` merges duplicates and fixes stale facts —
that's the pruning mechanism, and it runs on *duplicates and errors*, never on
"this seemed unimportant".

## Never

- **Decide a fact about them is too trivial to write down.** That call is theirs,
  and the answer is save it.
- **Skip a fact because there's no obvious note for it.** Make one.
- **Say something was saved when it wasn't.** See Rule Zero.
- **Write a file without logging it to today's `## Changes`.** See Rule Three.
- **Put the fact itself in `## Changes` instead of in a subject note.** The
  changelog is a receipt, not storage.
- Promise to write something "later" instead of writing it now
- Create a long catch-all file instead of a note per subject
- Change a skill without mirroring it to `AIOS/skills/`
- Overwrite anything they wrote themselves. Append.
- Read or write anything under `Privat/`
- Invent a decision they didn't actually make. If ambiguous, ask in one line.
- Delete or move existing notes without asking
- Save a full transcript they didn't ask for
- Touch `## Log` — that section is theirs, `## Changes` is yours
