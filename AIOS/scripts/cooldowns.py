#!/usr/bin/env python3
"""
cooldowns.py — the `--today`/`--upcoming` half `Calendar/Cooldowns.md` never had.

`event.py` already answers "what's on today/soon" for events. Cooldowns.md
has the exact same table shape — one row per fixed waiting period, sorted
soonest-first — but nothing computed days-left or flagged one as unlocked. It
was hand-maintained: add a row, and hope someone re-reads the table on the
right day. This closes that gap, same way event.py closes it for events.

A "cooldown" here means any fixed waiting period with a known end date: a
username-change cooldown, a free trial, a return/refund window, a warranty,
a notice period, a bank hold — anything where the honest answer to "can I do
X yet" is a date comparison, not a guess.

Usage:
    # add a cooldown
    python3 AIOS/scripts/cooldowns.py "Domain rename" --unlocks 2026-09-06 \
        --detail "[[My online accounts]]" [--locked 2026-08-07]

    # what unlocked today, or already passed and nobody moved it
    python3 AIOS/scripts/cooldowns.py --check

    # unlocking within N days (default 7 — what a daily brief cares about)
    python3 AIOS/scripts/cooldowns.py --upcoming 14

    # every open cooldown
    python3 AIOS/scripts/cooldowns.py --list

    # move a row from Open -> Passed once you know what actually happened
    python3 AIOS/scripts/cooldowns.py --resolve "Domain" --outcome "Renamed to X"

No dependencies. Plain stdlib.
"""
import scriptlog  # noqa: F401 -- logs this run to AIOS/history/scripts/

# aios-run: agent  (any fixed waiting period, or checking what's unlocked)

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P  # noqa: E402
from notelock import locked, write_atomic  # noqa: E402

NOTE = P.COOLDOWNS
OPEN_HEADING = "## Open cooldowns"
PASSED_HEADING = "## Passed"
OPEN_COLS = "| Unlocks | What | Locked | Detail |"
PASSED_COLS = "| Unlocked | What | Outcome |"

PIPE_SUB = "¦"


def fail(msg: str) -> None:
    print(f"cooldowns: ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def safe_cell(text: str) -> str:
    if text is None:
        return ""
    flat = " ".join(str(text).replace("\r", "\n").split("\n"))
    return flat.replace("|", PIPE_SUB).strip()


def as_date(s):
    try:
        return dt.date.fromisoformat(str(s).strip())
    except (ValueError, TypeError):
        return None


def table_bounds(lines, heading, header_prefix):
    """(header_idx, last_row_idx) for the first markdown table under `heading`."""
    hit = next((i for i, l in enumerate(lines) if l.strip() == heading), None)
    if hit is None:
        return None, None
    header_idx = next(
        (i for i in range(hit, len(lines)) if lines[i].startswith(header_prefix)), None)
    if header_idx is None:
        return None, None
    last_row = header_idx + 1  # the |---| separator
    i = last_row + 1
    while i < len(lines) and lines[i].startswith("|"):
        last_row = i
        i += 1
    return header_idx, last_row


class Row:
    def __init__(self, unlocks, what, locked_date, detail):
        self.unlocks = unlocks
        self.what = what
        self.locked_date = locked_date
        self.detail = detail

    def render(self):
        return (f"| **{self.unlocks.isoformat()}** | {safe_cell(self.what)} | "
                f"{self.locked_date.isoformat() if self.locked_date else ''} | "
                f"{safe_cell(self.detail)} |")


def parse_open_rows(lines, header_idx, last_row_idx):
    rows = []
    for i in range(header_idx + 2, last_row_idx + 1):
        cells = [c.strip() for c in lines[i].split("|")]
        if len(cells) < 5:
            continue
        u = as_date(cells[1].replace("*", "").strip())
        if u is None:
            continue
        rows.append((i, Row(u, cells[2].replace("*", "").strip(),
                             as_date(cells[3]), cells[4])))
    return rows


def cmd_add(args) -> int:
    unlocks = as_date(args.unlocks)
    if not unlocks:
        fail("--unlocks must be YYYY-MM-DD")
    locked_date = as_date(args.locked) or dt.date.today()
    row = Row(unlocks, args.title, locked_date, args.detail or "")

    with locked(NOTE):
        if not NOTE.exists():
            fail(f"{NOTE} does not exist")
        text = NOTE.read_text(encoding="utf-8")
        lines = text.split("\n")
        header_idx, last_row_idx = table_bounds(lines, OPEN_HEADING, "| Unlocks")
        if header_idx is None:
            fail(f"no '{OPEN_HEADING}' table found in {NOTE}")

        # insert sorted soonest-first
        rows = parse_open_rows(lines, header_idx, last_row_idx)
        insert_at = last_row_idx + 1
        for idx, r in rows:
            if unlocks < r.unlocks:
                insert_at = idx
                break
        lines.insert(insert_at, row.render())
        write_atomic(NOTE, "\n".join(lines))

    print(f"cooldowns: added — {row.render()}")
    rel = P.relative(NOTE)
    subprocess.run(
        [sys.executable or "python3", str(P.SCRIPTS / "logchange.py"),
         f"Cooldown: {args.title} unlocks {unlocks.isoformat()}", rel],
        check=False)
    return 0


def cmd_resolve(args) -> int:
    with locked(NOTE):
        if not NOTE.exists():
            fail(f"{NOTE} does not exist")
        text = NOTE.read_text(encoding="utf-8")
        lines = text.split("\n")
        oh, ol = table_bounds(lines, OPEN_HEADING, "| Unlocks")
        if oh is None:
            fail(f"no '{OPEN_HEADING}' table found")
        rows = parse_open_rows(lines, oh, ol)
        hits = [(idx, r) for idx, r in rows if args.resolve.lower() in r.what.lower()]
        if not hits:
            fail(f"nothing open matches {args.resolve!r}")
        if len(hits) > 1:
            fail("matches more than one open cooldown — be more specific:\n  "
                 + "\n  ".join(r.what for _, r in hits))
        idx, r = hits[0]
        del lines[idx]

        ph, pl = table_bounds(lines, PASSED_HEADING, "| Unlocked")
        passed_row = f"| {dt.date.today().isoformat()} | {safe_cell(r.what)} | {safe_cell(args.outcome)} |"
        if ph is None:
            fail(f"no '{PASSED_HEADING}' table found — add one under {PASSED_HEADING}")
        lines.insert(pl + 1, passed_row)
        write_atomic(NOTE, "\n".join(lines))

    print(f"cooldowns: resolved — {r.what} -> {passed_row}")
    rel = P.relative(NOTE)
    subprocess.run(
        [sys.executable or "python3", str(P.SCRIPTS / "logchange.py"),
         f"Cooldown resolved: {r.what} — {args.outcome}", rel],
        check=False)
    return 0


def load_open():
    """Every open cooldown, sorted soonest-first regardless of the table's
    on-disk order. The table isn't guaranteed to stay strictly sorted by
    hand-editing alone, so every report function reads through this instead
    of trusting the file's order."""
    if not NOTE.exists():
        fail(f"{NOTE} does not exist")
    lines = NOTE.read_text(encoding="utf-8").split("\n")
    header_idx, last_row_idx = table_bounds(lines, OPEN_HEADING, "| Unlocks")
    if header_idx is None:
        return []
    rows = [r for _, r in parse_open_rows(lines, header_idx, last_row_idx)]
    return sorted(rows, key=lambda r: r.unlocks)


def cmd_report(mode: str, window: int) -> int:
    today = dt.date.today()
    rows = load_open()
    if mode == "check":
        due = [r for r in rows if r.unlocks <= today]
        if not due:
            print("cooldowns: nothing unlocked yet.")
            return 0
        for r in due:
            tag = "TODAY" if r.unlocks == today else f"{(today - r.unlocks).days}d ago — PASSED, never resolved"
            print(f"[{tag}] {r.what} — unlocked {r.unlocks} — {r.detail}")
        return 0
    if mode == "upcoming":
        edge = today + dt.timedelta(days=window)
        hits = [r for r in rows if today <= r.unlocks <= edge]
        if not hits:
            print(f"cooldowns: nothing unlocking in the next {window} days.")
            return 0
        for r in hits:
            days = (r.unlocks - today).days
            when = "today" if days == 0 else f"in {days} days"
            print(f"{r.unlocks}  {r.what:<40} {when:<12} {r.detail}")
        return 0
    # list
    if not rows:
        print("cooldowns: no open cooldowns.")
        return 0
    for r in rows:
        print(f"{r.unlocks}  {r.what:<40} locked {r.locked_date or '?'}  {r.detail}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("title", nargs="?", help="what's on cooldown")
    ap.add_argument("--unlocks", help="YYYY-MM-DD — when it opens")
    ap.add_argument("--locked", help="YYYY-MM-DD — when the wait started, defaults to today")
    ap.add_argument("--detail", help="wikilink or note where the full story lives")
    ap.add_argument("--check", action="store_true", help="what's unlocked today or overdue")
    ap.add_argument("--upcoming", type=int, nargs="?", const=7,
                    help="unlocking within N days (default 7)")
    ap.add_argument("--list", action="store_true", help="every open cooldown")
    ap.add_argument("--resolve", help="substring match — move this row to Passed")
    ap.add_argument("--outcome", default="", help="what actually happened, with --resolve")
    args = ap.parse_args()

    if args.resolve:
        return cmd_resolve(args)
    if args.check:
        return cmd_report("check", 0)
    if args.upcoming is not None:
        return cmd_report("upcoming", args.upcoming)
    if args.list:
        return cmd_report("list", 0)
    if args.title:
        return cmd_add(args)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
