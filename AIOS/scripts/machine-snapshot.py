#!/usr/bin/env python3
"""
machine-snapshot.py — log a dated disk/RAM reading, so "is this machine
still almost full" is a trend instead of a single stale reading stuck in a
hardware-reference note forever.

THE GAP: a disk or RAM number that only ever gets pasted into a note once is
never re-taken and never comparable. This appends one row per reading to
`AIOS/history/machine-snapshots.md`. Free text on purpose: the input is
whatever gets pasted from `df -h` / `free -h` / `lsblk` (or the equivalent on
another OS), and normalizing that robustly isn't worth the fragility — a
human (or an agent reading the paste) picks the numbers that matter and hands
them here.

Usage:
    python3 AIOS/scripts/machine-snapshot.py --machine "laptop" \
        --disk "8 GB free / 92% full (/ nvme0n1p4)" \
        --ram "14Gi total, 9.4Gi used, 1.5Gi swap in use" \
        [--note "after a cleanup pass"] [--date 2026-09-05]

    python3 AIOS/scripts/machine-snapshot.py --history [--machine laptop] [--last 10]

`--machine` is a free-text label, not a lookup against any device registry —
this vault design has no notion of "known machines" beyond whatever label you
give a snapshot. If you only ever run this from one machine, omit it and
every row is just labeled "this machine".

No dependencies. Plain stdlib.
"""
import scriptlog  # noqa: F401

# aios-run: agent  (any df/free/lsblk numbers that get pasted or reported)

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P  # noqa: E402
from notelock import locked, write_atomic  # noqa: E402

NOTE = P.HISTORY / "machine-snapshots.md"
HEADING = "## Snapshots"
HEADER_TEXT = (
    "---\ntitle: Machine snapshots\ntags:\n  - generated\n  - hardware\n---\n\n"
    "# Machine snapshots\n\n"
    "> [!info] One row per disk/RAM reading, dated\n"
    "> Written by `AIOS/scripts/machine-snapshot.py`. Current specs still live "
    "wherever you keep a hardware-reference note (e.g. `Atlas/Reference/`) — "
    "this is the history a single reading doesn't keep, so a trend (disk "
    "filling up, RAM pressure) is visible instead of a single stale number.\n\n"
    f"{HEADING}\n\n"
    "| Date | Machine | Disk | RAM | Note |\n"
    "|---|---|---|---|---|\n"
)

DEFAULT_MACHINE = "this machine"


def fail(msg: str) -> None:
    print(f"machine-snapshot: ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def safe_cell(text):
    if text is None:
        return ""
    return " ".join(str(text).replace("\r", "\n").split("\n")).replace("|", "¦").strip()


def table_bounds(lines):
    hit = next((i for i, l in enumerate(lines) if l.strip() == HEADING), None)
    if hit is None:
        return None, None
    header_idx = next((i for i in range(hit, len(lines)) if lines[i].startswith("| Date")), None)
    if header_idx is None:
        return None, None
    last = header_idx + 1
    i = last + 1
    while i < len(lines) and lines[i].startswith("|"):
        last = i
        i += 1
    return header_idx, last


def cmd_add(args) -> int:
    if not args.disk and not args.ram:
        fail("give at least one of --disk / --ram — nothing to record otherwise")
    machine = args.machine or DEFAULT_MACHINE
    date_str = args.date or dt.date.today().isoformat()
    try:
        dt.date.fromisoformat(date_str)
    except ValueError:
        fail(f"--date must be YYYY-MM-DD, got {date_str!r}")

    row = (f"| {date_str} | {safe_cell(machine)} | {safe_cell(args.disk) or '—'} | "
           f"{safe_cell(args.ram) or '—'} | {safe_cell(args.note)} |")

    with locked(NOTE):
        if not NOTE.exists():
            NOTE.parent.mkdir(parents=True, exist_ok=True)
            write_atomic(NOTE, HEADER_TEXT)
        lines = NOTE.read_text(encoding="utf-8").split("\n")
        header_idx, last_row_idx = table_bounds(lines)
        if header_idx is None:
            fail(f"no '{HEADING}' table found in {NOTE} — file may be corrupted")
        lines.insert(last_row_idx + 1, row)
        write_atomic(NOTE, "\n".join(lines))

    print(f"machine-snapshot: logged — {row}")
    rel = P.relative(NOTE)
    subprocess.run(
        [sys.executable or "python3", str(P.SCRIPTS / "logchange.py"),
         f"Machine snapshot ({machine}): {args.disk or ''} {args.ram or ''}".strip(), rel],
        check=False)
    return 0


def cmd_history(machine, last: int) -> int:
    if not NOTE.exists():
        print("machine-snapshot: no snapshots yet.")
        return 0
    lines = NOTE.read_text(encoding="utf-8").split("\n")
    header_idx, last_row_idx = table_bounds(lines)
    if header_idx is None:
        print("machine-snapshot: no snapshots yet.")
        return 0
    rows = []
    for i in range(header_idx + 2, last_row_idx + 1):
        cells = [c.strip() for c in lines[i].split("|")]
        if len(cells) < 6:
            continue
        if machine and cells[2].lower() != machine.lower():
            continue
        rows.append(cells[1:5])
    if not rows:
        print("machine-snapshot: no matching snapshots.")
        return 0
    for date, mach, disk, ram in rows[-last:]:
        print(f"{date}  {mach:<8} disk: {disk:<40} ram: {ram}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", help=f"free-text label, defaults to {DEFAULT_MACHINE!r}")
    ap.add_argument("--disk", help="free text, e.g. '8 GB free / 92%% full'")
    ap.add_argument("--ram", help="free text, e.g. '9.4Gi used / 14Gi, 1.5Gi swap'")
    ap.add_argument("--note", default="")
    ap.add_argument("--date", help="YYYY-MM-DD, defaults to today")
    ap.add_argument("--history", action="store_true")
    ap.add_argument("--last", type=int, default=10)
    args = ap.parse_args()

    if args.history:
        return cmd_history(args.machine, args.last)
    if args.disk or args.ram:
        return cmd_add(args)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
