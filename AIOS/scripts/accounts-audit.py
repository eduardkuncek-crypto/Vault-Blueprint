#!/usr/bin/env python3
"""
accounts-audit.py — the mechanical half of keeping `Atlas/Reference/My online
accounts.md` honest: age-check the "Needs action" table, add rows to either
table without hand-editing markdown.

HONEST LIMIT: this script cannot search your inbox itself — it has no
network access and no dependencies by design (same rule as every script in
this folder). Finding NEW signups is still an agent's job: re-run whatever
search the note was originally built from (e.g. a mail search for account
creation notices), then feed what it finds to --add / --add-active. What
this script actually automates: computing how overdue an unverified account
is (a plain date subtraction nobody was doing), and doing the table edit
safely instead of by hand.

Usage:
    python3 AIOS/scripts/accounts-audit.py --check
        # ages every "Needs action" row against today, flags anything
        # unverified for more than 14 days (--days to change the bar)

    python3 AIOS/scripts/accounts-audit.py --add "Some VPN" \
        --since 2026-07-20 --status "Email never verified"
        # append to the Needs action table

    python3 AIOS/scripts/accounts-audit.py --add-active "Some Service" \
        --since 2026-07-19
        # append to the Signed up, in use table

No dependencies. Plain stdlib.
"""
import scriptlog  # noqa: F401

# aios-run: agent  (re-checking account state, or a fresh signup pass)

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P  # noqa: E402
from notelock import locked, write_atomic  # noqa: E402

NOTE = P.ATLAS_REFERENCE / "My online accounts.md"
NEEDS_ACTION_HEADING = "## Needs action"
NEEDS_ACTION_COLS = "| Account | State | Since |"
ACTIVE_HEADING = "## Signed up, in use"
ACTIVE_COLS = "| Account | Since |"


def fail(msg: str) -> None:
    print(f"accounts-audit: ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def safe_cell(text):
    if text is None:
        return ""
    return " ".join(str(text).replace("\r", "\n").split("\n")).replace("|", "¦").strip()


def table_bounds(lines, heading, header_prefix):
    hit = next((i for i, l in enumerate(lines) if l.strip() == heading), None)
    if hit is None:
        return None, None
    header_idx = next((i for i in range(hit, len(lines)) if lines[i].startswith(header_prefix)), None)
    if header_idx is None:
        return None, None
    last = header_idx + 1
    i = last + 1
    while i < len(lines) and lines[i].startswith("|"):
        last = i
        i += 1
    return header_idx, last


def as_date(s):
    try:
        return dt.date.fromisoformat(str(s).strip().replace("**", ""))
    except (ValueError, TypeError):
        return None


def cmd_check(days_threshold: int) -> int:
    if not NOTE.exists():
        fail(f"{NOTE} does not exist")
    lines = NOTE.read_text(encoding="utf-8").split("\n")
    header_idx, last_row_idx = table_bounds(lines, NEEDS_ACTION_HEADING, "| Account")
    if header_idx is None:
        print("accounts-audit: no 'Needs action' table found.")
        return 0
    today = dt.date.today()
    rows = []
    for i in range(header_idx + 2, last_row_idx + 1):
        cells = [c.strip() for c in lines[i].split("|")]
        if len(cells) < 5:
            continue
        rows.append((cells[1], cells[2], cells[3]))
    if not rows:
        print("accounts-audit: nothing in 'Needs action'.")
        return 0
    overdue = 0
    for account, state, since_raw in rows:
        since = as_date(since_raw)
        if since is None:
            print(f"  {account:<24} {state:<40} since {since_raw!r} — unparseable date")
            continue
        age = (today - since).days
        flag = " !! OVERDUE" if age >= days_threshold else ""
        if flag:
            overdue += 1
        print(f"  {account:<24} {state:<40} {age}d since {since}{flag}")
    print(f"accounts-audit: {len(rows)} open, {overdue} over {days_threshold}d unresolved")
    return 0


def cmd_add(args, active: bool) -> int:
    if args.since:
        since = as_date(args.since)
        if since is None:
            fail(f"--since must be YYYY-MM-DD, got {args.since!r}")
    else:
        since = dt.date.today()
    heading = ACTIVE_HEADING if active else NEEDS_ACTION_HEADING
    prefix = "| Account" if active else "| Account"
    row = (f"| **{safe_cell(args.account)}** | {since.isoformat()} |" if active else
           f"| **{safe_cell(args.account)}** | {safe_cell(args.status)} | {since.isoformat()} |")

    with locked(NOTE):
        if not NOTE.exists():
            fail(f"{NOTE} does not exist")
        lines = NOTE.read_text(encoding="utf-8").split("\n")
        header_idx, last_row_idx = table_bounds(lines, heading, prefix)
        if header_idx is None:
            fail(f"no '{heading}' table found in {NOTE}")
        lines.insert(last_row_idx + 1, row)
        write_atomic(NOTE, "\n".join(lines))

    print(f"accounts-audit: added — {row}")
    rel = P.relative(NOTE)
    subprocess.run(
        [sys.executable or "python3", str(P.SCRIPTS / "logchange.py"),
         f"Account: {args.account} ({'active' if active else args.status})", rel],
        check=False)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="age every 'Needs action' row")
    ap.add_argument("--days", type=int, default=14, help="overdue threshold in days (default 14)")
    ap.add_argument("--add", metavar="ACCOUNT", help="add to 'Needs action'")
    ap.add_argument("--add-active", metavar="ACCOUNT", help="add to 'Signed up, in use'")
    ap.add_argument("--since", help="YYYY-MM-DD, defaults to today")
    ap.add_argument("--status", default="", help="e.g. 'Email never verified' (--add only)")
    args = ap.parse_args()

    if args.check:
        return cmd_check(args.days)
    if args.add:
        args.account = args.add
        return cmd_add(args, active=False)
    if args.add_active:
        args.account = args.add_active
        return cmd_add(args, active=True)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
