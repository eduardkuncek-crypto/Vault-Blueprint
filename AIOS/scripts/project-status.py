#!/usr/bin/env python3
"""
project-status.py — the `project-status <project>` routine, mechanized.

Prints where a project stands, what's blocking it, and its next action —
without opening the full note. Reads frontmatter (status, started, confirmed),
the `## Status` section, and the `## Next action` section, plus how long since
the file was last touched.

Usage:
    python3 AIOS/scripts/project-status.py "Bike Purchase"
    python3 AIOS/scripts/project-status.py bike        # fuzzy match on filename

Exit 0 on a match, 1 if nothing matched (prints close matches instead).

No dependencies. Plain stdlib. Never reads Privat/.
"""
import argparse
import os
import re
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
VAULT = os.path.abspath(os.path.join(HERE, "..", ".."))
EFFORTS = os.path.join(VAULT, "Efforts")


def frontmatter(text, key):
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    m = re.search(rf"^{key}:\s*(.+)$", text[3:end], re.M)
    return m.group(1).strip().strip('"').strip("'") if m else None


def section(text, heading):
    m = re.search(rf"^##+[ \t]*{re.escape(heading)}[ \t]*$\n+(.+?)(?=\n##|\Z)",
                  text, re.M | re.S)
    if not m:
        return None
    body = m.group(1).strip()
    body = re.sub(r"^>\s?\[!\w+\][^\n]*\n?", "", body, flags=re.M)
    body = re.sub(r"^>\s?", "", body, flags=re.M)
    body = " ".join(body.split())
    return body or None


def days_since(date_str):
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d",):
        try:
            d = datetime.strptime(date_str[:10], fmt)
            return (datetime.now() - d).days
        except ValueError:
            continue
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project", help="project name or a fragment of it")
    args = ap.parse_args()

    candidates = [f for f in os.listdir(EFFORTS) if f.endswith(".md")
                  and f not in ("Efforts.md", "Next Actions.md")]

    exact = f"{args.project}.md"
    fn = None
    for f in candidates:
        if f.lower() == exact.lower():
            fn = f
            break

    if fn is None:
        nlow = args.project.lower()
        matches = [f for f in candidates if nlow in f.lower()]
        if len(matches) == 1:
            fn = matches[0]
        elif len(matches) > 1:
            print(f"project-status: '{args.project}' matches more than one project:")
            for m in sorted(matches):
                print(f"  - {m[:-3]}")
            return 1
        else:
            print(f"project-status: no project matches '{args.project}'.", file=sys.stderr)
            print("Available:", file=sys.stderr)
            for c in sorted(candidates):
                print(f"  - {c[:-3]}", file=sys.stderr)
            return 1

    path = os.path.join(EFFORTS, fn)
    text = open(path, encoding="utf-8", errors="replace").read()
    name = fn[:-3]

    status = frontmatter(text, "status") or "none"
    started = frontmatter(text, "started")
    confirmed = frontmatter(text, "confirmed")
    skill = frontmatter(text, "skill")

    mtime_days = int((datetime.now().timestamp() - os.path.getmtime(path)) / 86400)
    confirmed_days = days_since(confirmed)

    status_text = section(text, "Status") or section(text, "Status, honestly")
    next_action = section(text, "Next action")

    print(f"{name} — status: {status}" + (f" (started {started})" if started else ""))
    age_bits = [f"file touched {mtime_days}d ago"]
    if confirmed_days is not None:
        age_bits.append(f"confirmed {confirmed_days}d ago")
    print("  " + ", ".join(age_bits))
    if skill:
        print(f"  load the `{skill}` skill first")
    print()
    if status_text:
        print("Status:")
        print(f"  {status_text}")
        print()
    else:
        print("Status: _(no ## Status section)_")
        print()
    if next_action:
        print("Next action:")
        print(f"  {next_action}")
    else:
        print("Next action: _(no ## Next action section — breaks the one-next-action rule)_")

    return 0


if __name__ == "__main__":
    sys.exit(main())
