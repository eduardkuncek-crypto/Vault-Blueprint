#!/usr/bin/env python3
"""
logchange.py — append a timestamped line to today's daily note under `## Changes`.

Every write an AI makes to this vault gets one line here, so you can open
today's daily note and see exactly what was changed, where, and when. The daily
note is the RECEIPT. The facts themselves still live in their own subject notes.

Usage:
    python3 AIOS/scripts/logchange.py "what changed" "path/to/note.md"
    python3 AIOS/scripts/logchange.py "what changed" "path/to/note.md" --kind new
    python3 AIOS/scripts/logchange.py "what changed"          # no file (rare)

    # several at once, one per line on stdin as:  what changed<TAB>path
    printf 'a\tx.md\nb\ty.md\n' | python3 AIOS/scripts/logchange.py --stdin

--kind is optional and defaults to "edit". Allowed: new, edit, append, skill,
script, template, map, delete.

Behaviour:
  - Creates today's daily note from AIOS/templates/daily-note.md if missing.
  - Creates the `## Changes` section if missing, placed after `## Log`.
  - APPEND ONLY. Never rewrites or reorders an existing line.
  - Paths are stored relative to the vault root and wrapped in backticks.
  - Exits non-zero and prints to stderr on any failure, so a caller can tell
    the difference between "logged" and "silently did nothing".

No dependencies. Plain stdlib. Added 2026-08-07.
"""

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

# Vault root = two levels up from this file (AIOS/scripts/logchange.py)
VAULT = Path(__file__).resolve().parent.parent.parent

DAILY_DIR = VAULT / "Calendar" / "Daily"
TEMPLATE = VAULT / "AIOS" / "templates" / "daily-note.md"

CHANGES_HEADING = "## Changes"
CHANGES_BLURB = (
    "%% Appended by `AIOS/scripts/logchange.py` every time anything in the vault "
    "is written. This is the receipt, not the content — the facts themselves live "
    "in their own notes. Never overwritten. %%"
)

KINDS = {
    "new": "new",
    "edit": "edit",
    "append": "append",
    "skill": "skill",
    "script": "script",
    "template": "template",
    "map": "map",
    "delete": "delete",
}


def fail(msg: str) -> None:
    print(f"logchange: ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def today_note(now: dt.datetime) -> Path:
    return DAILY_DIR / f"{now:%Y-%m-%d}.md"


def render_template(now: dt.datetime) -> str:
    """Fill the Obsidian template placeholders we can fill ourselves."""
    if TEMPLATE.exists():
        text = TEMPLATE.read_text(encoding="utf-8")
        text = text.replace("{{date:YYYY-MM-DD}}", f"{now:%Y-%m-%d}")
        # e.g. Friday, 7 August 2026
        long_date = f"{now:%A}, {now.day} {now:%B} {now:%Y}"
        text = text.replace("{{date:dddd, D MMMM YYYY}}", long_date)
        return text
    # Minimal fallback if the template is ever missing
    return (
        f"---\ntitle: \"{now:%Y-%m-%d}\"\ndate: {now:%Y-%m-%d}\ntags:\n  - daily\n---\n\n"
        f"# {now:%A}, {now.day} {now:%B} {now:%Y}\n\n## Brief\n\n---\n\n## Log\n\n---\n\n"
        "## Tomorrow\n\n- [ ]\n"
    )


def ensure_note(path: Path, now: dt.datetime) -> str:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_template(now), encoding="utf-8")
        print(f"logchange: created {path.relative_to(VAULT)}")
    return path.read_text(encoding="utf-8")


def ensure_changes_section(text: str) -> str:
    """Return text guaranteed to contain a `## Changes` section."""
    if re.search(r"^## Changes\s*$", text, flags=re.MULTILINE):
        return text

    block = f"\n{CHANGES_HEADING}\n\n{CHANGES_BLURB}\n"

    # Preferred position: immediately before the `---` that closes the Log
    # section, i.e. after Log and before Tomorrow.
    m = re.search(r"^## Log\s*$", text, flags=re.MULTILINE)
    if m:
        rest = text[m.end():]
        sep = re.search(r"^---\s*$", rest, flags=re.MULTILINE)
        if sep:
            cut = m.end() + sep.start()
            return text[:cut] + block.lstrip("\n") + "\n" + text[cut:]

    # Fallback: append at the end of the file.
    return text.rstrip("\n") + "\n\n---\n\n" + block.lstrip("\n")


def rel_path(raw: str) -> str:
    """Normalise a path to be vault-relative, without exploding on odd input."""
    p = Path(raw)
    try:
        if p.is_absolute():
            return str(p.resolve().relative_to(VAULT))
    except ValueError:
        return str(p)  # outside the vault; log it verbatim
    return str(p).lstrip("./")


def make_line(now: dt.datetime, what: str, where: str | None, kind: str) -> str:
    what = " ".join(what.split()).rstrip(".")
    if not what:
        fail("empty change description")
    stamp = f"{now:%H:%M}"
    tag = f" _{kind}_" if kind != "edit" else ""
    if where:
        return f"- **{stamp}** —{tag} {what} → `{rel_path(where)}`"
    return f"- **{stamp}** —{tag} {what}"


def append_lines(lines: list[str], now: dt.datetime) -> Path:
    note = today_note(now)
    text = ensure_note(note, now)
    text = ensure_changes_section(text)

    m = re.search(r"^## Changes\s*$", text, flags=re.MULTILINE)
    if not m:
        fail("could not find or create the ## Changes section")

    # Find the end of this section: the next `## ` heading, `---`, or EOF.
    rest = text[m.end():]
    nxt = re.search(r"^(## |---\s*$)", rest, flags=re.MULTILINE)
    end = m.end() + (nxt.start() if nxt else len(rest))

    body = text[m.end():end].rstrip("\n")

    # CommonMark needs a blank line before a list starts. If the section so far
    # ends with prose (the blurb) rather than an existing bullet, add one.
    last = body.splitlines()[-1].strip() if body.strip() else ""
    gap = "\n" if last.startswith("- ") else "\n\n"

    body += gap + "\n".join(lines)
    new_text = text[:m.end()] + body + "\n\n" + text[end:]

    note.write_text(new_text, encoding="utf-8")
    return note


def main() -> None:
    ap = argparse.ArgumentParser(add_help=True, description=__doc__)
    ap.add_argument("what", nargs="?", help="what changed, in plain words")
    ap.add_argument("where", nargs="?", help="the file that changed")
    ap.add_argument("--kind", default="edit", choices=sorted(KINDS), help="type of change")
    ap.add_argument("--stdin", action="store_true", help="read 'what<TAB>where' lines from stdin")
    args = ap.parse_args()

    now = dt.datetime.now()
    lines: list[str] = []

    if args.stdin:
        for raw in sys.stdin.read().splitlines():
            if not raw.strip():
                continue
            parts = raw.split("\t")
            what = parts[0]
            where = parts[1] if len(parts) > 1 and parts[1].strip() else None
            kind = parts[2] if len(parts) > 2 and parts[2].strip() in KINDS else args.kind
            lines.append(make_line(now, what, where, kind))
    else:
        if not args.what:
            fail("nothing to log — pass a description, or use --stdin")
        lines.append(make_line(now, args.what, args.where, args.kind))

    if not lines:
        fail("nothing to log")

    note = append_lines(lines, now)
    for line in lines:
        print(f"logchange: {line}")
    print(f"logchange: written to {note.relative_to(VAULT)}")


if __name__ == "__main__":
    main()
