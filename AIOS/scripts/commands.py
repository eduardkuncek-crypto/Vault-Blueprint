#!/usr/bin/env python3
"""
commands.py — rebuild AIOS/generated/commands.md, a flat list of every trigger phrase.

Why this exists
----------------
Trigger phrases live spread across several skill tables and one routines
table in `AIOS/skill-map.md`. Nothing is missing — it just isn't in one
place, and "one place" is a mechanical problem: every trigger phrase in the
vault is already text sitting in a markdown table. This script just collects
it, so nobody has to remember where.

Unlike `AIOS/reference/migration.md` (judgement), this file is 100%
extraction, so it's fully machine-written, like `AIOS/generated/where.md`.
Never edit it by hand — edit `AIOS/skill-map.md` and rerun this.

Runs automatically: `logchange.py` calls this whenever a write touches
`AIOS/skill-map.md`, so it can't go stale.

Usage:
    python3 AIOS/scripts/commands.py            # rebuild AIOS/generated/commands.md
    python3 AIOS/scripts/commands.py --check    # would it change? exit 1 if so

No dependencies. Plain stdlib.
"""
import re
import sys
import pathlib
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parents[2]
SKILL_MAP = ROOT / "AIOS" / "skill-map.md"
OUT = ROOT / "AIOS" / "generated" / "commands.md"


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_skill_groups(text: str):
    """Every '### <group>' table under '## Installed skills', in order."""
    if "## Installed skills" not in text:
        return []
    section = text.split("## Installed skills", 1)[1].split("## Routines", 1)[0]
    parts = re.split(r"^### (.+)$", section, flags=re.M)
    groups = []
    for i in range(1, len(parts), 2):
        title = parts[i].strip()
        body = parts[i + 1]
        rows = []
        for line in body.splitlines():
            line = line.strip()
            if not line.startswith("|") or line.startswith("|---"):
                continue
            cells = _cells(line)
            if len(cells) < 2:
                continue
            if cells[0].strip("` ").lower() == "skill":
                continue
            rows.append((cells[0], cells[1]))
        if rows:
            groups.append((title, rows))
    return groups


def parse_routines(text: str):
    if "## Routines" not in text:
        return []
    section = text.split("## Routines", 1)[1].split("## Adding a routine", 1)[0]
    rows = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = _cells(line)
        if len(cells) < 3:
            continue
        if cells[0].strip("` ").lower() == "routine":
            continue
        rows.append((cells[0], cells[1], cells[2]))
    return rows


def build() -> str:
    text = SKILL_MAP.read_text(encoding="utf-8")
    groups = parse_skill_groups(text)
    routines = parse_routines(text)

    lines = [
        "---",
        "title: commands",
        "tags:",
        "  - reference",
        "  - generated",
        "---",
        "",
        "# commands.md — every trigger phrase, in one place",
        "",
        "> [!info] Generated — do not edit by hand",
        "> Rebuilt by `AIOS/scripts/commands.py`, run automatically by "
        "`logchange.py` whenever `AIOS/skill-map.md` changes. Edit the skill "
        "or routine's description there, not here.",
        f"> Rebuilt {date.today().isoformat()}.",
        "",
        "**This is the exhaustive machine list — most of it runs itself, you "
        "never say it.** Handy when you've forgotten the exact trigger "
        "phrase for something.",
        "",
        "## Skills",
        "",
    ]
    for title, rows in groups:
        lines.append(f"### {title}")
        lines.append("")
        lines.append("| Skill | Say / fires when |")
        lines.append("|---|---|")
        for name, use_when in rows:
            lines.append(f"| {name} | {use_when} |")
        lines.append("")

    lines.append("## Routines")
    lines.append("")
    lines.append("| Routine | Say / fires when | What happens |")
    lines.append("|---|---|---|")
    for name, fires, oneline in routines:
        lines.append(f"| {name} | {fires} | {oneline} |")
    lines.append("")

    lines.append("## Related")
    lines.append("")
    lines.append("- [[skill-map]] — the source this is generated from")
    lines.append("- [[routines]] — full steps once you remember the trigger")
    lines.append("- [[migration]] — the one about handing the vault to a different AI")
    lines.append("- [[me]]")
    return "\n".join(lines) + "\n"


def main() -> None:
    new_text = build()
    if "--check" in sys.argv:
        old_text = OUT.read_text(encoding="utf-8") if OUT.exists() else None
        if old_text == new_text:
            print("commands: AIOS/generated/commands.md is current")
            sys.exit(0)
        print("commands: AIOS/generated/commands.md is stale")
        sys.exit(1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(new_text, encoding="utf-8")
    print(f"commands: rewrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
