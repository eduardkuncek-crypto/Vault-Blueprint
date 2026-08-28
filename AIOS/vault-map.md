# vault-map.md

> Table of contents for the vault. Its job is to stop an AI blindly sampling
> files and burning context. It should always answer: **"where do I look for X?"**

> [!important] This file is meant to be edited constantly
> It ships as a description of the *design*. The moment you have real notes, it
> becomes a description of *your* vault — add the specific rows, delete what you
> don't use. A map that doesn't match reality is worse than no map, because it
> sends the next session to the wrong place confidently.

## Vault root

`<< path to this folder, e.g. ~/Dropbox/My Vault >>`

Keep it on a real local disk that syncs, not a network or FUSE mount — some AI
tools can't read those. If an AI ever can't see the vault, that's the first thing
to check.

## Folder map

The structure is **ACE**: Atlas (things that stay true), Calendar (things tied to
a date), Efforts (things you're actively pushing). Plus `AIOS/` for the AI layer
and `Privat/` for the part no AI touches.

| Folder | What lives here | AI may write? |
|---|---|---|
| `Privat/` | The private half. Diary, people, anything you don't want an AI reading. | **NO — do not read or write** |
| `AIOS/` | The AI operating system layer: identity, maps, templates, scripts, skill copies. Root holds the boot files (`me.md`, `character.md`, `vault-map.md`, `skill-map.md`) plus subfolders. | Yes |
| `AIOS/templates/` | Note templates: daily, event, project, learn note, media note, weekly review. | Yes |
| `AIOS/scripts/` | Small Python scripts that read the vault and report or regenerate. No dependencies, plain stdlib, cross-platform (Linux/macOS/Windows). Start with `setup.py` and `setup-check.py` — the rest are named after the routine that runs them (see `AIOS/skill-map.md`), and each has its own docstring. Full catalog: `AIOS/reference/setup.md`. | Yes |
| `AIOS/skills/` | Plain-markdown master copies of every installed skill. The portability guarantee — and, on platforms without native skill install, the actual working copy an AI reads and follows directly. | Yes |
| `AIOS/history/chat-history/cowork/` | **Generated automatically**, on a schedule, by `backup-cowork.py` — every conversation as readable Markdown. Don't read at session start; open one only when asked about an old conversation. | **No — machine-written** |
| `AIOS/history/chat-history/cowork-raw/` | **Generated.** The same conversations exactly as Claude stored them (`.jsonl`) — the real backup; the Markdown above is for reading. | **No — machine-written** |
| `AIOS/history/chat-history/curated/` | Curated write-ups from `chronicle`/`save-chat` — decisions and action items pulled to the top. | Yes — append only |
| `AIOS/history/scripts/` | **Generated.** One run history note per script, appended automatically by `scriptlog.py` every time any script runs. | **No — machine-written** |
| `AIOS/generated/` | **Generated, never hand-edited.** `git-status.md` (is the optional git backup committed/pushed), `where.md` (one-grep note index), `commands.md` (every trigger phrase, flat), `taste.md` (every `## Taste` section, compiled), `happened.md` (every diary event, indexed), `scale.md` (per-folder note counts). | **No — machine-written** |
| `AIOS/reference/` | Docs opened on demand, never at session start: `canon.md` (facts repeated in more than one note), `naming.md` (naming scheme + duplicate check), `vault-conventions.md` (tags, status values, daily-note anatomy), `routines.md` (full steps for every routine), `moves.md` (register of every relocation), `migration.md` (hand-to-a-different-AI file), `setup.md` (every script, cataloged), `blueprint-changes.md` (what each blueprint update actually does, in plain English). | Yes |
| `AIOS/config/` | Machine-readable state. `blueprint-manifest.json` says which shipped files belong to the blueprint versus to you; `blueprint-state.json` remembers which blueprint version you're on and what you've already said no to. | **Written by scripts — safe to delete, you'll just get re-asked once** |
| `AIOS/history/blueprint-updates/` | **Generated.** A dated copy of every file a blueprint update overwrote, taken before it was overwritten. This is what makes `--undo` real instead of a promise. | **No — machine-written** |
| `Atlas/` | Knowledge, reference, clippings. Timeless material. | Yes |
| `Atlas/About Me/` | The long version of `me.md` — **one note per subject** about you as a person. | Yes |
| `Atlas/Knowledge/` | Notes written to understand a concept. Output of `learn`. | Yes |
| `Atlas/Reference/` | Cheatsheets, command lists, specs, your own hardware and accounts. | Yes |
| `Atlas/Clippings/` | Saved web articles with summaries. | Yes |
| `Atlas/Media/` | One note per show/book/game you're actually watching, reading or playing. | Yes |
| `Atlas/Worlds/` | One note per game world/save/server — coordinates, seeds, mods, versions. | Yes |
| `Atlas/Radar.md` | Things you're curious about but haven't started. A queue, not a subject. | Yes — append |
| `Calendar/` | Anything anchored to a date. | Yes |
| `Calendar/Daily/` | `YYYY-MM-DD.md`. Brief + Diary + `## Changes` audit trail — see [[vault-conventions]] for what owns each section. | Yes — **append only** |
| `Calendar/Weekly/` | `YYYY-Wnn.md`. Output of `weekly-review`. | Yes |
| `Calendar/Events/` | `YYYY/<Title>.md` — a trip, an appointment, anything dated that isn't a project. Created by `event.py`, never by hand; it links itself into every daily note it covers. | Yes — via `event.py` |
| `Efforts/` | Active projects, one note each. | Yes |
| `Inbox/` | **Drop zone** — `Screenshots/` and `Files/`. Dump things here with no naming; the AI reads the facts off them and files them. **A file sitting here is unprocessed.** | Yes — and empty it once processed |
| `Attachments/` | Images already embedded in a note. Stops screenshots landing at the vault root. | Yes |
| `.obsidian/` | Obsidian config and plugins. | Only if asked |

> [!tip] New subfolders under `Atlas/` are encouraged
> When a fact has no home, the answer is a new note — and if the whole category
> is missing, a new subfolder with an index note. Register it here in the same
> turn. **Don't create new top-level folders** without asking; that changes the
> ACE structure everything else assumes.

## Where to look for what

Add a row every time you create something an AI would struggle to find. This
table is the difference between one file read and a folder scan.

| If I ask about... | Look in |
|---|---|
| **What should I do now / today / next** | `Efforts/Next Actions.md` — regenerate first with `python3 AIOS/scripts/next-actions.py` |
| **Is the vault healthy** | `python3 AIOS/scripts/vault-check.py` — reports only, changes nothing |
| **Is the automation actually working** — chat backup, scheduled jobs, skills, `me.md` | `python3 AIOS/scripts/setup-check.py` — one pass/fail table, checks everything instead of assuming |
| **Setting the vault up on a new computer**, or first-run setup | Say **"set yourself up"** — runs the `setup-vault` skill. Or directly: `python3 AIOS/scripts/setup.py` |
| **Has the blueprint improved since I downloaded it** | Say **"update my vault from the blueprint"** — runs the `update-vault` skill. Or directly: `python3 AIOS/scripts/blueprint-update.py`. It never overwrites anything you wrote |
| **What blueprint suggestions have I turned down** | `python3 AIOS/scripts/blueprint-update.py --show-declined` |
| **Put back what the last update changed** | `python3 AIOS/scripts/blueprint-update.py --undo` |
| Old conversations / chat transcripts | `AIOS/history/chat-history/cowork/` — generated automatically, don't edit |
| Whether the optional git backup is working | `AIOS/generated/git-status.md`, written by `vault-snapshot.py` |
| **What did the AI change, and when** | `Calendar/Daily/YYYY-MM-DD.md` → `## Changes` |
| **What I'm working on overall** | `Efforts/Efforts.md` — the live status table |
| **Who I am / how to work with me** | `AIOS/me.md` |
| **How I want an AI to behave** | `Atlas/About Me/Working with AI.md` |
| **What I can actually do, and what needs explaining** | `Atlas/About Me/Tech skill inventory.md` |
| **My favourite anything** — film, meal, colour, game | `Atlas/About Me/Preferences and tastes.md` §Named favourites — the index. Never answer "that isn't saved" without opening it |
| **Anything personal — family, food, money, opinions, routine** | `Atlas/About Me/` — start at its index |
| A show/book/game I'm watching or playing, or a character I liked | `Atlas/Media/<Title>.md` |
| Game coordinates, a seed, a server, a world save | `Atlas/Worlds/<World>.md` |
| Something I want to check out but haven't started | `Atlas/Radar.md` |
| My PC / laptop / phone specs | `Atlas/Reference/My machines.md` |
| Wi-Fi, router, ISP | `Atlas/Reference/Home network.md` |
| What software I use | `Atlas/Reference/My software stack.md` |
| What accounts I have and what I'm paying for | `Atlas/Reference/My online accounts.md` |
| **Something I dropped in for you to deal with** | `Inbox/` — say "check my inbox" |
| **When did I do X / find out about my own past events** | `python3 AIOS/scripts/diary.py --when "<thing>"` — never answer this from memory |
| **A trip / appointment / exam week — anything dated that isn't a project** | `Calendar/Events/YYYY/` — `python3 AIOS/scripts/event.py --today` / `--upcoming 14` answer "what's on" without opening a note |
| What tooling exists | `AIOS/skill-map.md` |
| **What every script does** | `AIOS/reference/setup.md` |
| Daily notes / journal | `Calendar/Daily/` |
| Weekly reviews | `Calendar/Weekly/` |
| A specific project | `Efforts/<Project>.md` — **add a row here per project** |
| **Does a note for this already exist** | `python3 AIOS/scripts/route-check.py --exists "<subject>"` — before creating anything |
| Private diary | **Nowhere. Don't.** |

## Reading order for a new session

1. `AIOS/me.md` — identity and working rules
2. `AIOS/character.md` — voice and tone, if you've customised it. How the AI
   talks, not what it does — behavior rules stay in `me.md`.
3. This file — where things are
4. `AIOS/skill-map.md` — what tooling exists
5. `Atlas/About Me/Working with AI.md` — **always. No condition.**
6. Then, **only if relevant to the request**, the specific project note.

> [!failure] Step 5 used to have a condition on it, and the condition failed
> It said "read this if the session involves doing real work rather than
> answering a question." An AI has to *judge* that, and a condition an AI has to
> judge is a condition it will skip. Made unconditional. Learn from it: don't put
> judgement calls in rules you need to actually fire.

Do not scan `Efforts/` or `Atlas/` wholesale. Use this map to open the one or two
files that matter.

## Naming, tags, status values, daily-note anatomy

Moved to **`AIOS/reference/vault-conventions.md`** — mechanics for *writing* a
note, not for finding one, so it doesn't need to be boot-loaded. Opened on
demand, or by the `vault-librarian` skill when it fires. The naming scheme and
the before-you-create-a-note duplicate check live in **`AIOS/reference/naming.md`**.

## Scale — per-folder note counts

Moved to **`AIOS/generated/scale.md`** — a hand-typed count goes stale the
moment it's written, and a script can count more reliably than a human can
retype. Rebuilt automatically by `vault-map.py` on every note create/delete;
nags out loud once the vault has grown noticeably since the folder map above
was last reviewed. Stamp a review: `python3 AIOS/scripts/vault-map.py --reviewed`.

## Related

- [[Home]] — vault entry point
- [[me]] — identity
- [[skill-map]] — tooling
- [[vault-conventions]] — naming, tags, status values, daily-note anatomy
- [[naming]] — one subject, one note, and the check that keeps it that way
- [[how-to-use-this]] — the one guide
- [[scale]] — per-folder note counts
