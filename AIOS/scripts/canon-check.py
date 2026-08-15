#!/usr/bin/env python3
"""
canon-check — find every place in the vault that still says the old thing.

THE PROBLEM THIS EXISTS FOR
---------------------------
A fact gets corrected in one note. The other notes that repeat it are never
touched. Weeks later a session opens one of those, believes it, and acts on
it. `vault-check.py` cannot catch this: every link works, every file is valid
Markdown, and the vault is confidently wrong.

Example: a project's status note says "using the old library" months after a
switch to a new one, because the switch was only ever written down in the
decision log of a different note.

HOW IT WORKS
------------
`AIOS/reference/canon.md` holds one row per fact that lives in more than one
place. Each row names the truth, the note that owns it, and the **old
wording** that must no longer appear anywhere else. This script reads that
table and greps the vault.

  python3 AIOS/scripts/canon-check.py

Reports only. It never edits a note. Exit code 1 if anything stale is found,
so a scheduled task or a shell `&&` can rely on it.

    --list      print the parsed table and stop (use this to check your syntax)
    --history   also scan Calendar/Daily and Calendar/Weekly (off by default:
                old daily notes are a historical record, not a claim about now)

ADDING A FACT
-------------
The moment you correct something that appears in more than one note, add a
row. That is the whole maintenance burden, and it is the point: correcting a
fact and registering it are the same action, so the next session inherits the
correction instead of the mistake.

Stale wordings are plain text, **semicolon-separated**, case-insensitive
substrings — not regexes. That is deliberate. A regex in a Markdown table gets
mangled by the pipe character and is one typo away from silently matching
nothing. Semicolons rather than commas because a stale wording is usually a
fragment of a real sentence, and real sentences contain commas.

No dependencies. Plain stdlib.
"""
import scriptlog  # noqa: F401 -- logs this run to AIOS/history/scripts/

# aios-run: manual  (run after correcting a repeated fact)
import os
import sys

VAULT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", ".."))
CANON = os.path.join(VAULT, "AIOS", "reference", "canon.md")

SKIP_DIRS = {
    "Privat",           # never read, never write
    ".git", ".obsidian", ".trash", "__pycache__",
}
SKIP_PATHS = {
    os.path.join("AIOS", "history"),   # generated chat logs + curated transcripts
    os.path.join("AIOS", "archive"),   # finished work, frozen on purpose
    os.path.join("AIOS", "skills"),    # mirror of the installed skills
    os.path.join("AIOS", "generated", "where.md"),  # if you use a generated index
}
HISTORY_PATHS = {
    os.path.join("Calendar", "Daily"),
    os.path.join("Calendar", "Weekly"),
}


def parse_canon():
    """Read AIOS/reference/canon.md and return a list of fact dicts.

    Only rows inside a Markdown table with the expected 7 columns are read;
    everything else in the file is prose and is ignored, so the table can be
    documented as heavily as it likes.
    """
    if not os.path.isfile(CANON):
        print(f"canon-check: no table at {CANON}")
        print("  Nothing to check yet. Create it when you have your first")
        print("  repeated fact to track, or run vault-check.py instead.")
        return [], [], []

    facts, problems, notes_only = [], [], []
    with open(CANON, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) != 7:
                continue
            if cells[0].lower() in ("#", "id"):
                continue
            if set(cells[0]) <= set("-: "):
                continue
            if not cells[0].isdigit():
                continue

            stale = [s.strip() for s in cells[4].split(";")
                     if s.strip() and s.strip() != "—"]
            allowed = [a.strip() for a in cells[5].split(";")
                       if a.strip() and a.strip() != "—"]
            if not stale:
                notes_only.append(f"  [{cells[0]}] {cells[1]} — recorded, "
                                  f"nothing to grep for")
                continue
            facts.append({
                "id": cells[0],
                "fact": cells[1],
                "truth": cells[2],
                "owner": cells[3],
                "stale": stale,
                "allowed": allowed + [cells[3]],
                "since": cells[6],
            })
    return facts, problems, notes_only


def vault_files(include_history):
    skip_paths = set(SKIP_PATHS)
    if not include_history:
        skip_paths |= HISTORY_PATHS

    for dirpath, dirnames, filenames in os.walk(VAULT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        rel_dir = os.path.relpath(dirpath, VAULT)
        if rel_dir == ".":
            rel_dir = ""
        if any(rel_dir == p or rel_dir.startswith(p + os.sep)
               for p in skip_paths):
            dirnames[:] = []
            continue
        for name in filenames:
            if not name.endswith(".md"):
                continue
            rel = os.path.join(rel_dir, name) if rel_dir else name
            if rel in skip_paths:
                continue
            if os.path.normpath(rel) == os.path.join("AIOS", "reference", "canon.md"):
                continue
            yield rel


def allowed_here(rel_path, allowed):
    name = os.path.basename(rel_path)[:-3]
    for entry in allowed:
        e = entry.strip().strip("[]").strip()
        if not e:
            continue
        if e.endswith(".md"):
            e = e[:-3]
        if e == name or e in rel_path:
            return True
    return False


def main():
    include_history = "--history" in sys.argv
    facts, problems, notes_only = parse_canon()

    print(f"canon-check — {VAULT}")
    print(f"  {len(facts)} checkable facts, {len(notes_only)} recorded only"
          f"{' (scanning history too)' if include_history else ''}")
    print()

    if not facts and not notes_only:
        return 0

    if "--list" in sys.argv:
        for f in facts:
            print(f"  [{f['id']}] {f['fact']}")
            print(f"       truth : {f['truth']}")
            print(f"       owner : {f['owner']}   since {f['since']}")
            print(f"       stale : {', '.join(f['stale'])}")
            print()
        for n in notes_only:
            print(n)
        for p in problems:
            print(p)
        return 0

    if problems:
        print("MALFORMED ROWS — these can never fire:")
        for p in problems:
            print(p)
        print()

    contents = {}
    for rel in vault_files(include_history):
        try:
            with open(os.path.join(VAULT, rel), encoding="utf-8") as fh:
                contents[rel] = fh.read().splitlines()
        except (OSError, UnicodeDecodeError):
            continue

    total = 0
    for f in facts:
        hits = []
        for rel, lines in contents.items():
            if allowed_here(rel, f["allowed"]):
                continue
            for n, line in enumerate(lines, 1):
                low = line.lower()
                for phrase in f["stale"]:
                    if phrase.lower() in low:
                        hits.append((rel, n, phrase, line.strip()))
                        break
        if hits:
            total += len(hits)
            print(f"[STALE] {f['fact']}")
            print(f"  truth: {f['truth']}  (owner: {f['owner']}, "
                  f"corrected {f['since']})")
            for rel, n, phrase, line in sorted(hits):
                snippet = line if len(line) <= 110 else line[:107] + "..."
                print(f"    {rel}:{n}  «{phrase}»")
                print(f"      {snippet}")
            print()

    if total or problems:
        print(f"{total} stale mention(s) across {len(facts)} facts. "
              f"Nothing was changed.")
        print("Fix each one in the note it appears in, then re-run. If a "
              "mention is legitimate")
        print("(a note explaining the correction), add that note to "
              "'Allowed in' in AIOS/reference/canon.md.")
        return 1

    print("CLEAN — every canonical fact says the same thing everywhere.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
