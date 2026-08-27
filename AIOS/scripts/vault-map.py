#!/usr/bin/env python3
"""
vault-map.py — rebuild the generated Scale block inside AIOS/generated/scale.md.

Why this exists
---------------
A hand-typed note count in `vault-map.md` goes stale fast, and different
sessions can produce different numbers for the same vault depending on what
each one counted. A number a human has to retype is a number that will be
wrong.

So the count is generated and states its own rule. The *judgement* half of
`vault-map.md` — the folder map and the "where to look for what" table — is
still written by hand, because deciding where something belongs is not
something a script can do.

What counts as a note
----------------------
Every `.md` file, EXCEPT:
  * anything under `Privat/`                        — never read, never counted
  * anything under `AIOS/history/chat-history/cowork/` and `cowork-raw/`
                                                      — machine-written, overwritten every run
  * anything under `AIOS/skills/`                    — the skill mirror
  * anything under `.git/`, `.obsidian/`, `.trash/`, `.claude/`

This exclusion list deliberately matches `vault-check.py`'s SKIP_PATHS. If you
change the rule here, change it there in the same turn — a disagreement
between the two is exactly the bug this script exists to prevent.

The hand-written half still needs a human
------------------------------------------
The folder map and the "where to look for what" table are judgement, not
counting, so no script can refresh them. The generated block carries a
`map-reviewed` marker, and this script shouts once the vault has grown
REVIEW_EVERY notes past the last review. Stamp a review with `--reviewed`.

Usage
-----
    python3 AIOS/scripts/vault-map.py             # rewrite the block
    python3 AIOS/scripts/vault-map.py --check     # is it stale? changes nothing
    python3 AIOS/scripts/vault-map.py --reviewed  # "I just re-read the hand-written half"

Exit codes: 0 fine (or rewritten) · 1 stale (--check only) · 2 couldn't run.
A due review is reported loudly but never changes the exit code — it's a nudge
for a person, not a failure.

Called automatically by logchange.py whenever a write creates or deletes a
note, so it cannot drift. No dependencies. Plain stdlib.
"""
import argparse
import re
import sys
from datetime import date
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent.parent
MAP = VAULT / "AIOS" / "generated" / "scale.md"

BEGIN = "<!-- BEGIN GENERATED: scale -->"
END = "<!-- END GENERATED: scale -->"
REVIEW_RE = re.compile(r"<!-- map-reviewed: (\d{4}-\d{2}-\d{2}) @ (\d+) notes -->")

# How many notes may be added before the hand-written half of vault-map.md
# (folder map + "where to look for what") should be re-read by a person.
REVIEW_EVERY = 40

SKIP_PREFIXES = (
    "Privat/",
    "AIOS/history/chat-history/cowork/",
    "AIOS/history/chat-history/cowork-raw/",
    "AIOS/skills/",
    "AIOS/history/scripts/",
)
SKIP_DIR_NAMES = {".git", ".obsidian", ".trash", ".claude", "__pycache__"}

# Folders whose growth is worth a comment when it stops
WATCH_EMPTY = {
    "Atlas/Knowledge": "the `learn` routine has never produced a note",
    "Calendar/Weekly": "`weekly-review` has never run",
}

DEFAULT_BLOCK = f"""{BEGIN}

*(not yet built — run `python3 AIOS/scripts/vault-map.py`)*

{END}
"""


def notes() -> list[Path]:
    out = []
    for p in VAULT.rglob("*.md"):
        parts = p.relative_to(VAULT).parts
        if any(seg in SKIP_DIR_NAMES or seg.startswith(".") for seg in parts[:-1]):
            continue
        rel = "/".join(parts)
        if any(rel.startswith(pre) for pre in SKIP_PREFIXES):
            continue
        out.append(p)
    return out


def folder_of(p: Path) -> str:
    rel = p.relative_to(VAULT)
    return str(rel.parent) if str(rel.parent) != "." else "(vault root)"


def last_review(text: str, current: int) -> tuple[str, int]:
    m = REVIEW_RE.search(text)
    if m:
        return m.group(1), int(m.group(2))
    return f"{date.today():%Y-%m-%d}", current


def build(reviewed: tuple[str, int]) -> str:
    files = notes()
    counts: dict[str, int] = {}
    for f in files:
        counts[folder_of(f)] = counts.get(folder_of(f), 0) + 1

    rows = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))

    lines = [
        BEGIN,
        "",
        f"**{len(files)} notes**, counted {date.today():%Y-%m-%d} by "
        "`AIOS/scripts/vault-map.py`.",
        "",
        "| Folder | Notes |",
        "|---|---|",
    ]
    for name, n in rows:
        lines.append(f"| `{name}/` | {n} |" if name != "(vault root)"
                     else f"| vault root | {n} |")

    empties = [(f, why) for f, why in WATCH_EMPTY.items() if counts.get(f, 0) <= 1]
    if empties:
        lines += ["", "Worth staring at:", ""]
        for f, why in empties:
            lines.append(f"- **`{f}/` holds only its own index** — {why}.")

    lines += [
        "",
        "Excluded from the count: `Privat/` (never read), "
        "`AIOS/history/chat-history/cowork/` and `cowork-raw/` (machine-written "
        "transcripts, overwritten every run) and `AIOS/skills/` (the skill "
        "mirror). Same rule as `vault-check.py`.",
        "",
        f"Hand-written half last re-read **{reviewed[0]}**, at {reviewed[1]} "
        f"notes. `vault-map.py` says so when it's due again "
        f"(every {REVIEW_EVERY} notes) — stamp it with `--reviewed`.",
        "",
        f"<!-- map-reviewed: {reviewed[0]} @ {reviewed[1]} notes -->",
        "",
        END,
    ]
    return "\n".join(lines)


def nag_review(reviewed: tuple[str, int], current: int) -> None:
    grown = current - reviewed[1]
    if grown < REVIEW_EVERY:
        return
    print("")
    print(f"vault-map: !! the HAND-WRITTEN half of vault-map.md is due a re-read "
          f"— {grown} notes added since {reviewed[0]}.")
    print("  No script can refresh those two tables; they are judgement.")
    print("  Re-read the folder map and the 'where to look for what' table "
          "against what is actually in the vault,")
    print("  fix what has drifted, change nothing else, then stamp it:")
    print("      python3 AIOS/scripts/vault-map.py --reviewed")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="report whether the block is stale; change nothing")
    ap.add_argument("--reviewed", action="store_true",
                    help="stamp today: the hand-written half was just re-read")
    args = ap.parse_args()

    if not MAP.is_file():
        MAP.parent.mkdir(parents=True, exist_ok=True)
        MAP.write_text(
            "---\ntitle: scale\ntags:\n  - generated\n---\n\n"
            "# scale.md — per-folder note counts\n\n"
            "> [!warning] Generated — do not edit by hand\n"
            "> Rebuilt by `python3 AIOS/scripts/vault-map.py`, called "
            "automatically by `logchange.py` whenever a note is created or "
            "deleted. Never boot-loaded — `AIOS/vault-map.md` keeps a one-line "
            "pointer here instead of carrying this table itself.\n\n"
            + DEFAULT_BLOCK,
            encoding="utf-8",
        )

    text = MAP.read_text(encoding="utf-8")
    if BEGIN not in text or END not in text:
        print("vault-map: ERROR: generated markers missing from AIOS/generated/scale.md",
              file=sys.stderr)
        sys.exit(2)

    n = len(notes())
    reviewed = (f"{date.today():%Y-%m-%d}", n) if args.reviewed \
        else last_review(text, n)
    block = build(reviewed)
    current = re.search(re.escape(BEGIN) + r".*?" + re.escape(END), text, re.S)

    if current and current.group(0).strip() == block.strip():
        print("vault-map: Scale block already current")
        nag_review(reviewed, n)
        sys.exit(0)

    if args.check:
        print(f"vault-map: STALE — Scale block does not match reality ({n} notes)")
        print("  fix: python3 AIOS/scripts/vault-map.py")
        nag_review(reviewed, n)
        sys.exit(1)

    new = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), lambda _: block,
                 text, flags=re.S)
    MAP.write_text(new, encoding="utf-8")
    if args.reviewed:
        print(f"vault-map: hand-written half stamped as re-read today, at {n} notes")
    else:
        print(f"vault-map: Scale block rewritten — {n} notes")
    nag_review(reviewed, n)


if __name__ == "__main__":
    main()
