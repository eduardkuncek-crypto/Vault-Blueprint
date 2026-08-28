---
name: "setup-vault"
description: "The first-run bootstrap for a fresh vault built from this blueprint. Use when the user says \"set yourself up\", \"set up this vault\", \"get started\", \"install this\", \"initialize the vault\", \"run the vault setup\", \"process my setup answers\", or when AIOS/me.md still contains << >> placeholders and they want to start using the vault. Also use to resume a partly-finished setup, or to go deeper on the interview later. This is the ONE skill a brand-new user needs to trigger — everything else follows from it."
---

# Setup Vault

The user has a fresh, empty vault built from this blueprint and just asked you
to set it up. **Do the whole thing in this one conversation, without waiting
to be asked again for each part.** They should not need to know the phrases
"run the setup interview" or "process my setup answers" — "set yourself up"
means all of it: folders, automation, skills, and the interview, in order,
reporting honestly as you go.

This skill is written to work the same way regardless of whether you're
Claude Code in a terminal, Cowork on the user's own computer, Cowork in a
cloud session, or a different AI entirely reading this file directly. Where
those genuinely differ, it says so explicitly rather than assuming one of
them.

## The whole flow, in order

1. **Say what you're about to do**, in three sentences, before doing it. Not a
   wall of text — just: you're going to create some folders, try to turn on
   automatic chat backup, get the vault's skills active, then ask some
   questions about them. Should take a few minutes plus however long they
   want to spend on the questions.
2. **Run the scripts** (§1 below).
3. **Get the skills active** (§2 below) — do the part that's actually
   possible on this platform; be honest about the part that isn't.
4. **Run the interview**, starting immediately, Section 1 only unless they
   say otherwise (§3 below).
5. **Run the self-check and report it straight** (§4 below) — this is not
   optional. Never tell the user setup succeeded without having just run the
   check that confirms it.
6. **Explain how the thing actually works**, briefly, in plain language (§5
   below) — this is what makes the difference between someone who trusts the
   system and someone who doesn't.

If you're resuming a partly-finished setup (some placeholders in `me.md` are
gone, some scripts are already scheduled), **skip what's already done and say
so in one line.** Redoing finished work wastes their time and makes it look
like nothing was remembered.

---

## §1. Run the scripts

From the vault root:

```bash
python3 AIOS/scripts/setup.py
```

Run it with the Bash tool (or your platform's equivalent) and **show the user
what it actually printed** — don't paraphrase "it worked." This script:
creates the folders the automation needs, finds whatever job scheduler this
OS actually has (cron on Linux/macOS, Task Scheduler on Windows) and installs
the chat-backup, changelog-check and (if `git` is present) vault-snapshot
jobs through it, then runs a vault health check.

**If `python3` isn't found**, try `python`. If neither exists, stop here and
give the exact install command for their OS — don't guess or skip this step:

- Linux (Debian/Ubuntu/Mint): `sudo apt install python3`
- macOS: `brew install python3` (or point them at python.org if they don't have Homebrew)
- Windows: https://www.python.org/downloads/windows/ — tell them to tick
  "Add python.exe to PATH" during install, that's the step everyone misses

**Read what the script prints.** It marks each thing `[ok]`, `[YOU]` (needs a
human to do something — a download link or a command to run), or `[!!]`
(actually failed). Relay the `[YOU]` and `[!!]` lines to the user verbatim —
those are exactly the things you cannot do for them.

**One honest limitation, worth saying to the user in your own words if it
applies:** if this session is running in a disposable cloud sandbox rather
than on the user's own computer, the scheduled jobs this step installs will
look successful and then quietly not exist tomorrow, because the whole
container gets thrown away. There's no reliable way to detect this from
inside the script. If you have reason to think that's the situation — this
looks like a cloud AI session rather than a local terminal — say so plainly
and suggest running `setup.py` again from a real terminal on their machine
(or Cowork's on-device mode) for the automation to actually stick. Don't
suppress this warning just because it's awkward to say.

## §2. Get the skills active

The seven skills in `AIOS/skills/` (`auto-capture`, `vault-first`,
`vault-librarian`, `no-bullshit`, `daily-brief`, `update-vault`, and this one)
are markdown files, not automatically-running code. How they become "active"
genuinely depends on what's reading this file right now — do the right one,
and tell the user which one you did.

**If you can run shell commands against a real local filesystem** (Claude
Code in a terminal, or Cowork running directly on the user's computer) —
copy them into `.claude/skills/`, which Claude Code (and Cowork when it's
running locally) reads automatically, no separate install step or user
action required:

```bash
mkdir -p .claude/skills
for d in AIOS/skills/*/; do
  name=$(basename "$d")
  [ "$name" = "README.md" ] && continue
  mkdir -p ".claude/skills/$name"
  cp -r "$d"/. ".claude/skills/$name/"
done
```

Then verify it actually landed — list `.claude/skills/` and confirm all seven
folders are there with a `SKILL.md` inside each, and say so with the actual
count, not "done."

**If you're Cowork running in a cloud session** — you cannot silently create
an account-level skill from inside a session; the platform requires the
user's own action to save one (this is a genuine platform boundary, not a
bug to work around). Do both of these:

1. Tell the user plainly: *"Cowork skills need your say-so to save — I can't
   silently install them. I'll package each one so you can save it with one
   click."* Then produce each `AIOS/skills/<name>/SKILL.md` as a downloadable
   `.skill` file and deliver it, so the user gets a save option per skill.
2. **Regardless of whether they save any of them**, treat this vault's
   `AIOS/skills/*/SKILL.md` files as active instructions for the rest of
   *this* session and say so: read `auto-capture`, `vault-first`,
   `vault-librarian` and `no-bullshit` now, in full, and follow them for the
   rest of the conversation. This is the fallback that makes the vault work
   correctly even before — or without — the user ever saving a native skill.
   `AIOS/vault-map.md` already tells any competent session to open
   `AIOS/skills/` when behavior is unclear; make that explicit here too, in
   `CLAUDE.md`'s reading list, so it's true on every future session as well,
   not just this one.

**If neither applies** (a bare chat interface with no file access) — this
skill can't have triggered at all, since it requires reading files from the
vault. Nothing to do here.

Either way, tell the user honestly which parts are "actually installed" vs.
"working because I'm reading the files directly" — both are fine outcomes,
but claiming the first when it's really the second is exactly the kind of
false confidence that broke trust in this system before.

## §3. Run the interview

Read `AIOS/setup-questions.md` — that's the question list, in 8 sections.
Read `AIOS/me.md` first and check whether any sections already have answers
(**resume, don't restart** — re-asking answered questions is the fastest way
to lose someone's patience).

**Two modes — check which one you're in.** `AIOS/setup-questions.md` has a
`→` line under every question:

- **Some or all already filled in** → they typed answers themselves. Process
  what's there, write it to the vault, and don't re-ask it conversationally.
  Then offer to interview them on only the remaining blanks.
- **All blank, and they haven't said "process my answers"** → interview mode:
  start now, don't wait for a second message asking you to.
- **They said "process my setup answers"** → read the file, write everything
  to the vault, report what landed where and which sections are still blank.

**Run it now, starting with Section 1, without waiting for a separate
go-ahead** — "set yourself up" already was the go-ahead. Ask Section 1's
questions conversationally, a few at a time, in your own words — not as a
read-aloud numbered list, people answer lists in monosyllables. Use
multiple-choice where a genuine option set helps (Section 6 especially).
**Write the answers to the vault at the end of the section**, not at the end
of the whole interview — say what you wrote and where, in one line, then ask
if they want to keep going.

**Section 1 (10 questions) is the only mandatory one.** After it: *"That's
enough to use the vault. Sections 2–8 make it better — want to keep going, or
start using it?"*

Rules while interviewing, same as any session in this vault:

- **"I don't know" is a real answer** — write it down as undecided, never
  substitute a guess.
- **Don't interpret upward.** Their words, their calibration.
- **Follow the thread** — a good interview isn't a rigid form.
- **Capture things mentioned in passing**, not just direct answers.
- **Never write to `Privat/`.**
- **Never claim a write before it succeeded** — write, confirm, then say so,
  naming the file.
- **Every note the routing table sends to `Atlas/About Me/` (or anywhere else
  with a folder index) follows `vault-librarian`'s note-creation rules, not
  just the routing table's destination path** — that means a row in the
  folder's index note (`Atlas/About Me/About Me.md` etc.) and a link up to
  it, same as any other note in the vault. A note that exists but isn't in
  its index is only findable by luck; don't leave one behind mid-interview.

Where answers go: follow the routing table at the bottom of
`AIOS/setup-questions.md`. In short — `AIOS/me.md` gets the short summary
(replace the `<< >>` placeholders for whichever sections you just answered;
keep it short since it's loaded every session), `Atlas/About Me/` gets one
note per subject, `Efforts/` gets one note per project. **Only delete the
TEMPLATE warning box once every placeholder in the file is gone** — after
Section 1 alone, most of `me.md` (devices, skills, projects, behavior rules)
is still template text, and the box exists precisely to stop a session
mistaking a placeholder for a real answer. Leave it in and say plainly that
Section 1 is done but the file isn't fully real yet. Log every write with
`AIOS/scripts/logchange.py`, same as any other write to this vault.

## §4. Self-check — always run this, always report it straight

```bash
python3 AIOS/scripts/setup-check.py
```

This prints a table: what's actually confirmed working, what's a WARN (often
normal on a brand-new vault — read the detail), and what's an actual FAIL.
**Show the user this table, or a faithful summary of it — don't just say
"all done."** This is the mechanism that replaces "trust me, it worked" with
something checkable, which is the whole point of this step existing.

If anything is a genuine FAIL, say so plainly and either fix it or tell them
exactly what to do. If chat backup shows no source found, that's often
correct — you may be running from inside this same conversation, which isn't
the machine Claude's desktop app is installed on. Say that rather than
treating it as mysterious.

## §5. Explain how it actually works — briefly, in plain language

Close with a short, plain-language explanation, not a wall of docs — most of
this is one sentence each:

- **The vault is the memory, not the AI.** These are plain text files. Any AI
  that can read this folder starts a session already knowing the user,
  because it reads `AIOS/me.md` and the relevant notes first, every time.
- **Chats save themselves**, if the scheduler installed — a script runs
  automatically and copies conversations into `AIOS/history/chat-history/cowork/` as
  readable Markdown. Point them at that folder.
- **Skills are just instructions** — markdown files that make the AI behave a
  particular way automatically (writing facts down without being asked,
  answering from their notes instead of guessing, and so on). Say which ones
  ended up active and how, from §2.
- **In Obsidian**, open this folder as a vault and start at `Home.md`. They
  never need to open `AIOS/` by hand — that's instructions for the AI, not
  for them.
- Point them at `AIOS/how-to-use-this.md` for the full guide, and mention
  they can re-run `python3 AIOS/scripts/setup-check.py` any time they want to
  confirm things are still working — for instance a day or two from now, to
  make sure a scheduled job survived.

## When it's done

1. Tell them, in one short list: what got created, which interview sections
   they skipped (and that those are available any time), and to delete
   `AIOS/setup-questions.md`, `README-START-HERE.md`, the four `EXAMPLE `
   notes, and this skill's folder once they're confident everything landed.
2. Offer to set up a scheduled morning brief if `daily-brief` is active.

## Never

- Wait for a second message before starting §1–§4 — "set yourself up" already
  authorizes the whole flow through the self-check.
- Ask all 50 interview questions in one message.
- Re-ask something already answered in the vault **or already typed into a
  `→` line**.
- Claim a skill is "installed" when what actually happened is you read its
  file and are following it for this session — say which one happened.
- Claim automation is working without having just run `setup-check.py` and
  read its actual output.
- Guess an interview answer they didn't give.
- Read or write anything under `Privat/`.
