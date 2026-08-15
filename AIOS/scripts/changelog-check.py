#!/usr/bin/env python3
"""
changelog-check.py — catch a vault edit that never got a receipt in ## Changes.

WHY THIS EXISTS
---------------
`logchange.py` appends the `## Changes` receipt line — but only when
something remembers to call it. That's always been the AI's job to remember,
and "remember every time" is exactly the kind of rule that quietly stops
being followed. The honest fix isn't a stronger reminder, it's a script that
notices when a note's content moved and nobody said anything about it.

MECHANISM
---------
1. Snapshot every tracked note's mtime in `.changelog-snapshot.json` (next to
   this script, not a vault note).
2. Each run compares current mtimes to the snapshot.
3. A note whose mtime moved, and whose path does not appear anywhere in
   TODAY's daily note, gets one line appended to `## Changes`:

       - **14:32** — _unlogged_ `Efforts/Some Project.md` changed with no
         receipt today — check what happened and log it properly.

   That line is deliberately weak content (it can't know WHY) — it exists to
   turn a silent miss into something sitting where it will be seen.
4. The snapshot is rewritten either way, so nothing repeats tomorrow.

First run ever (no snapshot on disk) only builds the baseline. It cannot know
what changed before it existed, so it flags nothing rather than dumping every
note in the vault as "unlogged."

WHAT'S DELIBERATELY EXCLUDED
-----------------------------
Anything under `Privat/`, `.git/`, `.obsidian/`, `AIOS/skills/` (a mirror, not
notes), `AIOS/history/` (generated), and `AIOS/archive/` (frozen). `Calendar/`
is excluded too: checking whether a daily note logged itself is circular.

HONEST LIMIT
------------
Only checks TODAY's daily note. A note edited two days ago during a stretch
where this wasn't running yet, and logged then, will not be found
retroactively if the snapshot was never refreshed in between — it isn't a
historical search, it's a same-day net. Running it every 15–60 minutes keeps
that window small.

USAGE
-----
    python3 AIOS/scripts/changelog-check.py                # run once, write if needed
    python3 AIOS/scripts/changelog-check.py --check        # report only, write nothing
    python3 AIOS/scripts/changelog-check.py --install-schedule --every-min 30

Exit codes: 0 nothing unlogged · 1 something was flagged (or would be, under
--check) · 2 couldn't run.

No dependencies beyond this vault's own scripts. Plain stdlib.
"""
from __future__ import annotations
import scriptlog  # noqa: F401 -- logs this run to AIOS/history/scripts/

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VAULT = HERE.parent.parent
SNAPSHOT = HERE / ".changelog-snapshot.json"

sys.path.insert(0, str(HERE))
import logchange  # noqa: E402  (same directory, deliberately reused, not duplicated)

SKIP_DIRS = {"Privat", ".git", ".obsidian", ".trash", "__pycache__"}
SKIP_PATHS = {
    Path("AIOS") / "skills",
    Path("AIOS") / "history",
    Path("AIOS") / "archive",
}
SKIP_PREFIXES = ("Calendar/Daily", "Calendar/Weekly")


def tracked_notes() -> list[Path]:
    out = []
    for dp in VAULT.rglob("*.md"):
        rel = dp.relative_to(VAULT)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if any(str(rel).startswith(str(p)) for p in SKIP_PATHS):
            continue
        if str(rel).replace("\\", "/").startswith(SKIP_PREFIXES):
            continue
        out.append(dp)
    return out


def load_snapshot() -> dict:
    try:
        return json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_snapshot(snap: dict) -> None:
    SNAPSHOT.write_text(json.dumps(snap), encoding="utf-8")


def today_text(now: dt.datetime) -> str:
    note = logchange.today_note(now)
    if not note.exists():
        return ""
    try:
        return note.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def find_unlogged(now: dt.datetime) -> tuple[list[str], dict]:
    first_run = not SNAPSHOT.exists()
    old = load_snapshot()
    notes = tracked_notes()
    today = today_text(now)

    new_snap: dict = {}
    unlogged: list[str] = []
    for p in notes:
        r = str(p.relative_to(VAULT)).replace("\\", "/")
        try:
            mtime = p.stat().st_mtime
        except OSError:
            continue
        new_snap[r] = mtime
        if first_run:
            continue
        if old.get(r) == mtime:
            continue
        if f"`{r}`" in today:
            continue
        unlogged.append(r)

    return unlogged, new_snap


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="report only — don't write a catch line, don't save the snapshot")
    ap.add_argument("--install-schedule", "--install-cron", dest="install_schedule",
                    action="store_true")
    ap.add_argument("--every-min", type=int, default=30, metavar="N")
    args = ap.parse_args()

    if args.install_schedule:
        sys.path.insert(0, str(HERE))
        import scheduler  # noqa: E402
        ok, detail = scheduler.install("changelog-check", Path(__file__),
                                       every_minutes=args.every_min)
        print(("Installed. " if ok else "Could NOT install automatically. ") + detail)
        return 0 if ok else 1

    if not (VAULT / "AIOS").is_dir():
        print(f"{VAULT} is not the vault — no AIOS/ folder in it", file=sys.stderr)
        return 2

    now = dt.datetime.now()
    unlogged, new_snap = find_unlogged(now)

    if not unlogged:
        print("changelog-check: nothing unlogged.")
        if not args.check:
            save_snapshot(new_snap)
        return 0

    print(f"changelog-check: {len(unlogged)} note(s) changed with no receipt "
          f"in today's daily note:")
    for r in unlogged:
        print(f"  - {r}")

    if args.check:
        print("changelog-check: --check, nothing written.")
        return 1

    lines = [logchange.make_line(
        now, f"`{r}` changed with no receipt today — check what happened and "
             f"log it properly", None, "unlogged")
        for r in unlogged]
    note = logchange.append_lines(lines, now)
    save_snapshot(new_snap)
    print(f"changelog-check: appended {len(lines)} catch line(s) to "
          f"{note.relative_to(VAULT)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
