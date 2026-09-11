#!/usr/bin/env python3
"""
screentime.py — one command to log a day's screen time and sleep, so "is it
actually going down" is a number instead of a feeling.

THE GAP: a screen-time or sleep number that only ever gets said out loud, with
no date attached and no history, can't answer "is this actually changing."
This appends one row per day and can print a rolling average.

Usage:
    python3 AIOS/scripts/screentime.py --hours 6.5 [--sleep 7] \
        [--date 2026-09-05] [--note "mostly gaming"]

    python3 AIOS/scripts/screentime.py --list [--last 14]
    python3 AIOS/scripts/screentime.py --avg [--last 14]   # rolling average

Judgement doesn't belong in this script's output — it only tracks the
number, it doesn't editorialize. A trend line is more useful than a lecture,
and it's also all this script is equipped to produce.

No dependencies. Plain stdlib.
"""
import scriptlog  # noqa: F401

# aios-run: agent  (any time a screen-time or sleep number comes up)

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P  # noqa: E402
from notelock import locked, write_atomic  # noqa: E402

NOTE = P.ABOUT_ME / "Screen time.md"
HEADING = "## Log"
INTRO = (
    "%% Append-only, via `AIOS/scripts/screentime.py`. One row per day you "
    "state a number for — not a nag, just the data. %%"
)
COLS = "| Date | Screen hrs | Sleep hrs | Note |"
SEP = "|---|---|---|---|"


def fail(msg: str) -> None:
    print(f"screentime: ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def safe_cell(text: str) -> str:
    if text is None:
        return ""
    return " ".join(str(text).replace("\r", "\n").split("\n")).replace("|", "¦").strip()


def ensure_section(lines) -> int:
    for i, l in enumerate(lines):
        if l.strip() == HEADING:
            return i
    rel = next((i for i, l in enumerate(lines) if l.strip() == "## Related"), len(lines))
    block = ["", HEADING, "", INTRO, "", COLS, SEP, ""]
    lines[rel:rel] = block
    return rel + 1


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
    if args.date:
        try:
            date_str = dt.date.fromisoformat(args.date).isoformat()
        except ValueError:
            fail(f"--date must be YYYY-MM-DD, got {args.date!r}")
    else:
        date_str = dt.date.today().isoformat()

    sleep_cell = f"{args.sleep:g}" if args.sleep is not None else ""
    row = f"| {date_str} | **{args.hours:g}h** | {sleep_cell} | {safe_cell(args.note)} |"

    with locked(NOTE):
        if not NOTE.exists():
            fail(f"{NOTE} does not exist")
        lines = NOTE.read_text(encoding="utf-8").split("\n")
        ensure_section(lines)
        header_idx, last_row_idx = table_bounds(lines)
        lines.insert(last_row_idx + 1, row)
        write_atomic(NOTE, "\n".join(lines))

    print(f"screentime: logged — {row}")
    rel = P.relative(NOTE)
    what = f"Screen time: {args.hours:g}h" + (f", sleep {args.sleep:g}h" if args.sleep is not None else "")
    subprocess.run([sys.executable or "python3", str(P.SCRIPTS / "logchange.py"), what, rel],
                    check=False)
    return 0


def load_rows():
    if not NOTE.exists():
        fail(f"{NOTE} does not exist")
    lines = NOTE.read_text(encoding="utf-8").split("\n")
    header_idx, last_row_idx = table_bounds(lines)
    if header_idx is None:
        return []
    out = []
    for i in range(header_idx + 2, last_row_idx + 1):
        cells = [c.strip() for c in lines[i].split("|")]
        if len(cells) < 5:
            continue
        m = re.search(r"[\d.]+", cells[2])
        if not m:
            continue
        sleep_m = re.search(r"[\d.]+", cells[3])
        out.append({"date": cells[1], "hours": float(m.group(0)),
                     "sleep": float(sleep_m.group(0)) if sleep_m else None,
                     "note": cells[4]})
    return out


def cmd_list(last: int) -> int:
    rows = load_rows()[-last:]
    if not rows:
        print("screentime: nothing logged yet.")
        return 0
    for r in rows:
        sleep = f"{r['sleep']:g}h sleep" if r["sleep"] is not None else "sleep ?"
        print(f"{r['date']}  {r['hours']:g}h screen  {sleep}  {r['note']}")
    return 0


def cmd_avg(last: int) -> int:
    rows = load_rows()[-last:]
    if not rows:
        print("screentime: nothing logged yet.")
        return 0
    avg_hours = sum(r["hours"] for r in rows) / len(rows)
    sleeps = [r["sleep"] for r in rows if r["sleep"] is not None]
    print(f"screentime: last {len(rows)} entries — avg screen {avg_hours:.1f}h/day"
          + (f", avg sleep {sum(sleeps)/len(sleeps):.1f}h/night" if sleeps else ""))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hours", type=float, help="screen hours today")
    ap.add_argument("--sleep", type=float, help="sleep hours last night")
    ap.add_argument("--date", help="YYYY-MM-DD, defaults to today")
    ap.add_argument("--note", default="", help="free text")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--avg", action="store_true", help="rolling average")
    ap.add_argument("--last", type=int, default=14)
    args = ap.parse_args()

    if args.list:
        return cmd_list(args.last)
    if args.avg:
        return cmd_avg(args.last)
    if args.hours is not None:
        return cmd_add(args)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
