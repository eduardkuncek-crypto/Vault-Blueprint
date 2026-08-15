#!/usr/bin/env python3
"""
context-budget.py — measure what an AI loads before the user types a word.

REPORTS ONLY. Changes nothing. Same contract as vault-check.py.

Why this exists
---------------
Two things in this setup grow over time and only one is free:

  * Vault notes      — loaded on demand via vault-map.md. Effectively free.
  * The always-on
    instruction layer — skill descriptions, boot files, always-on skill bodies.
                        Paid IN FULL on every single session.

On 2026-08-07 the user asked whether growing skills were making the AI dumber.
Measured answer: ~27,000 tokens of floor, and `auto-capture` had grown 30%
that same day. He was right about the direction.

The one-time cleanup is not the fix — nothing stops it re-inflating next month.
This script is the fix: it makes the growth visible and loud.

Usage
-----
    python3 AIOS/scripts/context-budget.py              # report
    python3 AIOS/scripts/context-budget.py --baseline   # record today as the baseline

Exit codes: 0 fine · 1 over threshold · 2 couldn't measure.

Caveat, stated plainly: token counts are ESTIMATES (chars / 4). Good enough to
track direction and catch a 30% jump; not exact. And skills are read from the
vault mirror `AIOS/skills/`, which is only as fresh as the last auto-capture
mirror — if a skill was changed and not mirrored, this undercounts.

No dependencies. Plain stdlib. Added 2026-08-07.
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent.parent
SKILLS = VAULT / "AIOS" / "skills"
BASELINE = VAULT / "AIOS" / "scripts" / ".context-baseline.json"

# Read at the start of every session, per CLAUDE.md and vault-map.md
BOOT_FILES = [
    "CLAUDE.md",
    "AIOS/me.md",
    "AIOS/vault-map.md",
    "AIOS/skill-map.md",
    "Atlas/About Me/Working with AI.md",
]

# Skills whose FULL BODY loads in essentially every vault session
ALWAYS_ON = ["auto-capture", "vault-first", "vault-librarian", "no-bullshit"]

# Warn if the floor grows more than this over the recorded baseline
THRESHOLD = 0.10

TOK = 4  # chars per token, rough


def tokens(n_chars: int) -> int:
    return n_chars // TOK


def bar(n: int, peak: int, width: int = 28) -> str:
    if peak <= 0:
        return ""
    return "█" * max(1, round(width * n / peak))


def skill_description(path: Path) -> int:
    """Bytes of the description field — this is what's ALWAYS in the system prompt."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    m = re.search(r"^description:\s*(.*?)(?=^[a-zA-Z_-]+:|^---)", text, re.M | re.S)
    return len(m.group(1).strip()) if m else 0


def measure() -> dict:
    if not SKILLS.is_dir():
        print(f"context-budget: cannot find {SKILLS}", file=sys.stderr)
        sys.exit(2)

    descs, bodies = {}, {}
    for d in sorted(SKILLS.iterdir()):
        f = d / "SKILL.md"
        if not f.is_file():
            continue
        descs[d.name] = skill_description(f)
        bodies[d.name] = f.stat().st_size

    boot = {}
    for rel in BOOT_FILES:
        p = VAULT / rel
        boot[rel] = p.stat().st_size if p.is_file() else 0

    always = {n: bodies.get(n, 0) for n in ALWAYS_ON}

    return {
        "date": date.today().isoformat(),
        "n_skills": len(descs),
        "descriptions": sum(descs.values()),
        "boot": sum(boot.values()),
        "always_on": sum(always.values()),
        "floor": sum(descs.values()) + sum(boot.values()) + sum(always.values()),
        "_descs": descs,
        "_bodies": bodies,
        "_boot": boot,
        "_always": always,
    }


def report(m: dict, base: dict | None) -> int:
    print(f"context-budget — {VAULT}")
    print(f"  {m['n_skills']} skills mirrored · measured {m['date']}")
    print()

    layers = [
        (f"skill descriptions ({m['n_skills']})", m["descriptions"], "always, every session"),
        (f"boot files ({len(BOOT_FILES)})", m["boot"], "always, every session"),
        (f"always-on skill bodies ({len(ALWAYS_ON)})", m["always_on"], "always, in this vault"),
    ]
    peak = max(x[1] for x in layers)
    print(f"  {'LAYER':<34} {'~tokens':>8}   {'':<28} WHEN")
    for name, n, when in layers:
        print(f"  {name:<34} {tokens(n):>8}   {bar(n, peak):<28} {when}")
    print(f"  {'-' * 34} {'-' * 8}")
    print(f"  {'FLOOR BEFORE HE TYPES A WORD':<34} {tokens(m['floor']):>8}")
    print()

    print("  Heaviest always-on items:")
    items = [(f"skill: {k}", v) for k, v in m["_always"].items()]
    items += [(f"boot:  {k}", v) for k, v in m["_boot"].items()]
    for name, n in sorted(items, key=lambda x: -x[1])[:8]:
        print(f"    {tokens(n):>6} tok  {name}")
    print()

    print("  Fattest descriptions (these load even when irrelevant):")
    for name, n in sorted(m["_descs"].items(), key=lambda x: -x[1])[:5]:
        print(f"    {tokens(n):>6} tok  {name}")
    print()

    if not base:
        print("  No baseline recorded. Run with --baseline to set one,")
        print("  then this script can tell you when things are creeping up.")
        return 0

    delta = m["floor"] - base["floor"]
    pct = (delta / base["floor"]) if base["floor"] else 0
    arrow = "+" if delta >= 0 else ""
    print(f"  Baseline {base['date']}: {tokens(base['floor'])} tok")
    print(f"  Now:                {tokens(m['floor'])} tok  ({arrow}{tokens(delta)} tok, {arrow}{pct:.0%})")
    print()

    if pct > THRESHOLD:
        print(f"  OVER BUDGET — the floor has grown {pct:.0%} since {base['date']}.")
        print("  Before adding more text, read Atlas/Reference/Context budget.md.")
        print("  The rule there: when a rule fails, the fix is a MECHANISM or a")
        print("  SHORTER rule. Never a longer one.")
        return 1

    print(f"  Within budget (threshold {THRESHOLD:.0%}).")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", action="store_true", help="record today's measurement as the baseline")
    args = ap.parse_args()

    m = measure()

    base = None
    if BASELINE.is_file():
        try:
            base = json.loads(BASELINE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            base = None

    if args.baseline:
        keep = {k: v for k, v in m.items() if not k.startswith("_")}
        BASELINE.write_text(json.dumps(keep, indent=2) + "\n", encoding="utf-8")
        print(f"context-budget: baseline recorded — {tokens(m['floor'])} tok on {m['date']}")
        print(f"  {BASELINE.relative_to(VAULT)}")
        return

    sys.exit(report(m, base))


if __name__ == "__main__":
    main()
