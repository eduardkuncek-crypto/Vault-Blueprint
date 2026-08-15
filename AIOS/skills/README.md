---
title: AIOS Skills
tags:
  - index
---

# AIOS/skills

Master copies of the skills this vault depends on, in plain markdown, in the
vault, in version control.

> [!warning] These are copies. How they become "active" depends on the platform.
> Skills don't run from the vault by themselves — they need to either be
> registered with your AI tool, or read directly. **Which one happens depends
> on what you're using, and it's worth knowing the difference so nothing
> silently doesn't work:**
>
> - **Claude Code (a terminal)** — copy each folder into `.claude/skills/`
>   (`AIOS/skills/auto-capture/` → `.claude/skills/auto-capture/`, and so on).
>   That's it. No upload, no asking the AI to "install" anything — Claude Code
>   reads that folder directly, every session, automatically. The `setup-vault`
>   skill does this copy for you the first time.
> - **Cowork** — a session **cannot silently create an account-level skill for
>   you**; the platform requires you to click save on it yourself. If you ask
>   an AI to "install" a skill here and it claims success without you having
>   clicked anything, that claim is wrong — this was the exact failure that
>   made an earlier version of this blueprint unreliable. The honest version:
>   the AI can package a skill as a downloadable `.skill` file for you to save,
>   **and/or** just read the `SKILL.md` files directly and follow them for the
>   session, which works identically without any install step at all —
>   `CLAUDE.md` tells every session to do exactly that as a fallback.
> - **Anything else that can read this folder** — same fallback: read the
>   `SKILL.md` files and follow them. That's the whole point of a skill being
>   plain markdown instead of code — nothing about "activating" it is actually
>   required for it to work, it's just an optimization some platforms offer.
>
> To change a skill later, edit its `SKILL.md` here directly (or ask the AI
> to), and re-copy to `.claude/skills/` if you're on Claude Code.

## Why keep copies here at all

1. **Backup.** If a skill gets deleted or corrupted, the text is here.
2. **Claude Code uses this format directly.** Copy a folder to
   `.claude/skills/<name>/SKILL.md` and Claude Code picks it up with no upload
   step.
3. **Portability.** `SKILL.md` is just markdown with frontmatter — a name, a
   description, and instructions in prose. Move to a different AI and these come
   with you, readable by anything.

## Structure

```
AIOS/skills/<name>/SKILL.md
AIOS/skills/<name>/references/...   (if the skill has them)
AIOS/skills/<name>/scripts/...      (if the skill has them)
```

**Exactly one YAML frontmatter block per file.** A duplicated block is silently
read as body text and the skill's description stops working.

## What's in here

| Skill | What it does | Keep? |
|---|---|---|
| `auto-capture` | Writes facts into the vault **without being asked**. One note per subject. **This is the one that makes the vault fill itself.** | Yes |
| `vault-first` | Opens the matching note *before* answering anything about you. Stops generic answers about your own life. | Yes |
| `vault-librarian` | Where a note goes, frontmatter, tags, naming, hard rules. The other half of `vault-first`. | Yes |
| `no-bullshit` | Fires before any claim you'd act on. Search-or-mark-unverified, plus a required case-against on any recommendation. | Yes |
| `daily-brief` | Morning brief into today's daily note, plus the `log` routine. | Yes |
| `setup-vault` | Runs the first-run interview. **Delete once you're set up.** | No |

## Not in here on purpose

These are shipped by Anthropic and installable in one click. Copying them into a
vault only guarantees you end up running a stale version:

`docx` · `pptx` · `xlsx` · `pdf` · `obsidian-markdown` · `obsidian-cli` ·
`schedule` · `skill-creator` · `find-skills` · `consolidate-memory` · `morning`

Two of those are worth turning on early:

- **`morning`** — renders your daily brief as a proper HTML page instead of
  plain markdown.
- **`consolidate-memory`** — periodic pass that merges duplicate notes and prunes
  stale facts. Run it every month or so once the vault is real.

## Keeping them in sync

`auto-capture` re-exports a skill here whenever one is created or changed, in the
same turn. If you ever suspect drift, say *"re-sync my skills to the vault"* to
force a full pass.

## Related

- [[skill-map]] — what each skill is for and when it fires
- [[how-to-use-this]] — the guide
- [[me]]
