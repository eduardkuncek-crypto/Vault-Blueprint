#!/usr/bin/env python3
"""
Regenerate Efforts/Next Actions.md — the one page that answers "what do I do now".

Reads, never invents:
  - every project note's `## Next action` section  (source of truth stays in the note)
  - every open `- [ ]` checkbox anywhere outside Privat/

Run:  python3 AIOS/scripts/next-actions.py
Safe to run any time. It only ever overwrites Efforts/Next Actions.md.
Never reads Privat/.
"""
import os
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
VAULT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(VAULT, "Efforts", "Next Actions.md")

SKIP_DIRS = {"Privat", ".git", ".obsidian", ".trash", ".claude"}
SKIP_PATHS = {os.path.join("AIOS", "skills"), os.path.join("AIOS", "history"),
              os.path.join("AIOS", "templates")}

STATUS_ORDER = ["active", "planned", "upcoming", "stalled", "parked", "done"]


def walk_md():
    for dp, dns, fns in os.walk(VAULT):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        rel = os.path.relpath(dp, VAULT)
        if any(rel == s or rel.startswith(s + os.sep) for s in SKIP_PATHS):
            continue
        for fn in sorted(fns):
            if fn.endswith(".md"):
                yield os.path.join(dp, fn)


def frontmatter(text, key):
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    m = re.search(rf"^{key}:\s*(.+)$", text[3:end], re.M)
    return m.group(1).strip().strip('"').strip("'") if m else None


def next_action(text):
    m = re.search(r"^##+[ \t]*Next action[ \t]*$\n+(.+?)(?=\n##|\Z)",
                  text, re.M | re.S)
    if not m:
        return None
    body = m.group(1).strip()
    body = re.sub(r"^>.*$", "", body, flags=re.M)          # drop callouts
    body = " ".join(body.split())
    return body or None


def main():
    projects, tasks, missing = [], [], []

    eff = os.path.join(VAULT, "Efforts")
    for fn in sorted(os.listdir(eff)):
        if not fn.endswith(".md") or fn in ("Efforts.md", "Next Actions.md"):
            continue
        text = open(os.path.join(eff, fn), encoding="utf-8").read()
        st = (frontmatter(text, "status") or "none").lower()
        na = next_action(text)
        if na is None:
            missing.append((fn[:-3], st))
        else:
            projects.append((fn[:-3], st, na))

    for p in walk_md():
        rel = os.path.relpath(p, VAULT)
        if rel.replace(os.sep, "/") == "Efforts/Next Actions.md":
            continue
        for i, line in enumerate(open(p, encoding="utf-8"), 1):
            m = re.match(r"^\s*- \[ \]\s+(.+?)\s*$", line)
            if m and m.group(1).strip():
                tasks.append((rel, i, m.group(1).strip()))

    def key(row):
        st = row[1]
        return (STATUS_ORDER.index(st) if st in STATUS_ORDER else 99, row[0])

    projects.sort(key=key)
    live = [r for r in projects if r[1] in ("active", "planned", "upcoming")]
    stalled = [r for r in projects if r[1] == "stalled"]
    rest = [r for r in projects if r not in live and r not in stalled]

    now = datetime.now(timezone.utc).astimezone()
    L = []
    L.append("---")
    L.append("title: Next Actions")
    L.append("tags:")
    L.append("  - index")
    L.append("  - generated")
    L.append(f"generated: {now.strftime('%Y-%m-%d %H:%M')}")
    L.append("---")
    L.append("")
    L.append("# Next Actions")
    L.append("")
    L.append("> [!warning] Generated file — do not edit by hand")
    L.append("> Regenerate with `python3 AIOS/scripts/next-actions.py`, or say"
             " **`next`**. Edits here are overwritten. The real text lives in"
             " each project note's `## Next action` section — change it there.")
    L.append("")
    L.append(f"Generated {now.strftime('%Y-%m-%d %H:%M %Z')} · "
             f"{len(live)} live · {len(tasks)} open checkboxes")
    L.append("")

    L.append("## Do these")
    L.append("")
    if live:
        L.append("| Project | Status | The one next action |")
        L.append("|---|---|---|")
        for name, st, na in live:
            L.append(f"| [[{name}]] | `{st}` | {na} |")
    else:
        L.append("_Nothing live._")
    L.append("")

    if stalled:
        L.append("## Stalled — has a next action, nothing is happening")
        L.append("")
        L.append("| Project | The one next action |")
        L.append("|---|---|")
        for name, st, na in stalled:
            L.append(f"| [[{name}]] | {na} |")
        L.append("")

    L.append("## Open checkboxes")
    L.append("")
    if tasks:
        L.append("| Task | Where |")
        L.append("|---|---|")
        for rel, ln, txt in tasks:
            note = os.path.basename(rel)[:-3]
            L.append(f"| {txt} | [[{note}]] |")
    else:
        L.append("_None._")
    L.append("")

    if rest:
        L.append("## Not live (parked, done)")
        L.append("")
        L.append("| Project | Status | Next action if it restarts |")
        L.append("|---|---|---|")
        for name, st, na in rest:
            L.append(f"| [[{name}]] | `{st}` | {na} |")
        L.append("")

    if missing:
        L.append("## Missing a `## Next action` section")
        L.append("")
        L.append("These project notes break the convention in [[Efforts]] — "
                 "every project note ends with exactly one next action.")
        L.append("")
        for name, st in missing:
            L.append(f"- [[{name}]] — `{st}`")
        L.append("")

    L.append("## Related")
    L.append("")
    L.append("- [[Efforts]] — the projects themselves")
    L.append("- [[Efforts.base]] — live status table")
    L.append("- [[Home]]")
    L.append("")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"wrote {OUT}")
    print(f"  {len(live)} live projects, {len(rest)} not live, "
          f"{len(tasks)} open checkboxes, {len(missing)} missing next action")
    return 0


if __name__ == "__main__":
    sys.exit(main())
