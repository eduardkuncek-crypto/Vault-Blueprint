#!/usr/bin/env python3
"""
capture-heartbeat.py — catch a stretch of chat with nothing captured at all.

WHY THIS EXISTS
---------------
A `capture-audit` scheduled task (not this script — set that up separately,
see the `auto-capture` skill) does the real work: fresh-context, reads the
day's transcripts, understands what should have been saved, writes what was
missed. It needs an LLM for that — matching topics isn't pattern-matching,
and running a reasoning pass every few minutes is comparatively expensive.

This script is the cheap, mechanical half: no reasoning, just clocks. It
can't tell you WHAT got missed — only THAT a stretch of chat activity
produced zero `## Changes` receipts, which is the shape of a session where
auto-capture went quiet entirely rather than missing one fact among many.
Same division of labour as `changelog-check.py` (catches a file that changed
with no receipt) — this catches a chat that happened with no receipt, which
changelog-check structurally cannot see since no vault file has to change
for that failure.

MECHANISM
---------
1. `backup-cowork.py` mirrors live chats into
   `AIOS/history/chat-history/cowork/*.md`, on whatever schedule you gave
   it — so the newest mtime under there is the freshest available signal
   that a conversation happened, at most one backup cycle stale.
2. Compare that mtime's time-of-day to the clock time of the LAST line under
   today's `## Changes` (or "no lines at all" if the section is empty/missing).
3. If chat activity is more than THRESHOLD_MIN ahead of the last receipt —
   default 45, wider than backup-cowork's own lag so this doesn't just
   re-detect the sync delay — append one `_unlogged_` line, same weak-content
   pattern as changelog-check: it can't know what was said, only that nothing
   was written down while something was clearly happening.
4. A snapshot (`.capture-heartbeat-snapshot.json`, next to this script)
   records the newest chat mtime already flagged, so the same gap doesn't
   produce a new nag line every run until either a receipt lands or the
   chat mtime moves again.

HONEST LIMIT
------------
Granularity is capped by backup-cowork's own sync interval — this cannot see
activity more recently than the last backup. Tighten that schedule if this
needs to be more responsive; this script alone can't be. It also cannot
distinguish "nothing worth capturing happened" from "something did and got
missed" — that judgement is exactly what a capture-audit pass exists for.
This is a smoke detector, not the fire inspector.

USAGE
-----
    python3 AIOS/scripts/capture-heartbeat.py                 # run once, write if needed
    python3 AIOS/scripts/capture-heartbeat.py --check         # report only
    python3 AIOS/scripts/capture-heartbeat.py --install-schedule --every-min 30

Exit codes: 0 nothing to flag · 1 a gap was flagged (or would be, under
--check) · 2 couldn't run (e.g. --install-schedule from inside a cloud
sandbox rather than your own computer).

No dependencies. Plain stdlib.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VAULT = HERE.parent.parent
COWORK_ROOT = VAULT / "AIOS" / "history" / "chat-history" / "cowork"
SNAPSHOT = HERE / ".capture-heartbeat-snapshot.json"
THRESHOLD_MIN = 45

sys.path.insert(0, str(HERE))
import logchange  # noqa: E402 -- reused, not duplicated


def is_sandbox_guess() -> bool:
    """Best-effort, not authoritative — same heuristic setup-check.py uses.
    A path under /sessions/, /tmp/ or /var/ that isn't inside a real home
    directory is the strongest available signal that this is a disposable
    cloud container rather than someone's own computer."""
    p = str(VAULT)
    return "/sessions/" in p or p.startswith("/tmp/") or p.startswith("/var/")


def newest_chat_mtime(today: dt.date) -> dt.datetime | None:
    """Newest mtime among today's synced transcripts."""
    best: float | None = None
    if not COWORK_ROOT.is_dir():
        return None
    for p in COWORK_ROOT.rglob("*.md"):
        try:
            mtime = p.stat().st_mtime
        except OSError:
            continue
        stamp = dt.datetime.fromtimestamp(mtime)
        if stamp.date() != today:
            continue
        if best is None or mtime > best:
            best = mtime
    return dt.datetime.fromtimestamp(best) if best is not None else None


def last_change_time(now: dt.datetime) -> dt.datetime | None:
    """Clock time of the last `## Changes` line in today's note, or None if empty/missing."""
    note = logchange.today_note(now)
    if not note.exists():
        return None
    try:
        text = note.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    times = re.findall(r"^- \*\*(\d{2}):(\d{2})\*\*", text, flags=re.MULTILINE)
    if not times:
        return None
    hh, mm = times[-1]
    return now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)


def load_snapshot() -> dict:
    try:
        return json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_snapshot(snap: dict) -> None:
    SNAPSHOT.write_text(json.dumps(snap), encoding="utf-8")


def check(now: dt.datetime) -> tuple[bool, str]:
    """Returns (should_flag, message)."""
    chat_mtime = newest_chat_mtime(now.date())
    if chat_mtime is None:
        return False, "no synced chat activity today — nothing to check."

    snap = load_snapshot()
    already_flagged_ts = snap.get(str(now.date()))
    if already_flagged_ts and chat_mtime.timestamp() <= already_flagged_ts:
        return False, "already flagged this exact gap — waiting for either a receipt or newer chat activity."

    last_change = last_change_time(now)
    if last_change is None:
        gap_min = (now - chat_mtime).total_seconds() / 60
        if gap_min >= THRESHOLD_MIN:
            return True, (f"chat activity synced ({chat_mtime:%H:%M}) but today's "
                           f"`## Changes` has no entries at all — check what happened "
                           f"in the last sync and log it")
        return False, "chat activity recent, no receipts yet, but still inside the grace window."

    gap_min = (chat_mtime - last_change).total_seconds() / 60
    if gap_min >= THRESHOLD_MIN:
        return True, (f"chat activity synced ({chat_mtime:%H:%M}) {int(gap_min)} min "
                       f"after the last `## Changes` receipt ({last_change:%H:%M}) — "
                       f"check what happened since and log it")
    return False, f"last receipt {int(gap_min)} min behind latest sync — inside the grace window."


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="report only — don't write a catch line, don't save the snapshot")
    ap.add_argument("--install-schedule", "--install-cron", dest="install_schedule",
                    action="store_true")
    ap.add_argument("--uninstall-schedule", "--uninstall-cron",
                    dest="uninstall_schedule", action="store_true")
    ap.add_argument("--every-min", type=int, default=30, metavar="N",
                    help="minutes between checks")
    args = ap.parse_args()

    if args.install_schedule or args.uninstall_schedule:
        if is_sandbox_guess():
            print("Refusing: this looks like a cloud/sandboxed session, not "
                  "your own computer.")
            print("Run this on the machine that owns the vault.")
            return 2
        sys.path.insert(0, str(HERE))
        import scheduler  # noqa: E402
        if args.uninstall_schedule:
            ok, detail = scheduler.uninstall("capture-heartbeat")
            print(("Removed. " if ok else "Could not remove: ") + detail)
            return 0 if ok else 1
        ok, detail = scheduler.install("capture-heartbeat", Path(__file__),
                                       every_minutes=args.every_min)
        print(("Installed. " if ok else "Could NOT install automatically. ") + detail)
        return 0 if ok else 1

    now = dt.datetime.now()
    flag, msg = check(now)

    if not flag:
        print(f"capture-heartbeat: {msg}")
        return 0

    print(f"capture-heartbeat: {msg}")
    if args.check:
        print("capture-heartbeat: --check, nothing written.")
        return 1

    line = logchange.make_line(now, msg, None, "unlogged")
    note = logchange.append_lines([line], now)
    chat_mtime = newest_chat_mtime(now.date())
    snap = load_snapshot()
    snap[str(now.date())] = chat_mtime.timestamp() if chat_mtime else now.timestamp()
    save_snapshot(snap)
    print(f"capture-heartbeat: appended 1 catch line to {note.relative_to(VAULT)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
