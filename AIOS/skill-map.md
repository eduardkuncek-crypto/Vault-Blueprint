# skill-map.md

> Dictionary of what tooling is available and when to use it. Skills are packaged
> instructions loaded by the AI. Routines live here in the vault as plain
> markdown, so you own them regardless of which AI you use.

## Installed skills

> [!warning] Keep this table honest
> If a skill gets installed or removed, update this table. An AI trusting a stale
> list will confidently reference tooling that isn't there. `vault-check.py`
> compares this file against what's actually installed and complains.

### Vault — the core five

| Skill | Use when |
|---|---|
| `auto-capture` | **Always on.** Captures decisions, status changes, facts, media, world state from screenshots, numbers, tasks and Radar interests as they come up. One note per subject, never a catch-all file. No transcripts unless asked. Mirrors any changed skill into `AIOS/skills/`. Every write gets a line in today's `## Changes`. |
| `vault-first` | **Always on.** Opens the matching note *before* answering anything about you or your stuff. Rule Two: never say a fact isn't saved without grepping for it first. |
| `vault-librarian` | **Always on when writing.** Where a new note goes, required frontmatter, tag scheme, naming, and how to invent a home when nothing fits. |
| `no-bullshit` | **Always on.** Fires before any claim you'll act on — specs, prices, versions, compatibility, "is this safe" — and whenever you push back or ask "are you sure". |
| `daily-brief` | Morning brief into today's daily note, and the `log` routine. |

### Worth installing (Anthropic's, one click)

| Skill | Use when |
|---|---|
| `morning` | Renders the morning brief as a styled HTML page instead of plain markdown |
| `consolidate-memory` | Periodic pass to merge duplicate notes and prune stale facts |
| `obsidian-markdown` | Writing notes — frontmatter, callouts, wikilinks |
| `obsidian-cli` | Reading/searching the vault from the command line |
| `schedule` | Setting up recurring automated tasks ("every morning at 6") |
| `skill-creator` | Building a new skill or fixing one that doesn't trigger reliably |
| `find-skills` | Looking for a skill that might already exist for something |
| `docx` `xlsx` `pptx` `pdf` | Documents, spreadsheets, decks, PDFs |

### Setup only — delete when done

| Skill | Use when |
|---|---|
| `setup-vault` | **The whole first-run bootstrap.** Triggers on "set yourself up" and similar — runs the setup scripts, gets the skills active for whatever platform this is, runs the interview from `AIOS/setup-questions.md`, and finishes with a real self-check. One skill, one trigger phrase, does everything. |

> [!note] Every skill is backed up in the vault
> Plain-markdown copies live in `AIOS/skills/<name>/SKILL.md`, re-exported
> automatically whenever a skill changes. That folder is the portability
> guarantee — it works in Claude Code as-is, and is readable by any other AI.

---

## Routines

Plain-language procedures. Say the name and the AI follows the steps. These are
deliberately not code and not provider-specific — **edit them in plain English.**

### `daily-brief`

Compile today's brief. Steps:

1. Pull today's events from a calendar connector and anything unread and
   important from mail, if either is connected.
2. Check deadlines in `Efforts/` and any project notes touched in the last 3 days.
3. **Check `Calendar/Cooldowns.md`** if it exists. Anything unlocking today goes
   near the top with the action it enables; anything within 7 days gets one line.
   Neither? Write nothing.
4. Output: what's on today, what's slipping, one suggested focus.
5. Write to `Calendar/Daily/YYYY-MM-DD.md` using `AIOS/templates/daily-note.md`.
   **Never overwrite what you already wrote — append.**

### `changelog`

**Runs without being asked, on every single vault write.** Not something you
invoke — something that happens automatically, enforced by Rule Three of
`auto-capture`.

```
python3 AIOS/scripts/logchange.py "what changed" "path/to/note.md" --kind edit
```

`--kind` defaults to `edit`. Others: `new`, `append`, `skill`, `script`,
`template`, `map`, `delete`. Several at once via stdin, tab-separated:

```
printf 'what\tpath\tkind\n...' | python3 AIOS/scripts/logchange.py --stdin
```

The script creates today's note from the template if it's missing, creates the
`## Changes` section if it's missing, and only ever appends. Non-zero exit on
failure — check it, don't assume.

**The daily note is the receipt. The subject note is still the content.**

Lines must be specific enough to be useful in six months:

- **Good:** `Status stalled → active after the disk resize finished → Efforts/Old Laptop.md`
- **Useless:** `Updated a note`

Why it exists: `me.md` says *never tell me something was saved before it was*,
and without this there's no way to check. Now you open today's note and see the
receipts.

### `log`

You dictate or type a quick unstructured thought. The AI cleans it up minimally
(keeps your voice, fixes nothing but obvious typos), timestamps it `HH:MM`, and
appends it to today's daily note under `## Log`.

### `next`

The "what do I actually do now" page. Run:

```
python3 AIOS/scripts/next-actions.py
```

It regenerates `Efforts/Next Actions.md` from two sources it never invents: every
project note's `## Next action` section, and every open `- [ ]` checkbox outside
`Privat/`. Then read the live table.

Source of truth stays in the project notes — the generated file is disposable. If
a project has no `## Next action` section, the script names it at the bottom
rather than silently skipping it.

### `cooldown`

**Runs without being asked.** Any time a fixed waiting period comes up — in
conversation, in a screenshot, in an email — log it in `Calendar/Cooldowns.md`.

The trigger is any sentence shaped like *"you can only do this every N days"* or
*"not available until <date>"*. **Triviality is not a filter.** A username change
cooldown, a free trial ending, a returns window, a warranty, a cashback deadline,
a form that can only be submitted once a month — all of them get a row.

1. Compute the unlock date with a real command, never mentally:
   `date -d "<start date> +N days" +%F`.
2. Add a row to the **Open cooldowns** table, soonest first, linked to wherever
   the full detail lives.
3. If missing it would actually annoy you, also create a **one-off scheduled
   task** firing on that date. Table = the record, scheduled task = the poke.
4. When the date passes and you've acted, move the row to **Passed** with what
   you did. Don't delete it.

### `vault-check`

Integrity pass. Run:

```
python3 AIOS/scripts/vault-check.py
```

Reports broken wikilinks, missing frontmatter, notes not reachable from their
folder index, `status:` values outside the allowed vocabulary, dead `dataview`
blocks, skills installed but missing from this file, and sync conflict files.
**Reports only — it changes nothing.** Run it monthly, or whenever the vault
feels wrong.

A conflicted `.md` file is a real problem — two machines edited a note and one
version is hiding, so diff before deleting. A conflicted `.obsidian/*.json` is
just junk from two machines having Obsidian open at once; delete it.

### `context-budget`

```
python3 AIOS/scripts/context-budget.py            # report
python3 AIOS/scripts/context-budget.py --baseline # reset the baseline
```

Measures what loads before you type a word — skill descriptions, boot files,
always-on skill bodies — and shouts if the floor has grown >10% since the
baseline. **Reports only.**

Run it before adding text to any always-on file. This is the thing that stops
the setup quietly getting dumber as it grows: notes are loaded on demand and are
effectively free, but the always-on instruction layer is paid in full on every
single session.

### `backup-cowork`

Copy your Claude/Cowork chat history into `AIOS/history/chat-history/cowork/`
(readable Markdown) and `cowork-raw/` (exact originals). **Must run on your own
machine, not from inside a cloud AI session** — a cloud session can't reach
your local Claude app's files; that's not a bug, it's how sandboxing works.

```bash
python3 AIOS/scripts/backup-cowork.py                                 # run once
python3 AIOS/scripts/backup-cowork.py --install-schedule --every-min 60  # + schedule it
```

Read-only on the source, never deletes, skips unchanged files. Checks every OS's
known storage location and uses whichever one exists — see the script's own
docstring if it can't find yours. `setup.py` installs the schedule for you using
whatever this OS actually has (cron on Linux/macOS, Task Scheduler on Windows) —
see `scheduler.py` if you're curious how.

### `vault-snapshot`

Optional. Commits the vault to git and pushes it, independently of whether
Obsidian is even open. Nothing else in this vault requires this to work.

```bash
python3 AIOS/scripts/vault-snapshot.py                                    # commit + push now
python3 AIOS/scripts/vault-snapshot.py --install-schedule --every-min 10  # + schedule it
```

Writes `AIOS/generated/git-status.md` every run — that file is the honest
answer to "is this actually backed up", since an AI reading the vault often
can't run `git status` itself. First run creates the repo if there isn't one
yet; a remote (GitHub, GitLab, your own server) is optional — without one it
just commits locally.

### `setup-check`

The single "is this actually working" command. Run it any time, especially
right after setup and again a day or two later:

```
python3 AIOS/scripts/setup-check.py
```

Tests, doesn't assume: Python version, `me.md` filled-in state, which skills
are present and whether they're active in `.claude/skills/`, whether a
scheduler was found and which jobs are really installed in it, whether your
chat folder was found, whether git is set up, and a `vault-check.py` pass.
Every line is something the script actually just checked, not a guess.

### `canon-check`

Optional, once you have your first repeated fact worth tracking. Add a row to
`AIOS/reference/canon.md` — the true version of a fact, which note owns it,
and the stale wording that shouldn't appear anywhere else — then:

```
python3 AIOS/scripts/canon-check.py
```

It greps the whole vault for the stale wording and reports every hit. Run it
right after correcting anything that's repeated in more than one note.

### `changelog-check`

**Runs on its own if scheduled** (`setup.py` does this). Notices a note whose
content changed with no `## Changes` receipt for it today, and appends a
catch-line so the miss doesn't disappear silently. First run ever only builds
a baseline — it can't know what changed before it existed.

### `project-status <project>`

Read the project's note in `Efforts/`, then say in under 200 words: where it
stands, what's blocking it, and the single next action. No summary of things
already known.

### `decide <question>`

When stuck between options. Lay out the real trade-offs with numbers where
numbers exist, give a recommendation, and say what would change your mind. Then
write the decision into the project note's decisions log once picked.

**Don't guess the numbers.** Search for specs and prices, or say plainly you're
unsure.

### `learn <topic>`

Scaffold a new topic: what it is, why it matters to you, the 5 things to learn in
order, and one concrete thing to build this week. Create a note in
`Atlas/Knowledge/` from `AIOS/templates/learn-note.md` and link it to related
existing notes.

### `weekly-review`

Sunday pass. Read the week's daily notes. What actually got finished, what was
promised and didn't happen, which projects went untouched, and what to drop. Be
blunt — the point is catching things that slipped. Write to
`Calendar/Weekly/YYYY-Wnn.md` from `AIOS/templates/weekly-review.md`.

### `rock-tumbler <note or text>`

Feedback on creative writing without rewriting it. Your voice is the asset —
don't let an AI replace it with its own.

Ask open-ended questions using the **IDI** framework:

1. **Imagine** — what could this become? What's the version of this that's more
   itself, not more conventional?
2. **Discern** — what's actually working here, and what's doing nothing? Where
   does a reader lose the thread?
3. **Integrate** — how does this connect to what already exists in the vault?
   What contradicts something established elsewhere?

Rules: questions over prescriptions, roughly 3:1. Point at logic gaps and
structural problems directly — don't soften those. Never rewrite a passage
unless explicitly asked.

### `chronicle` / `save-chat`

Write the whole conversation verbatim into
`AIOS/history/chat-history/curated/YYYY-MM-DD-<topic>.md` (kept separate from
the auto-generated `cowork/` folder, which gets overwritten on every backup
run). At the top of the file, before the transcript:

1. **Decisions made** — with enough context to be useful in six months
2. **Action items** — concrete
3. **Open questions** — what didn't get resolved

Then the verbatim transcript below a `---`. Verbatim means verbatim, typos
included.

### `courier <note>`

Prepare a note for someone else's eyes. Steps:

1. Read the note plus any notes it wikilinks to.
2. Strip anything personal: names of family, health, money, anything from a daily
   note's log, anything that reads like a diary entry.
3. Replace wikilinks with either a short inline summary of the linked note or
   nothing — the recipient can't follow vault links.
4. Output as a standalone file. Markdown by default; use the `docx` or `pdf`
   skill if it warrants it.
5. **Show the sanitised version before it leaves.** Every time.

Never courier anything from `Privat/`. Never read `Privat/` at all.

### `tidy`

Housekeeping. Find notes with no links, inconsistent tags, obvious duplicates,
untitled/orphan files, and frontmatter that doesn't match the conventions in
`vault-map.md`. **Propose a list first. Change nothing until approved.**

---

## Adding a routine

Write it here in the same shape: a name, then numbered steps in plain language.
That's it. No code, no config, no provider-specific format. If you ever leave
this AI, this file still works.

## When to promote a routine into a skill

A routine becomes worth turning into a real skill when:

- You run it more than about once a week, **and**
- It needs to trigger automatically without you naming it, **or**
- It needs reference files, scripts, or more instructions than fit here readably.

Use the `skill-creator` skill to do it, and keep the routine here as the
plain-markdown fallback.

## Related

- [[Home]]
- [[me]]
- [[vault-map]]
- [[how-to-use-this]]
