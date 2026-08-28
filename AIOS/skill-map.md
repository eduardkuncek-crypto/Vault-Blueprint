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

### Staying current

| Skill | Use when |
|---|---|
| `update-vault` | **"update my vault from the blueprint".** Fetches the latest blueprint, works out what's genuinely different from *your* vault, reads the changes out in plain English, and applies only what you pick. Never overwrites anything you wrote. Keep this one — it's how every future improvement reaches you. |

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
deliberately not code and not provider-specific — **edit them in plain
English.** This table is the lookup; **`AIOS/reference/routines.md`** carries
the full steps for each one — open it when a routine is actually running, not
at session start.

| Routine | Fires | One line |
|---|---|---|
| `message-capture` | Start of every session | Scan the incoming message for facts, decisions, plans, questions — route each to the right note. |
| `daily-brief` | On request, or scheduled | Calendar + mail + deadlines + cooldowns → today's daily note. |
| `capture` | Any blind append (Radar/canon/frontmatter/table row/diary) | One command via `capture.py` — never open the file first. |
| `diary` | Any real-life thing you mention | One plain line into today's `## Diary`. `python3 AIOS/scripts/diary.py "..."` |
| `when` | "When did I…" about anything that happened | `python3 AIOS/scripts/diary.py --when "<thing>"` — answers from the generated index or says plainly there's no record. |
| `event` | A dated real-life thing that isn't a project — trip, appointment, exam week | `python3 AIOS/scripts/event.py "<Title>" --start YYYY-MM-DD [--end YYYY-MM-DD]`. Links itself into every daily note it covers. |
| `changelog` | Every single vault write, no exception | `logchange.py` appends the receipt and runs a few guards that keep generated files honest. |
| `log` | You dictate a thought | Timestamp, clean typos only, append to today's diary. |
| `next` | On request | Regenerate `Efforts/Next Actions.md` from project notes. |
| `cooldown` | Any fixed waiting period, unprompted | Compute the unlock date for real, row in `Cooldowns.md`. |
| `vault-map` | Any note created/deleted | Rebuilds the note-count table in `AIOS/generated/scale.md`. |
| `route-check` | Any note created/deleted | Rebuilds `AIOS/generated/where.md`, the one-grep index. |
| `naming` | Before creating any note | Checks this subject doesn't already have a note. |
| `relocate` | Any time a file/folder needs to move or be renamed | `move.py` — moves it and rewrites every mention across the vault. Never `mv` by hand. |
| `verify` | Before/after a multi-file change | Snapshot/diff — did anything break, in numbers. |
| `vault-check` | Monthly or on request | Broken links, bad frontmatter, stale skill list. |
| `context-budget` | Any boot-file write | Measures the always-loaded floor. |
| `backup-cowork` | Hourly (your own machine's scheduler) | Chat history → `AIOS/history/chat-history/cowork/`. |
| `vault-snapshot` | Every 10 min (optional, your own machine) | git commit + push, writes `git-status.md`. |
| `update-vault` | "update my vault from the blueprint" | Pulls in blueprint improvements as yes/no questions. Never overwrites your writing. |
| `setup-check` | On request, especially after setup | One pass/fail table — is the automation actually working. |
| `canon-check` | `canon.md` touched (immediate) | Finds notes still repeating a corrected fact. |
| `stale-check` | Weekly (if scheduled), or on request | EXPIRED / ORPHAN / NO ROUTE report. |
| `changelog-check` | Timer, if scheduled | Catches a write with no `## Changes` receipt. |
| `project-status <project>` | On request | Where it stands, what's blocking it, next action. |
| `decide <question>` | On request | Trade-offs with numbers, a recommendation. |
| `learn <topic>` | On request | Scaffold a new `Knowledge/` note. |
| `weekly-review` | Sunday (if scheduled) | What got done, what slipped. |
| `rock-tumbler <note>` | On request | IDI feedback on writing, never rewrites. |
| `chronicle` / `save-chat` | On request | Curated write-up from an already-backed-up chat. |
| `migrate` | On request — "make vault migratable" | Refreshes `AIOS/reference/migration.md`'s inventory. |
| `courier <note>` | On request | Strip personal info, show before it leaves. |
| `tidy` | On request | Housekeeping list — propose first, change nothing. |

## Adding a routine

Full steps go in `AIOS/reference/routines.md`, same shape as the others there.
Add one row to the table above so it can be found without opening that file.

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
- [[routines]] — the full steps for every routine above
- [[how-to-use-this]]
