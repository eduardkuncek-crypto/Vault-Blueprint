---
title: setup
tags:
  - reference
---

# setup — every script in the vault

> [!important] Opened on demand, never boot-loaded
> For actually setting the vault up on a new computer, see
> **`README-START-HERE.md`** (say "set yourself up") and
> `python3 AIOS/scripts/setup-check.py` for the self-check. This file is the
> reference catalog of what every script does, for when you want to know
> what's available without re-reading each docstring.

## Every script

### `AIOS/scripts/`

| Script | What it does |
|---|---|
| `setup.py` | First-run bootstrap: creates folders, tries to install the scheduled jobs (`backup-cowork`, `vault-snapshot`) using whatever this OS actually has. |
| `setup-check.py` | The one "is this actually working" command — Python version, `me.md` filled-in state, skills active, scheduler found, chat folder found, git set up, `vault-check.py` pass. |
| `scheduler.py` | Cross-platform cron/Task-Scheduler abstraction other scripts install jobs through. Not called directly. |
| `logchange.py` | Appends one line to today's daily note under `## Changes` on every vault write. Runs several guards (see its own docstring) that keep generated files honest — `where.md`, `commands.md`, `taste.md`, `scale.md`, `happened.md`. |
| `notelock.py` | Shared file-lock module, imported by `logchange.py` and `diary.py` — not run directly. Stops two scripts racing to write the same daily note. |
| `paths.py` | The path registry every other script can import instead of hardcoding a string. Run `python3 AIOS/scripts/paths.py` to print every registered path. |
| `move.py` | Move or rename a file/folder and rewrite every mention of the old path across the vault, in one command. Never `mv` a vault file by hand. |
| `verify.py` | `--snapshot` before a multi-file change, `--diff` after — what was touched, what was deleted, whether anything shrank suspiciously, whether `Privat/` was touched. |
| `vault-check.py` | Integrity pass: broken wikilinks, missing frontmatter, bad `status:` values, dead `dataview` blocks, stale skill list. Reports only. |
| `vault-map.py` | Rebuilds the note-count table in `AIOS/generated/scale.md`. Runs automatically on any note create/delete. |
| `route-check.py` | Rebuilds `AIOS/generated/where.md` (the one-grep note index); `--exists` checks whether a subject already has a note before you create a duplicate; `--dupes` finds existing collisions; `--naming` checks filenames against the scheme in `naming.md`. |
| `stale-check.py` | Finds notes whose content has probably gone stale (past its folder's shelf life) and notes nothing links to. Reports only, except `--fix-orphans`. |
| `canon-check.py` | Greps the vault for stale wording after a repeated fact gets corrected in `AIOS/reference/canon.md`. |
| `taste.py` | Compiles every note's `## Taste` section into `AIOS/generated/taste.md`, grouped by category. |
| `commands.py` | Rebuilds `AIOS/generated/commands.md` — every skill and routine trigger phrase, in one flat list — whenever `skill-map.md` changes. |
| `migration-scan.py` | Rebuilds the generated inventory block in `AIOS/reference/migration.md` (what skills/routines/scripts exist), for the `migrate` routine. |
| `context-budget.py` | Measures what loads before you type a word — the always-loaded floor — and flags growth. |
| `changelog-check.py` | Scheduled: catches a note that changed with no `## Changes` receipt. |
| `next-actions.py` | Rebuilds `Efforts/Next Actions.md` from every project's `## Next action` section and every open checkbox. |
| `project-status.py` | `project-status <name>` — where a project stands, what's blocking it, its next action, without opening the full note. |
| `event.py` | Dated things that aren't projects — a trip, an appointment. Creates `Calendar/Events/YYYY/<Title>.md` and keeps it linked into the days it covers. |
| `diary.py` | Appends to today's `## Diary`, and answers "when did I…" from `AIOS/generated/happened.md` — an index of every real-life event ever recorded. |
| `capture.py` | Batch-write to the vault (frontmatter fields, table rows, Radar entries, canon corrections, a diary line) without reading the target file first. |
| `chronicle.py` | Builds a curated write-up from an already-backed-up chat, instead of retyping the conversation. |
| `backup-cowork.py` | Copies your local Claude/Cowork chat history into the vault, readable and raw. Must run on your own machine. |
| `vault-snapshot.py` | Optional git commit + push of the whole vault, independent of Obsidian being open. |
| `blueprint-update.py` | Pulls improvements from the Vault Blueprint into this vault, as a list of yes/no questions. |
| `blueprint-manifest.py`, `blueprint-release.py` | Blueprint-side tooling for regenerating and releasing the blueprint itself — not relevant to a downstream vault. |
| `scriptlog.py` | Shared run-history logger, imported by other scripts — not run directly. Appends to `AIOS/history/scripts/<name>.md` on every run. |

## Where things live

See the folder map in `AIOS/vault-map.md` for the full picture. The short
version: `AIOS/reference/` is opened on demand, `AIOS/generated/` is
machine-written and never hand-edited, `AIOS/config/` is small
machine-readable state, `AIOS/history/` is every kind of automated history.

## If something looks wrong

```
python3 AIOS/scripts/setup-check.py
python3 AIOS/scripts/vault-check.py
```

Neither writes anything. Both tell you what's actually true instead of
assuming.

## Related

- [[vault-map]]
- [[routines]] — the plain-English procedures these scripts back
- [[me]]
