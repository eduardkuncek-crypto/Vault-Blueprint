#!/usr/bin/env python3
"""
weekly-digest.py — pull one week's raw material for a weekly-review pass,
so the agent reads one digest instead of opening up to 7 daily notes by hand.

For every Calendar/Daily/YYYY-MM-DD.md in the target ISO week, this reads
the `## Changes` lines (written mechanically by logchange.py — the receipt
of every vault write) and every `- [ ]` / `- [x]` checkbox in the file, and
prints a compact digest: what changed, which files/projects got touched and
how often, and which checkboxes are open vs closed.

This does NOT write the weekly review itself — "what to drop", "what
actually matters" is still judgement, not a mechanical fact. It just
removes the file reads that judgement doesn't need.

Usage:
    python3 AIOS/scripts/weekly-digest.py                  # current ISO week
    python3 AIOS/scripts/weekly-digest.py --week 2026-W32
    python3 AIOS/scripts/weekly-digest.py --write           # also append the
                                                              # digest into
                                                              # Calendar/Weekly/
                                                              # YYYY-Wnn.md
                                                              # under
                                                              # "## Raw digest"

--write only ever appends a "## Raw digest" section (creating the file from
the template if it doesn't exist yet). It never touches the hand-written
sections above it (Finished / Said I'd do, didn't / etc).

No dependencies. Plain stdlib. Never reads Privat/.
"""
import argparse
import datetime as dt
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VAULT = os.path.abspath(os.path.join(HERE, "..", ".."))
DAILY_DIR = os.path.join(VAULT, "Calendar", "Daily")
WEEKLY_DIR = os.path.join(VAULT, "Calendar", "Weekly")
TEMPLATE = os.path.join(VAULT, "AIOS", "templates", "weekly-review.md")

CHANGE_RE = re.compile(
    r"^- \*\*(\d{2}:\d{2})\*\* — (?:_(\w+)_ )?(.+?)(?: → `(.+)`)?\s*$"
)
CHECKBOX_RE = re.compile(r"^\s*- \[( |x|X)\]\s+(.+?)\s*$")


def iso_week_range(week_str=None):
    """Return (monday_date, sunday_date, 'YYYY-Wnn') for the given or current week."""
    if week_str:
        m = re.match(r"^(\d{4})-W(\d{2})$", week_str.strip())
        if not m:
            raise ValueError(f"--week must look like 2026-W32, got {week_str!r}")
        year, week = int(m.group(1)), int(m.group(2))
    else:
        year, week, _ = dt.date.today().isocalendar()
    monday = dt.date.fromisocalendar(year, week, 1)
    sunday = dt.date.fromisocalendar(year, week, 7)
    label = f"{year}-W{week:02d}"
    return monday, sunday, label


def daily_notes_in_range(monday, sunday):
    d = monday
    while d <= sunday:
        p = os.path.join(DAILY_DIR, f"{d.isoformat()}.md")
        if os.path.isfile(p):
            yield d, p
        d += dt.timedelta(days=1)


def section(text, heading):
    m = re.search(rf"^##+[ \t]*{re.escape(heading)}[ \t]*$\n(.*?)(?=\n##+ |\Z)",
                  text, re.M | re.S)
    return m.group(1) if m else ""


def parse_day(path):
    text = open(path, encoding="utf-8", errors="replace").read()
    changes = []
    for line in section(text, "Changes").splitlines():
        m = CHANGE_RE.match(line.strip())
        if m:
            time_, kind, what, where = m.groups()
            changes.append({"time": time_, "kind": kind or "edit",
                             "what": what.strip(), "path": where})

    checkboxes = []
    for line in text.splitlines():
        m = CHECKBOX_RE.match(line)
        if m and m.group(2):
            checkboxes.append({"done": m.group(1).lower() == "x",
                                "text": m.group(2)})

    return changes, checkboxes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", metavar="YYYY-Wnn", default=None)
    ap.add_argument("--write", action="store_true",
                     help="append the digest into Calendar/Weekly/YYYY-Wnn.md")
    args = ap.parse_args()

    try:
        monday, sunday, label = iso_week_range(args.week)
    except ValueError as e:
        print(f"weekly-digest: {e}", file=sys.stderr)
        return 1

    all_changes = []
    all_checkboxes = []
    days_found = []
    for d, p in daily_notes_in_range(monday, sunday):
        changes, checkboxes = parse_day(p)
        days_found.append(d)
        for c in changes:
            c["date"] = d.isoformat()
            all_changes.append(c)
        for c in checkboxes:
            c["date"] = d.isoformat()
            all_checkboxes.append(c)

    touch_counts = {}
    for c in all_changes:
        if c["path"]:
            touch_counts[c["path"]] = touch_counts.get(c["path"], 0) + 1

    out = []
    out.append(f"Week {label} ({monday.isoformat()} to {sunday.isoformat()}) — "
               f"{len(days_found)}/7 days have a daily note, "
               f"{len(all_changes)} vault writes, "
               f"{sum(1 for c in all_checkboxes if c['done'])} checkbox(es) closed, "
               f"{sum(1 for c in all_checkboxes if not c['done'])} still open")
    out.append("")

    if not days_found:
        out.append("No daily notes exist for this week yet.")
    else:
        for d, p in daily_notes_in_range(monday, sunday):
            changes, checkboxes = parse_day(p)
            out.append(f"### {d.isoformat()} ({d.strftime('%A')})")
            if changes:
                for c in changes:
                    tail = f" → `{c['path']}`" if c["path"] else ""
                    out.append(f"  - **{c['time']}** [{c['kind']}] {c['what']}{tail}")
            else:
                out.append("  _(no logged changes)_")
            done = [c for c in checkboxes if c["done"]]
            open_ = [c for c in checkboxes if not c["done"]]
            if done:
                out.append(f"  closed: " + "; ".join(c["text"] for c in done))
            if open_:
                out.append(f"  open: " + "; ".join(c["text"] for c in open_))
            out.append("")

    if touch_counts:
        out.append("### Most-touched files")
        for path, n in sorted(touch_counts.items(), key=lambda kv: -kv[1])[:15]:
            out.append(f"  - {n}x  `{path}`")
        out.append("")

    digest = "\n".join(out)
    print(digest)

    if args.write:
        wpath = os.path.join(WEEKLY_DIR, f"{label}.md")
        if not os.path.isfile(wpath):
            if os.path.isfile(TEMPLATE):
                tpl = open(TEMPLATE, encoding="utf-8").read()
                tpl = tpl.replace("{{date:YYYY}}-W{{date:WW}}", label)
                tpl = tpl.replace("{{date:YYYY}}", str(monday.year))
                tpl = tpl.replace("{{date:WW}}", f"{monday.isocalendar()[1]:02d}")
                tpl = tpl.replace("{{date:YYYY-MM-DD}}", monday.isoformat())
                content = tpl
            else:
                content = f"# Week {label}\n"
            os.makedirs(os.path.dirname(wpath), exist_ok=True)
            with open(wpath, "w", encoding="utf-8") as f:
                f.write(content)

        existing = open(wpath, encoding="utf-8").read()
        if "## Raw digest" in existing:
            print(f"weekly-digest: {os.path.relpath(wpath, VAULT)} already has "
                  f"a '## Raw digest' section — not appending a second one.",
                  file=sys.stderr)
            return 1

        with open(wpath, "a", encoding="utf-8") as f:
            f.write("\n## Raw digest\n\n")
            f.write("%% Generated by weekly-digest.py — mechanical, not judgement. "
                    "The sections above are yours to write from this. %%\n\n")
            f.write(digest)
            f.write("\n")
        print(f"\nappended digest to {os.path.relpath(wpath, VAULT)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
