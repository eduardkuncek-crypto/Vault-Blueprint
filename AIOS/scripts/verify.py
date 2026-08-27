#!/usr/bin/env python3
"""
verify.py — snapshot the vault's files before a multi-file change, diff after.

Mechanizes the rule in AIOS/me.md: after a change touching more than a couple
of files, verify and show the numbers before being asked — what was touched,
what was deleted, whether anything lost content, whether Privat/ was touched.
"Did you break anything" deserves a real answer, not reassurance.

Usage:
    python3 AIOS/scripts/verify.py --snapshot     # before the change
    ... do the work ...
    python3 AIOS/scripts/verify.py --diff         # after — prints the numbers

What --diff reports:
  - files added / removed since the snapshot
  - files whose line count dropped more than 20% (possible content loss, not
    just a trim)
  - whether anything under Privat/ was touched at all (should never happen)

Snapshot lives in AIOS/scripts/.verify-snapshot.json — not a vault note,
never counted by vault-map.py, never a thing Obsidian shows.

No dependencies. Plain stdlib.
"""
import argparse
import json
import os
import sys
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent.parent
SNAPSHOT = Path(__file__).resolve().parent / ".verify-snapshot.json"
SKIP_DIRS = {".git", ".obsidian", ".trash", ".claude", "__pycache__"}
SKIP_FILES = {SNAPSHOT.resolve()}  # never let the snapshot detect its own file

SHRINK_THRESHOLD = 0.8  # flag a .md file if its line count drops below 80% of before


def scan() -> dict:
    files = {}
    for dirpath, dirnames, filenames in os.walk(VAULT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.resolve() in SKIP_FILES:
                continue
            rel = str(p.relative_to(VAULT))
            try:
                st = p.stat()
            except OSError:
                continue
            lines = None
            # Hard rule: never read anything under Privat/. Stat-only is enough here.
            if fn.endswith(".md") and not rel.startswith("Privat" + os.sep):
                try:
                    lines = sum(1 for _ in p.open("r", encoding="utf-8", errors="replace"))
                except OSError:
                    lines = None
            files[rel] = {"size": st.st_size, "lines": lines, "mtime": st.st_mtime}
    return files


def cmd_snapshot() -> None:
    files = scan()
    SNAPSHOT.write_text(json.dumps({"files": files}), encoding="utf-8")
    print(f"verify: snapshotted {len(files)} files → {SNAPSHOT.name}")


def cmd_diff() -> None:
    if not SNAPSHOT.exists():
        print("verify: no snapshot on disk — run --snapshot first", file=sys.stderr)
        sys.exit(1)

    before = json.loads(SNAPSHOT.read_text(encoding="utf-8"))["files"]
    after = scan()

    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(
        rel for rel in (set(before) & set(after))
        if before[rel]["mtime"] != after[rel]["mtime"]
    )
    shrunk = []
    for rel in changed:
        b, a = before[rel], after[rel]
        if b.get("lines") and a.get("lines") is not None and a["lines"] < b["lines"] * SHRINK_THRESHOLD:
            shrunk.append((rel, b["lines"], a["lines"]))

    privat_touched = sorted(p for p in (added + removed + changed) if p.startswith("Privat/"))

    print(f"verify: {len(added)} added, {len(removed)} removed, {len(changed)} changed "
          f"since the snapshot")

    if added:
        print("\n  added:")
        for p in added:
            print(f"    + {p}")
    if removed:
        print("\n  removed:")
        for p in removed:
            print(f"    - {p}")
    if changed and not shrunk:
        print("\n  changed (no content-loss flags):")
        for p in changed:
            print(f"    ~ {p}")
    if shrunk:
        print("\n  !! POSSIBLE CONTENT LOSS — line count dropped >20%:")
        for p, b, a in shrunk:
            print(f"    {p}: {b} → {a} lines")
    if privat_touched:
        print("\n  !! Privat/ was touched — this should never happen:")
        for p in privat_touched:
            print(f"    {p}")

    if not (added or removed or changed):
        print("  nothing changed since the snapshot")

    if shrunk or privat_touched:
        sys.exit(1)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--snapshot", action="store_true", help="save current state as the baseline")
    g.add_argument("--diff", action="store_true", help="compare current state to the last snapshot")
    args = ap.parse_args()

    if args.snapshot:
        cmd_snapshot()
    else:
        cmd_diff()


if __name__ == "__main__":
    main()
